CREATE TABLE collections (
 id text PRIMARY KEY, name text NOT NULL, scope text NOT NULL DEFAULT '',
 owner_id text NOT NULL DEFAULT 'local-owner', created_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE papers (
 id text PRIMARY KEY, collection_id text NOT NULL REFERENCES collections(id), title text NOT NULL,
 source_url text, created_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), UNIQUE(collection_id,title)
);
CREATE TABLE document_versions (
 id text PRIMARY KEY, paper_id text NOT NULL REFERENCES papers(id), sha256 text NOT NULL,
 storage_key text NOT NULL, processing_id text NOT NULL, parser text NOT NULL,
 embedding_id text NOT NULL, status text NOT NULL DEFAULT 'queued', error text,
 warnings text NOT NULL DEFAULT '[]', artifact_key text, created_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 UNIQUE(paper_id,sha256,processing_id)
);
CREATE TABLE passages (
 id text PRIMARY KEY, version_id text NOT NULL REFERENCES document_versions(id), ordinal int NOT NULL,
 heading text NOT NULL, text text NOT NULL, page int NOT NULL, item_ids text NOT NULL,
 boxes text NOT NULL DEFAULT '[]', token_count int NOT NULL CHECK(token_count <= 512),
 embedding text NOT NULL CHECK(json_valid(embedding) AND json_array_length(embedding)=384),
 UNIQUE(version_id,ordinal)
);
CREATE VIRTUAL TABLE passage_fts USING fts5(heading,text,content='passages',content_rowid='rowid',tokenize='unicode61');
CREATE TRIGGER passage_insert AFTER INSERT ON passages BEGIN
 INSERT INTO passage_fts(rowid,heading,text) VALUES (new.rowid,new.heading,new.text);
END;
CREATE TRIGGER passage_delete AFTER DELETE ON passages BEGIN
 INSERT INTO passage_fts(passage_fts,rowid,heading,text) VALUES ('delete',old.rowid,old.heading,old.text);
END;
CREATE TRIGGER passage_update AFTER UPDATE OF heading,text ON passages BEGIN
 INSERT INTO passage_fts(passage_fts,rowid,heading,text) VALUES ('delete',old.rowid,old.heading,old.text);
 INSERT INTO passage_fts(rowid,heading,text) VALUES (new.rowid,new.heading,new.text);
END;
CREATE INDEX passage_version ON passages(version_id);
CREATE INDEX paper_collection ON papers(collection_id);
CREATE TABLE runs (
 id text PRIMARY KEY, collection_id text NOT NULL REFERENCES collections(id), question text NOT NULL,
 scope text NOT NULL, mode text NOT NULL, provider text NOT NULL, model text NOT NULL,
 provenance text NOT NULL, manifest text NOT NULL, config text NOT NULL,
 status text NOT NULL DEFAULT 'queued', cancel_requested boolean NOT NULL DEFAULT false,
 calls int NOT NULL DEFAULT 0, tokens int NOT NULL DEFAULT 0, usage_unknown boolean NOT NULL DEFAULT false,
 reserved_tokens int NOT NULL DEFAULT 0, tool_calls int NOT NULL DEFAULT 0,
 result text, report text, error text,
 created_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), updated_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE jobs (
 id text PRIMARY KEY, kind text NOT NULL CHECK(kind IN ('ingest','research')), target_id text NOT NULL,
 status text NOT NULL DEFAULT 'queued', owner text, lease_until text,
 attempts int NOT NULL DEFAULT 0, available_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), error text,
 created_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), updated_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
 UNIQUE(kind,target_id)
);
CREATE INDEX job_dispatch ON jobs(status,available_at,lease_until);
CREATE TABLE workers (id text PRIMARY KEY, heartbeat_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
CREATE TABLE events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, run_id text NOT NULL REFERENCES runs(id), node text NOT NULL,
 kind text NOT NULL, data text NOT NULL, duration_ms int, created_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX event_run ON events(run_id,id);
CREATE TABLE artifacts (
 run_id text NOT NULL REFERENCES runs(id), role text NOT NULL, payload text NOT NULL,
 created_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), PRIMARY KEY(run_id,role)
);
CREATE TABLE llm_calls (
 cache_key text PRIMARY KEY, run_id text NOT NULL REFERENCES runs(id), role text NOT NULL,
 status text NOT NULL, response text, input_tokens int, output_tokens int,
 created_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')), updated_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE extraction_cache (
 cache_key text PRIMARY KEY, payload text NOT NULL, created_at text NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
