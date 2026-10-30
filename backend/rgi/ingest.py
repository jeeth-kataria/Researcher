"""Independent per-document ingestion; immutable versions and atomic indexing."""

import json
import hashlib
from dataclasses import dataclass, field
from importlib.metadata import version as package_version
from time import monotonic
from uuid import UUID, uuid4, uuid5
from .config import settings, configure_model_cache
from .db import connect, one, json_value
from .storage import path_for, store_pdf
from .embeddings import embedder, embedding_identity, vector_json, PREPROCESS
from .jobs import enqueue, fence


@dataclass
class Item:
    text: str
    page: int
    heading: str = "Document"
    item_ids: list[str] = field(default_factory=list)
    boxes: list[dict] = field(default_factory=list)


def processing_id():
    parser = settings().parser
    parser_version = {"docling": "2.36.1", "pypdf": "5.6.0"}.get(parser)
    if parser_version is None:
        raise ValueError("Unknown parser")
    return f"{parser}@{parser_version}:ocr-off:chunk-v1:target-420:{PREPROCESS}:{embedding_identity()}"


def upload(collection_id, title, data):
    if not title.strip() or len(title) > 200:
        raise ValueError("Paper title must contain 1–200 characters")
    if not one("SELECT id FROM collections WHERE id=?", (collection_id,)):
        raise ValueError("Collection not found")
    digest, key = store_pdf(data)
    identity = processing_id()
    with connect() as conn:
        # Serialize collection count+insert; no upload race can exceed the configured limit.
        conn.execute("SELECT id FROM collections WHERE id=?", (collection_id,))
        paper = conn.execute(
            "SELECT * FROM papers WHERE collection_id=? AND title=?", (collection_id, title)
        ).fetchone()
        if not paper:
            count = conn.execute(
                "SELECT count(*) AS n FROM papers WHERE collection_id=?", (collection_id,)
            ).fetchone()["n"]
            if count >= settings().max_papers:
                raise ValueError("Collection paper limit reached")
            paper = conn.execute(
                "INSERT INTO papers(id,collection_id,title) VALUES (?,?,?) RETURNING *",
                (uuid4(), collection_id, title),
            ).fetchone()
        prior = conn.execute(
            """SELECT * FROM document_versions
            WHERE paper_id=? AND sha256=? AND processing_id=?""",
            (paper["id"], digest, identity),
        ).fetchone()
        if prior:
            return {**prior, "duplicate": True}
        doc = conn.execute(
            """INSERT INTO document_versions
            (id,paper_id,sha256,storage_key,processing_id,parser,embedding_id)
            VALUES (?,?,?,?,?,?,?) RETURNING *""",
            (uuid4(), paper["id"], digest, key, identity, settings().parser, embedding_identity()),
        ).fetchone()
        enqueue(conn, "ingest", doc["id"])
        return {**doc, "duplicate": False}


def parse_pdf(path, parser):
    if parser == "pypdf":
        from pypdf import PdfReader

        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are unsupported")
        if len(reader.pages) > 200:
            raise ValueError("PDF exceeds 200-page application limit")
        items = [
            Item(p.extract_text() or "", n + 1, item_ids=[f"page/{n + 1}"])
            for n, p in enumerate(reader.pages)
        ]
        return items, {"parser": "pypdf", "warnings": ["Baseline parser: layout/boxes unavailable"]}
    if parser != "docling":
        raise ValueError("Unknown parser; no silent fallback")
    cache_root = configure_model_cache()
    from docling.datamodel.settings import settings as docling_settings

    docling_settings.cache_dir = cache_root / "docling"
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
    options.accelerator_options = AcceleratorOptions(num_threads=2, device=AcceleratorDevice.CPU)
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    result = converter.convert(path, max_num_pages=200)
    doc = result.document
    heading = "Document"
    items = []
    warnings = []
    for item, _level in doc.iterate_items():
        label = str(item.label.value)
        if label in ("section_header", "title"):
            heading = item.text
        text = item.export_to_markdown(doc=doc) if label == "table" else getattr(item, "text", "")
        if not text.strip():
            continue
        prov = item.prov
        boxes = [{"page": p.page_no, "bbox": p.bbox.model_dump(mode="json")} for p in prov]
        page = prov[0].page_no if prov else 1
        if not prov:
            warnings.append(f"No coordinates for {item.self_ref}; page is fallback")
        items.append(Item(text, page, heading, [item.self_ref], boxes))
    return items, {"parser": "docling", "warnings": warnings, "document": doc.export_to_dict()}


