"""SQLite FTS5 BM25 + exact CPU cosine, fused with RRF (never probabilities)."""

import heapq
import math
import re
from .db import connect, many, one
from .embeddings import embedder, embedding_identity


def latest_manifest(collection_id):
    return many(
        """SELECT version_id,paper_id,title,sha256,processing_id,embedding_id FROM (
          SELECT d.id AS version_id,p.id AS paper_id,p.title,d.sha256,d.processing_id,d.embedding_id,
          row_number() OVER (PARTITION BY p.id ORDER BY d.created_at DESC,d.rowid DESC) AS position
          FROM papers p JOIN document_versions d ON d.paper_id=p.id
          WHERE p.collection_id=? AND d.status='ready') WHERE position=1 ORDER BY paper_id""",
        (collection_id,),
    )


def fts_query(query):
    # Treat user input as literal Unicode terms, not FTS operators or SQL. Bound
    # the expression; OR lets names and individual concepts contribute evidence.
    terms = list(dict.fromkeys(re.findall(r"\w+", query, flags=re.UNICODE)))[:64]
    return " OR ".join('"' + term + '"' for term in terms)


def cosine_distance(left, right):
    if len(left) != 384 or len(right) != 384 or not all(math.isfinite(x) for x in left + right):
        raise ValueError("Invalid embedding dimensions or non-finite vector")
    denominator = math.sqrt(sum(x * x for x in left) * sum(x * x for x in right))
    return 1.0 - sum(a * b for a, b in zip(left, right, strict=True)) / denominator if denominator else 1.0


def search(collection_id, query, k=8, diversity=3, versions=None):
    if not query.strip() or len(query) > 2000:
        raise ValueError("Query must contain 1–2000 characters")
    if not 1 <= k <= 20 or not 1 <= diversity <= 10:
        raise ValueError("Retrieval bounds exceeded")
    manifest = latest_manifest(collection_id)
    if versions is not None:
        requested = {str(v) for v in versions}
        # Frozen runs may refer to a prior ready version, not the newest version.
        manifest = many(
            """SELECT d.id AS version_id,d.embedding_id FROM document_versions d
            JOIN papers p ON p.id=d.paper_id WHERE p.collection_id=? AND d.status='ready'""",
            (collection_id,),
        )
        manifest = [m for m in manifest if m["version_id"] in requested]
    allowed = [v["version_id"] for v in manifest]
    if not allowed:
        return []
    if any(v["embedding_id"] != embedding_identity() for v in manifest):
        raise ValueError(
            "Index embedding identity differs; explicitly select matching worker/API configuration"
        )
    query_vector = embedder().encode([query], query=True)[0]
    placeholders = ",".join("?" for _ in allowed)
    scope = f"p.collection_id=? AND c.version_id IN ({placeholders})"
    params = (collection_id, *allowed)
    with connect(write=False) as conn:
        keywords = []
        expression = fts_query(query)
        if expression:
            keywords = conn.execute(
                f"""SELECT c.id,bm25(passage_fts) AS score FROM passage_fts
                JOIN passages c ON c.rowid=passage_fts.rowid
                JOIN document_versions d ON c.version_id=d.id JOIN papers p ON d.paper_id=p.id
                WHERE passage_fts MATCH ? AND {scope} ORDER BY score,c.id LIMIT 80""",
                (expression, *params),
            ).fetchall()
        cursor = conn.execute(
            f"""SELECT c.id,c.embedding FROM passages c JOIN document_versions d ON c.version_id=d.id
            JOIN papers p ON d.paper_id=p.id WHERE {scope}""",
            params,
        )

        def distances():
            while batch := cursor.fetchmany(128):
                for row in batch:
                    yield (cosine_distance(row["embedding"], query_vector), row["id"])

        nearest = heapq.nsmallest(80, distances())
        keyword_ranks = {row["id"]: rank for rank, row in enumerate(keywords, 1)}
        vector_ranks = {identity: rank for rank, (_, identity) in enumerate(nearest, 1)}
        ids = sorted(set(keyword_ranks) | set(vector_ranks))
        if not ids:
            return []
        rows = conn.execute(
            f"""SELECT c.id,c.version_id,p.id AS paper_id,p.title,c.heading,c.text,c.page,
            c.item_ids,c.boxes,c.ordinal FROM passages c JOIN document_versions d ON c.version_id=d.id
            JOIN papers p ON d.paper_id=p.id WHERE c.id IN ({",".join("?" for _ in ids)}) AND {scope}""",
            (*ids, *params),
        ).fetchall()
    for row in rows:
        kr, vr = keyword_ranks.get(row["id"]), vector_ranks.get(row["id"])
        row.update(
            keyword_rank=kr,
            vector_rank=vr,
            fused_score=(1 / (60 + kr) if kr else 0) + (1 / (60 + vr) if vr else 0),
        )
    rows.sort(key=lambda r: (-r["fused_score"], r["id"]))
    selected, counts, texts = [], {}, set()
    for row in rows:
        paper = row["paper_id"]
        canonical = " ".join(row["text"].split()).lower()
        if counts.get(paper, 0) >= diversity or canonical in texts:
            continue
        counts[paper] = counts.get(paper, 0) + 1
        texts.add(canonical)
        selected.append({**row, "fused_rank": len(selected) + 1})
        if len(selected) >= k:
            break
    return selected


def context(collection_id, evidence_id, versions=None):
    item = one(
        """SELECT c.*,p.title,p.id AS paper_id,p.collection_id FROM passages c
        JOIN document_versions d ON d.id=c.version_id JOIN papers p ON p.id=d.paper_id
        WHERE c.id=? AND p.collection_id=?""",
        (evidence_id, collection_id),
    )
    if not item or (versions is not None and item["version_id"] not in {str(v) for v in versions}):
        raise ValueError("Evidence is outside allowed corpus")
    item.pop("embedding", None)
    neighbors = many(
        """SELECT id,version_id,text,page,heading,ordinal,item_ids,boxes FROM passages WHERE version_id=?
        AND ordinal BETWEEN ? AND ? ORDER BY ordinal""",
        (item["version_id"], item["ordinal"] - 1, item["ordinal"] + 1),
    )
    return {"passage": item, "neighbors": neighbors}
