# ADR 003 — static examples before optional hosted compute (accepted)
Requirement: usable public example at zero required cost without laptop availability.
Choice: Vite demo-mode static build with original synthetic PDFs, report and JSON.
It is read-only, clearly labeled, and exports inspectable source evidence. No keys or
accounts required. Alternative: always-on worker or a free hosted API required for the
portfolio. Tradeoff: static exploration cannot create a real run. Revisit only when
free-tier limitations, storage licensing, worker availability and authenticated owner
access have been verified in the actual account.

No API is externally deployed. Mode C remains optional preparation with an explicit
sizing/connection/storage gate. Current local query embeddings load BGE in the API;
claiming this fits a small free API instance would be unsupported. Optional Supabase
storage/auth, arXiv discovery, Ollama and reranking are deferred outside the critical
path. Required stack choices remain intact; no paid provider/storage substitution.
