"""Export a reviewed local run for static exploration; PDFs require license review."""

import argparse
import json
from pathlib import Path
from rgi.db import one, many

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run_id")
parser.add_argument("--output", type=Path, default=Path(".data/export"))
args = parser.parse_args()
run = one("SELECT * FROM runs WHERE id=%s AND status='complete'", (args.run_id,))
if not run:
    raise SystemExit("Completed run not found")
run["events"] = many("SELECT * FROM events WHERE run_id=%s ORDER BY id", (args.run_id,))
# Never export credentials, prompts or third-party PDF bytes.
args.output.mkdir(parents=True, exist_ok=True)
(args.output / "run.json").write_text(json.dumps(run, default=str, ensure_ascii=False, indent=2))
(args.output / "report.md").write_text(run["report"])
print("Exported report and source text; review licenses/privacy before public redistribution")
