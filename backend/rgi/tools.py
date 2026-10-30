"""Small scoped tools; no network, filesystem, shell or arbitrary code access."""

from uuid import UUID
from pydantic import Field
from .schemas import Strict
from .db import connect, many
from .jobs import check_cancel, event, fence
from .retrieval import search, context


class SearchInput(Strict):
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=8, ge=1, le=20)


class ContextInput(Strict):
    evidence_id: UUID


class PaperInput(Strict):
    paper_id: UUID


class Tools:
    def __init__(self, run, job, owner):
        self.run, self.job, self.owner = run, job, owner
        self.versions = [str(m["version_id"]) for m in run["manifest"]]

    def call(self, name, arguments):
        check_cancel(self.run["id"])
        if name not in (
            "search_passages",
            "read_context",
            "list_corpus",
            "inspect_paper",
            "fetch_extraction",
        ):
            raise ValueError("Tool not allowed")
        with connect() as conn:
            fence(conn, self.job["id"], self.owner)
            row = conn.execute(
                """UPDATE runs SET tool_calls=tool_calls+1 WHERE id=%s AND tool_calls<%s
                RETURNING tool_calls""",
                (self.run["id"], self.run["config"]["budget"]["max_tool_calls"]),
            ).fetchone()
            if not row:
                raise ValueError("Tool budget exhausted")
        if name == "search_passages":
            args = SearchInput.model_validate(arguments)
            result = search(
                self.run["collection_id"],
                args.query,
                args.k,
                self.run["config"]["budget"]["paper_diversity"],
                self.versions,
            )
        elif name == "read_context":
            args = ContextInput.model_validate(arguments)
            result = context(self.run["collection_id"], args.evidence_id, self.versions)
        elif name == "list_corpus":
            if arguments:
                raise ValueError("list_corpus takes no arguments")
            result = self.run["manifest"]
        else:
            args = PaperInput.model_validate(arguments)
            matched = [m for m in self.run["manifest"] if m["paper_id"] == str(args.paper_id)]
            if not matched:
                raise ValueError("Paper outside run corpus")
            if name == "inspect_paper":
                result = matched
            else:
                result = many(
                    "SELECT role,payload FROM artifacts WHERE run_id=%s AND role='methods'", (self.run["id"],)
                )
        with connect() as conn:
            fence(conn, self.job["id"], self.owner)
            # Evidence content is returned to the model; operational trace stores IDs and inputs.
            ids = (
                [str(p["id"]) for p in result if isinstance(p, dict) and "id" in p]
                if isinstance(result, list)
                else []
            )
            event(
                conn,
                self.run["id"],
                name,
                "tool_result",
                {
                    "arguments": arguments,
                    "evidence_ids": ids,
                    "count": len(result) if isinstance(result, list) else 1,
                },
            )
        return result
