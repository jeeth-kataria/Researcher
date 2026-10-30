# Evaluation protocol

`draft_cases.json` contains generated synthetic draft relevance labels, **pending
human review**. `results.fixture.json` is an actual run of deterministic fixture
functions (not SQLite retrieval, not an LLM, not a full worker benchmark). It exists
to verify reporting/denominators. It cannot show scientific quality or multi-agent
superiority. `pipeline-measurements.json` records measured parse time and process peak
RSS; missing parsers explicitly say not run. No results are human-validated yet.

`uv run python -m rgi.evaluate --collection UUID --provider fixture` evaluates actual
persisted API/worker runs in RAG, single and multi modes, for each case. Choose Groq
explicitly only after free-tier acknowledgement; it consumes quota. All modes share
corpus/model and the same declared ceiling. Their actual calls/tokens differ and are
reported, not disguised as equal. The harness aborts on corpus version changes, quota
pauses, failure, or mismatched manifests. It never switches providers. Compare real
modes only on a separately reviewed corpus; these fixtures are toy controls.

Metrics:

- Draft retrieval recall@k: relevant draft snippets found in the **initial** retrieval
  divided by the number of annotated relevant snippets. It uses initial search event IDs,
  not extra followups. In offline function mode the entire supplied example evidence is
  the retrieval context; this is not a measured hybrid search score. Human validation
  is pending, so the metric remains explicitly draft even when the value is 1.
- Structural citation correctness: existing IDs in the frozen manifest with exact
  whitespace-normalized source quotes / all citations in generated claims. No citations
  gives null, not a perfect score. This does not measure entailment.
- Factual support: human-supported claims / human-judged claims. Without judgments
  the numerator and denominator are zero and value null. Reviewer self-scores are
  never used as ground truth. Unjudged claim count is reported.
- False candidate-gap rate: human-labeled false candidates / human-judged candidates.
  Without judgments it is null. Dispositions are reported separately as workflow
  output, not a truth label. Include the known-studied retrieval control when reviewing.
- Latency: elapsed wall time. Offline is fixture functions only. API mode includes
  queue, worker processing and polling; it is explicitly not pure LLM latency.
- Tokens: provider metadata or null. Fixtures use zero because no model was called.
  Application budget reservations are not measured token counts.

Supply human judgments only after actually reviewing the evidence and documenting the
reviewer/protocol. JSON shape for `--judgments FILE`:

```json
{
  "review_status": "human-reviewed",
  "reviewer": "actual reviewer name",
  "RUN_UUID": {
    "claim_support": {"SHA256_OF_EXACT_CLAIM_TEXT": true},
    "false_candidate_gaps": {"candidate-id": false}
  }
}
```

The tool records your explicit attestation; it cannot certify a person performed the
review. Do not mark generated annotations human-reviewed. Add ambiguity notes to a
review log; double-review a subset before quality claims. Predefine task scope and
refutation criteria before evaluating real candidate gaps. Baseline wins are valid
outcomes; investigate coverage/budget differences rather than assuming agents help.

Single mode uses one researcher persona with extraction, self-review and proposal
continuations (three calls); multi uses five role personas across six calls. Shared
declared ceilings do not make actual usage identical. Single self-review is explicitly
not an independent skeptical worker. Ordinary RAG is one call without that continuation.
