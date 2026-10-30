# Local PostgreSQL without a paid container runtime

Mode A supports PostgreSQL 16 and pgvector 0.8.0. Docker Compose pins these in
`compose.yaml`; you can use free Docker Engine on Linux or compatible Podman tooling.
Native alternatives need no cloud account or credit card.

On macOS, install native PostgreSQL 16 with Homebrew or Postgres.app and install
pgvector for **that exact server major/version prefix**. On Linux use your distribution's
PostgreSQL 16 / pgvector package or compile pgvector tag v0.8.0 using the server's
`pg_config`. Follow the official [pgvector installation instructions](https://github.com/pgvector/pgvector#installation).
Use pg_config --sharedir and --pkglibdir to verify extension control/SQL/library paths;
a pgvector build for PostgreSQL 17 is not interchangeable with PostgreSQL 16.

Initialize a fresh cluster with UTF-8 (not SQL_ASCII):

```sh
initdb -D .pgdata -U rgi -A scram-sha-256 -W --encoding=UTF8 --locale=C
pg_ctl -D .pgdata -l .data/postgres.log -o '-h 127.0.0.1 -p 5433' start
createdb -h 127.0.0.1 -p 5433 -U rgi rgi
```

Create `.data` before using that log path. Use a local password matching your `.env`;
never reuse these example credentials on a public database. Migration 001 creates
`vector` and requires database privileges to install the extension; application data
access can use a less privileged role afterward. `uv run alembic upgrade head`, then
`uv run python scripts/setup_checkpoints.py`. The saver needs table create privileges
only at setup time, then normal checkpoint data privileges at runtime.

Check `SELECT extversion FROM pg_extension WHERE extname='vector';` and the health API.
If API is online but worker offline, start the worker separately with the same database,
file-storage directory and processing settings. Do not assume healthy API means a worker.

This build environment's native initdb was denied a System V shared-memory operation
by sandbox policy. Docker daemon was also offline. Those are environment limitations,
not permission to replace database integration tests with SQLite. Run integration
checks on a host that permits PostgreSQL processes.

Defaults: 20 MB/PDF, 200 pages, 50 papers/collection, CPU embedding batches of 8,
Docling 2 parser threads, OCR disabled. Those are starting bounds, not measured maximum
capacity. First-use parser/embedding downloads need Internet/disk; the application runs
locally after assets are cached. No large generative model is automatically downloaded.
The full worker dependency set includes CPU PyTorch/Docling and is much larger than the
API extra. Inspect `scripts/measure_pipeline.py` outputs for your own laptop before large
batches. Memory capacity on this build host was unavailable to sandbox introspection.

To stop: Ctrl-C API/worker/frontend; `docker compose stop db` or `pg_ctl -D .pgdata stop`.
To back up: `pg_dump "$RGI_DATABASE_URL" > .data/backup.sql` plus copy `.data/pdf` and
`.data/parsed`. Keep backups private. Avoid `docker compose down -v` unless intentionally
discarding the database. Recreate checkpoints only from backup or reviewed migrations.

Model assets are kept under `.data/models` by default (`HF_HOME`/`TORCH_HOME` can be
explicitly overridden). `uv run python scripts/prefetch_assets.py` explicitly populates
BGE and OCR-off Docling caches before starting jobs. It needs Internet for the first
fetch and never downloads a generative model. An incomplete BGE snapshot fails instead
of letting SentenceTransformers construct a different pooling model silently.
