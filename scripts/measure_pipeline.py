"""Measure local parsing time, peak process RSS, provenance; no invented quality scores."""

import argparse
import json
import resource
import sys
import time
from pathlib import Path
from rgi.ingest import parse_pdf, chunk_items
from rgi.embeddings import embedder

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("pdf", nargs="+", type=Path)
parser.add_argument("--parsers", nargs="+", default=["pypdf", "docling"])
parser.add_argument(
    "--embed", action="store_true", help="Explicitly load configured CPU embedder (may download small BGE)"
)
parser.add_argument("--output", type=Path, default=Path(".data/pipeline-measurements.json"))
args = parser.parse_args()
rows = []
for backend in args.parsers:
    for path in args.pdf:
        start = time.perf_counter()
        try:
            items, artifact = parse_pdf(path, backend)
            row = {
                "pdf": path.name,
                "parser": backend,
                "status": "ran",
                "items": len(items),
                "characters": sum(len(i.text) for i in items),
                "items_with_boxes": sum(bool(i.boxes) for i in items),
                "warnings": artifact["warnings"],
                "quality_review": "pending manual inspection",
            }
            if args.embed:
                encoder = embedder()
                chunks = list(chunk_items(items, encoder))
                for i in range(0, len(chunks), 8):
                    encoder.encode([c["payload"] for c in chunks[i : i + 8]])
                row.update(chunks=len(chunks), embedding_id=encoder.identity)
        except ImportError:
            row = {"pdf": path.name, "parser": backend, "status": "not run: dependency unavailable"}
        except Exception as exc:
            row = {"pdf": path.name, "parser": backend, "status": f"failed: {type(exc).__name__}"}
        row["elapsed_seconds"] = time.perf_counter() - start
        raw_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        row["process_peak_rss_mib"] = raw_rss / (1024 * 1024 if sys.platform == "darwin" else 1024)
        row["rss_note"] = "Cumulative process peak, including imports; not per-document incremental RAM"
        rows.append(row)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(rows, indent=2))
print(f"Measurements: {args.output}")
