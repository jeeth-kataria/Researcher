> Historical ADR: PostgreSQL/Gemini-first details are superseded by the user-approved
> [ADR 004](004-sqlite-and-groq.md). Use README and current architecture/setup docs.

# ADR 002 — typed stages before autonomous tools (accepted)
Requirement: teachable baseline, recoverable five-role research and skepticism.
Choice: shared Python functions scheduled by a small explicit LangGraph. Ordinary RAG
is one answer; single researcher gets self-review/experiment continuation stages; multi separates lead,
literature, methods, skepticism and experiment roles. Six multi-role model calls, not
five concurrent independent authorities. One concurrency slot and one review round.
Alternatives: unconstrained role conversation, fully autonomous function-calling agents,
parallel dependent steps. Tradeoff: less agent flexibility, stronger source/budget and
dependency contracts. Model-selected literature followups and deterministic counter
searches are bounded, validated retrieval inputs. Revisit when evaluated failures show
that missing tool autonomy matters more than added cost and state complexity.

Requirement: exact provenance AND honest uncertainty. Pydantic output models, frozen
manifest checks, exact normalized quotes and separate indexed support reviews. Gemini
1.20's wire schema accepts a subset, so references are expanded and unsupported JSON
Schema constraints omitted on the wire; full local Pydantic validation remains strict.
This was verified with the official SDK and mock HTTP transport, not just a fake SDK.
Alternative: trust structured JSON or use the same model's self-score as confidence.
Tradeoff: supporting a fact still needs human judgment. Revisit after independently
reviewed entailment/control datasets, never because five agents agree.

Requirement: no-spend and replay honesty. Explicit provider and billing acknowledgement,
no fallback, pre-call durable intent and conservative reservations, explicit ambiguity
acknowledgement after crashes. Exactly-once LLM calls are impossible without provider
idempotency guarantees. Quota pause and Retry-After win over automatic retry loops.
