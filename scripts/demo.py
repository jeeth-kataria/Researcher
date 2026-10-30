"""Real API/worker plumbing demo using original synthetic PDFs and fixture responses."""

import argparse
import os
import time
from pathlib import Path
import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--provider", choices=["fixture", "groq", "gemini"], default="fixture")
    parser.add_argument("--mode", choices=["rag", "single", "multi"], default="multi")
    parser.add_argument("--output", type=Path, default=Path(".data/demo-report.md"))
    args = parser.parse_args()
    headers = (
        {"Authorization": f"Bearer {os.environ['RGI_OWNER_TOKEN']}"} if os.getenv("RGI_OWNER_TOKEN") else {}
    )
    with httpx.Client(base_url=args.url, headers=headers, timeout=30) as api:

        def check(response):
            response.raise_for_status()
            return response.json()

        health = check(api.get("/api/health"))
        if health["database"] != "online" or not health["worker"]["online"]:
            raise SystemExit("Initialize SQLite and start the API and a real worker first")
        collection = check(api.post("/api/collections", json={"name": f"Synthetic demo {time.time_ns()}"}))
        cid = collection["id"]
        for path in sorted(Path("fixtures").glob("*.pdf")):
            check(
                api.post(
                    f"/api/collections/{cid}/papers",
                    data={"title": path.stem},
                    files={"file": (path.name, path.read_bytes(), "application/pdf")},
                )
            )
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            docs = check(api.get(f"/api/collections/{cid}/papers"))
            if any(d["status"] == "failed" for d in docs):
                raise SystemExit(f"Ingestion failed: {docs}")
            if len(docs) == 3 and all(d["status"] == "ready" for d in docs):
                break
            time.sleep(2)
        else:
            raise SystemExit("Ingestion timeout; inspect worker errors")
        hits = check(api.get(f"/api/collections/{cid}/search", params={"q": "memory retrieval", "k": 8}))
        print(f"Retrieved {len(hits)} passages from original synthetic fixture PDFs")
        if not hits:
            raise SystemExit("Retrieval returned no evidence")
        check(api.get(f"/api/collections/{cid}/evidence/{hits[0]['id']}"))
        run = check(
            api.post(
                "/api/runs",
                json={
                    "collection_id": cid,
                    "question": "How should memory retrieval ordering be evaluated under distractors?",
                    "provider": args.provider,
                    "mode": args.mode,
                },
            )
        )
        while time.monotonic() < deadline:
            detail = check(api.get(f"/api/runs/{run['id']}"))
            if detail["status"] == "complete":
                report = api.get(f"/api/runs/{run['id']}/report")
                report.raise_for_status()
                out = args.output
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(report.text)
                print(f"{detail['provenance']}\nRun {run['id']}\nReport: {out}")
                return
            if detail["status"] in ("failed", "paused", "waiting_for_quota", "cancelled"):
                raise SystemExit(f"{detail['status']}: {detail['error']}")
            time.sleep(2)
        raise SystemExit("Run timeout; persisted job remains inspectable")


if __name__ == "__main__":
    main()
