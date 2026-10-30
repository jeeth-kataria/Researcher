"""Exact cosine + PostgreSQL ts_rank_cd, fused with RRF (not probabilities)."""

from .db import connect, many, one
from .embeddings import embedder, vector_sql, embedding_identity


def latest_manifest(collection_id):
    return many(
        """SELECT DISTINCT ON (p.id) d.id AS version_id,p.id AS paper_id,p.title,
        d.sha256,d.processing_id,d.embedding_id FROM papers p JOIN document_versions d ON d.paper_id=p.id
        WHERE p.collection_id=%s AND d.status='ready' ORDER BY p.id,d.created_at DESC,d.id""",
        (collection_id,),
    )


def search(collection_id, query, k=8, diversity=3, versions=None):
    if not query.strip() or len(query) > 2000:
        raise ValueError("Query must contain 1–2000 characters")
    if not 1 <= k <= 20 or not 1 <= diversity <= 10:
        raise ValueError("Retrieval bounds exceeded")
    manifest = (
        latest_manifest(collection_id)
        if versions is None
        else many(
            """SELECT d.id AS version_id,
        d.embedding_id FROM document_versions d JOIN papers p ON p.id=d.paper_id
        WHERE p.collection_id=%s AND d.id=ANY(%s::uuid[]) AND d.status='ready'""",
            (collection_id, versions),
        )
    )
    allowed = [str(v["version_id"]) for v in manifest]
    if not allowed:
        return []
    if any(v["embedding_id"] != embedding_identity() for v in manifest):
        raise ValueError(
            "Index embedding identity differs; explicitly select matching worker/API configuration"
        )
    vector = vector_sql(embedder().encode([query], query=True)[0])
    with connect() as conn:
        rows = conn.execute(
            """WITH eligible AS (
            SELECT c.*,p.id AS paper_id,p.title FROM passages c
            JOIN document_versions d ON c.version_id=d.id JOIN papers p ON d.paper_id=p.id
            WHERE p.collection_id=%s AND c.version_id=ANY(%s::uuid[])
          ), kw AS (
            SELECT id,row_number() OVER (ORDER BY ts_rank_cd(search,websearch_to_tsquery('english',%s)) DESC,id)
              AS keyword_rank FROM eligible WHERE search @@ websearch_to_tsquery('english',%s) ORDER BY keyword_rank LIMIT 80
          ), vec AS (
            SELECT id,row_number() OVER (ORDER BY embedding <=> %s::vector,id) AS vector_rank
            FROM eligible ORDER BY embedding <=> %s::vector,id LIMIT 80
          ) SELECT e.id,e.version_id,e.paper_id,e.title,e.heading,e.text,e.page,e.item_ids,e.boxes,e.ordinal,
            kw.keyword_rank,vec.vector_rank,
            COALESCE(1.0/(60+kw.keyword_rank),0)+COALESCE(1.0/(60+vec.vector_rank),0) AS fused_score
          FROM eligible e LEFT JOIN kw ON e.id=kw.id LEFT JOIN vec ON e.id=vec.id
          WHERE kw.id IS NOT NULL OR vec.id IS NOT NULL ORDER BY fused_score DESC,e.id LIMIT 100""",
            (collection_id, allowed, query, query, vector, vector),
        ).fetchall()
    selected, counts, texts = [], {}, set()
    for row in rows:
        paper = str(row["paper_id"])
        canonical = " ".join(row["text"].split()).lower()
        if counts.get(paper, 0) >= diversity or canonical in texts:
            continue
        counts[paper] = counts.get(paper, 0) + 1
        texts.add(canonical)
        selected.append({**row, "fused_rank": len(selected) + 1, "fused_score": float(row["fused_score"])})
        if len(selected) >= k:
            break
    return selected


def context(collection_id, evidence_id, versions=None):
    item = one(
        """SELECT c.*,p.title,p.id AS paper_id,p.collection_id FROM passages c
        JOIN document_versions d ON d.id=c.version_id JOIN papers p ON p.id=d.paper_id
        WHERE c.id=%s AND p.collection_id=%s""",
        (evidence_id, collection_id),
    )
    if not item or (versions is not None and str(item["version_id"]) not in {str(v) for v in versions}):
        raise ValueError("Evidence is outside allowed corpus")
    item.pop("embedding", None)
    item.pop("search", None)
    neighbors = many(
        """SELECT id,version_id,text,page,heading,ordinal,item_ids,boxes FROM passages WHERE version_id=%s
        AND ordinal BETWEEN %s AND %s ORDER BY ordinal""",
        (item["version_id"], item["ordinal"] - 1, item["ordinal"] + 1),
    )
    return {"passage": item, "neighbors": neighbors}
