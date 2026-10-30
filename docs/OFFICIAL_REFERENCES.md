# Official references checked during this build

Checked 2026-10-30; plan limits and APIs can change. Package pins/locks are in the root
pyproject/uv.lock and frontend package files. Sources explain choices; executed checks
and their limitations are in VERIFICATION.md.

- FastAPI version discipline: https://fastapi.tiangolo.com/deployment/versions/
- Vite Node compatibility: https://vite.dev/guide/
- Vite patched stable release line: https://github.com/vitejs/vite/releases
- Playwright stable release: https://github.com/microsoft/playwright/releases/tag/v1.55.1
- Docling structure/chunking: https://docling-project.github.io/docling/concepts/chunking/
- BGE model card (384D, 512-token window): https://huggingface.co/BAAI/bge-small-en-v1.5
- BGE revision metadata: https://huggingface.co/api/models/BAAI/bge-small-en-v1.5
- LangGraph Postgres persistence: https://docs.langchain.com/oss/python/langgraph/add-memory
- Psycopg connections/pools: https://www.psycopg.org/psycopg3/docs/advanced/pool.html
- pgvector install/exact search: https://github.com/pgvector/pgvector
- Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- Account-specific rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Structured output API: https://ai.google.dev/gemini-api/docs/structured-output
- Pinned SDK types: https://github.com/googleapis/python-genai/blob/v1.20.0/google/genai/types.py
- Vercel Hobby: https://vercel.com/docs/plans/hobby
- Render free limitations: https://render.com/docs/free
- Supabase pricing: https://supabase.com/pricing
- Supabase direct/session/transaction connections: https://supabase.com/docs/guides/database/connecting-to-postgres

BGE revision pinned: 5c38ec7c405ec4b44b94cc5a9bb96e735b38267a. Gemini allowlist is
intentionally narrow (gemini-2.5-flash); changing it requires current free-availability
review, not an automatic provider/model switch. Account quotas/billing cannot be
verified without the owner's account; don't hardcode advertised numeric quotas.
