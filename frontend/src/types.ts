export type Citation = { evidence_id: string; quote: string };
export type Passage = {
  id: string;
  version_id: string;
  paper_id: string;
  title: string;
  heading: string;
  text: string;
  page: number;
  ordinal: number;
  item_ids: string[];
  boxes: {
    page: number;
    bbox: { l: number; t: number; r: number; b: number; coord_origin?: string };
  }[];
  pdf_url?: string;
  keyword_rank?: number | null;
  vector_rank?: number | null;
  fused_rank?: number;
  fused_score?: number;
};
export type Gap = {
  id: string;
  description: string;
  kind: string;
  significance: string;
  citations: Citation[];
  concerns: string;
};
export type Review = {
  gap_id: string;
  disposition: string;
  rationale: string;
  counterevidence: Citation[];
  unresolved: string;
};
export type Matrix = {
  paper_id: string;
  methods: string;
  datasets: string;
  baselines: string;
  metrics: string;
  conditions: string;
  results: string;
  limitations: string;
  citations: Citation[];
};
export type ResearchResult = {
  evidence: Passage[];
  queries: string[];
  coverage: string[];
  claims: {
    text: string;
    category: string;
    citations: Citation[];
    support: string;
  }[];
  matrix: Matrix[];
  gaps: Gap[];
  reviews: Review[];
  support_reviews: { claim_index: number; judgment: string; reason: string }[];
  experiments: Record<string, string>[];
  summary?: string;
};
export type Run = {
  id: string;
  collection_id: string;
  question: string;
  scope: string;
  mode: string;
  provider: string;
  model?: string;
  provenance: string;
  status: string;
  calls: number;
  tokens: number;
  usage_unknown: boolean;
  reserved_tokens?: number;
  tool_calls?: number;
  manifest: {
    version_id: string;
    paper_id: string;
    title: string;
    sha256: string;
    processing_id: string;
    embedding_id: string;
  }[];
  config?: { budget: Record<string, number> };
  created_at: string | null;
  error?: string;
  events?: {
    id?: number;
    node: string;
    kind: string;
    data: {
      summary?: string;
      message?: string;
      arguments?: Record<string, unknown>;
      evidence_ids?: string[];
    };
    duration_ms: number | null;
    created_at: string | null;
  }[];
  result?: ResearchResult;
  report?: string;
};
export type Collection = { id: string; name: string; scope: string };
export type Paper = {
  id: string;
  paper_id: string;
  title: string;
  sha256: string;
  status: string;
  processing_id: string;
  error?: string;
  warnings: string[];
  created_at: string;
};
