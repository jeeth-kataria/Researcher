CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE collections (
 id uuid PRIMARY KEY, name text NOT NULL, scope text NOT NULL DEFAULT '',
 owner_id text NOT NULL DEFAULT 'local-owner', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE papers (
 id uuid PRIMARY KEY, collection_id uuid NOT NULL REFERENCES collections(id), title text NOT NULL,
 source_url text, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(collection_id,title)
);
CREATE TABLE document_versions (
 id uuid PRIMARY KEY, paper_id uuid NOT NULL REFERENCES papers(id), sha256 text NOT NULL,
 storage_key text NOT NULL, processing_id text NOT NULL, parser text NOT NULL,
 embedding_id text NOT NULL, status text NOT NULL DEFAULT 'queued', error text,
 warnings jsonb NOT NULL DEFAULT '[]', artifact_key text, created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(paper_id,sha256,processing_id)
);
CREATE TABLE passages (
 id uuid PRIMARY KEY, version_id uuid NOT NULL REFERENCES document_versions(id), ordinal int NOT NULL,
 heading text NOT NULL, text text NOT NULL, page int NOT NULL, item_ids jsonb NOT NULL,
 boxes jsonb NOT NULL DEFAULT '[]', token_count int NOT NULL CHECK(token_count <= 512),
 embedding vector(384) NOT NULL,
 search tsvector GENERATED ALWAYS AS (to_tsvector('english', heading || ' ' || text)) STORED,
 UNIQUE(version_id,ordinal)
);
CREATE INDEX passage_search ON passages USING gin(search);
CREATE INDEX passage_version ON passages(version_id);
CREATE INDEX paper_collection ON papers(collection_id);
CREATE TABLE runs (
 id uuid PRIMARY KEY, collection_id uuid NOT NULL REFERENCES collections(id), question text NOT NULL,
 scope text NOT NULL, mode text NOT NULL, provider text NOT NULL, model text NOT NULL,
 provenance text NOT NULL, manifest jsonb NOT NULL, config jsonb NOT NULL,
 status text NOT NULL DEFAULT 'queued', cancel_requested boolean NOT NULL DEFAULT false,
 calls int NOT NULL DEFAULT 0, tokens int NOT NULL DEFAULT 0, usage_unknown boolean NOT NULL DEFAULT false,
 reserved_tokens int NOT NULL DEFAULT 0, tool_calls int NOT NULL DEFAULT 0,
 result jsonb, report text, error text,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE jobs (
 id uuid PRIMARY KEY, kind text NOT NULL CHECK(kind IN ('ingest','research')), target_id uuid NOT NULL,
 status text NOT NULL DEFAULT 'queued', owner text, lease_until timestamptz,
 attempts int NOT NULL DEFAULT 0, available_at timestamptz NOT NULL DEFAULT now(), error text,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(kind,target_id)
);
CREATE INDEX job_dispatch ON jobs(status,available_at,lease_until);
CREATE TABLE workers (id text PRIMARY KEY, heartbeat_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE events (
 id bigserial PRIMARY KEY, run_id uuid NOT NULL REFERENCES runs(id), node text NOT NULL,
 kind text NOT NULL, data jsonb NOT NULL, duration_ms int, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX event_run ON events(run_id,id);
CREATE TABLE artifacts (
 run_id uuid NOT NULL REFERENCES runs(id), role text NOT NULL, payload jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(run_id,role)
);
CREATE TABLE llm_calls (
 cache_key text PRIMARY KEY, run_id uuid NOT NULL REFERENCES runs(id), role text NOT NULL,
 status text NOT NULL, response jsonb, input_tokens int, output_tokens int,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE extraction_cache (
 cache_key text PRIMARY KEY, payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
