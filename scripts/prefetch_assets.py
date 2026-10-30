"""Explicitly populate local CPU parser/embedding caches. No generative model download."""

from rgi.config import configure_model_cache
from rgi.embeddings import BGEEmbedder
from rgi.ingest import parse_pdf
from pathlib import Path

configure_model_cache()
print("Loading pinned BGE-small CPU assets (Internet required on first use)")
encoder = BGEEmbedder()
print(f"Loaded {encoder.identity}, token window {encoder.limit}, dimension 384")
print("Loading Docling layout/table assets with OCR disabled")
items, artifact = parse_pdf(Path("fixtures/paper-a.pdf"), "docling")
print(f"Parsed original synthetic fixture: {len(items)} source items; not research results")