def chunk_items(items, encoder, target=420):
    """Greedy actual-token chunks preserve each source item and heading.

    Item boundaries deliberately avoid invented continuity/coordinates. Oversized
    tables are split as text and retain original table IDs and source boxes.
    """
    for item in items:
        heading = item.heading
        if encoder.count(heading) > 90:
            # Keep original heading in metadata; shorten only the embedding prefix.
            prefix = "Document section"
        else:
            prefix = heading
        words = item.text.split()
        offset = 0
        while offset < len(words):
            low, high = 1, len(words) - offset
            fit = 0
            while low <= high:
                mid = (low + high) // 2
                payload = prefix + "\n" + " ".join(words[offset : offset + mid])
                if encoder.count(payload) <= target:
                    fit, low = mid, mid + 1
                else:
                    high = mid - 1
            if not fit:
                raise ValueError("A source token exceeds the chunk budget; cannot safely index")
            # Text is an exact normalized source span, not generated prose.
            text = " ".join(words[offset : offset + fit])
            payload = prefix + "\n" + text
            yield {
                "text": text,
                "heading": heading,
                "page": item.page,
                "item_ids": item.item_ids,
                "boxes": item.boxes,
                "payload": payload,
                "token_count": encoder.count(payload),
            }
            offset += fit


def ingest(job, owner):
    doc = one("SELECT * FROM document_versions WHERE id=?", (job["target_id"],))
    if doc["status"] == "ready":
        return
    if doc["processing_id"] != processing_id():
        raise ValueError("Worker processing configuration differs from submitted document; restore it")
    with connect() as conn:
        fence(conn, job["id"], owner)
        conn.execute("UPDATE document_versions SET status='parsing',error=NULL WHERE id=?", (doc["id"],))
    expected_parser_version = {"docling": "2.36.1", "pypdf": "5.6.0"}[doc["parser"]]
    if package_version(doc["parser"]) != expected_parser_version:
        raise ValueError("Parser installed version differs from processing identity; use the lockfile")
    start = monotonic()
    cache_id = hashlib.sha256(f"{doc['sha256']}:{doc['processing_id']}".encode()).hexdigest()
    cache_path = path_for(f"index-cache/{cache_id}.json")
    if cache_path.exists():
        cached = json.loads(cache_path.read_text())
        chunks, vectors, artifact = cached["chunks"], cached["vectors"], cached["artifact"]
        artifact = {**artifact, "reused_processing_cache": True}
        if len(chunks) != len(vectors):
            raise ValueError("Corrupt local processing cache")
    else:
        items, artifact = parse_pdf(path_for(doc["storage_key"]), doc["parser"])
        if sum(len(i.text.strip()) for i in items) < 80:
            raise ValueError("Insufficient embedded text; scanned/image PDFs need OCR, disabled in v1")
        enc = embedder()
        chunks = list(chunk_items(items, enc))
        if not chunks:
            raise ValueError("No indexable passages")
        vectors = []
        for i in range(0, len(chunks), 8):
            vectors.extend(enc.encode([c["payload"] for c in chunks[i : i + 8]]))
        artifact["items"] = [vars(i) for i in items]
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix(f".{uuid4()}.tmp")
        temporary.write_text(
            json.dumps({"chunks": chunks, "vectors": vectors, "artifact": artifact}, default=str)
        )
        temporary.replace(cache_path)
    key = f"parsed/{doc['id']}.json"
    artifact.update(
        {
            "processing_id": doc["processing_id"],
            "duration_seconds": monotonic() - start,
            "chunk_count": len(chunks),
        }
    )
    artifact_path = path_for(key)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact, default=str))
    with connect() as conn:
        fence(conn, job["id"], owner)
        for n, (chunk, vec) in enumerate(zip(chunks, vectors, strict=True)):
            pid = uuid5(UUID(str(doc["id"])), str(n))
            conn.execute(
                """INSERT INTO passages(id,version_id,ordinal,heading,text,page,item_ids,boxes,
                token_count,embedding) VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT (version_id,ordinal) DO NOTHING""",
                (
                    pid,
                    doc["id"],
                    n,
                    chunk["heading"],
                    chunk["text"],
                    chunk["page"],
                    json_value(chunk["item_ids"]),
                    json_value(chunk["boxes"]),
                    chunk["token_count"],
                    vector_json(vec),
                ),
            )
        conn.execute(
            """UPDATE document_versions SET status='ready',warnings=?,artifact_key=?,error=NULL
            WHERE id=?""",
            (json_value(artifact["warnings"]), key, doc["id"]),
        )
