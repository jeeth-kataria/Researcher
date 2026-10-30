"""CPU embeddings with explicit preprocessing identity and no silent truncation."""

import hashlib
import math
import re
from functools import lru_cache
from .config import settings, configure_model_cache

MODEL = "BAAI/bge-small-en-v1.5"
REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
PREPROCESS = "heading-space-text-v1"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class FixtureEmbedder:
    """Deterministic lexical hashes ONLY for plumbing tests, not semantic research."""

    identity = "fixture-hash-384-v1"
    limit = 512

    def tokens(self, text):
        return re.findall(r"\w+|[^\w\s]", text.lower())

    def count(self, text):
        return len(self.tokens(text)) + 2

    def encode(self, texts, query=False):
        vectors = []
        for text in texts:
            if self.count(text) > self.limit:
                raise ValueError("Embedding input exceeds tokenizer window")
            vector = [0.0] * 384
            for token in self.tokens(text):
                idx = int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], "big") % 384
                vector[idx] += 1
            length = math.sqrt(sum(v * v for v in vector)) or 1
            vectors.append([v / length for v in vector])
        return vectors


class BGEEmbedder:
    limit = 512
    identity = f"{MODEL}@{REVISION}:{PREPROCESS}"

    def __init__(self):
        configure_model_cache()
        from sentence_transformers import SentenceTransformer
        from huggingface_hub import snapshot_download
        from pathlib import Path

        snapshot = Path(
            snapshot_download(
                repo_id=MODEL,
                revision=REVISION,
                allow_patterns=[
                    "modules.json",
                    "config.json",
                    "config_sentence_transformers.json",
                    "sentence_bert_config.json",
                    "model.safetensors",
                    "tokenizer.json",
                    "tokenizer_config.json",
                    "special_tokens_map.json",
                    "vocab.txt",
                    "1_Pooling/config.json",
                ],
            )
        )
        required = ("modules.json", "model.safetensors", "1_Pooling/config.json")
        if not all((snapshot / item).is_file() for item in required):
            raise ValueError("Incomplete pinned BGE snapshot; refusing automatic pooling/model fallback")
        self.model = SentenceTransformer(
            str(snapshot), device="cpu", local_files_only=True, trust_remote_code=False
        )
        self.model.max_seq_length = self.limit
        self.tokenizer = self.model.tokenizer

    def count(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=True, truncation=False))

    def encode(self, texts, query=False):
        inputs = [QUERY_PREFIX + t if query else t for t in texts]
        for text in inputs:
            if self.count(text) > self.limit:
                raise ValueError("Input including heading/query prefix exceeds 512 BGE tokens; shorten it")
        values = self.model.encode(inputs, batch_size=8, normalize_embeddings=True, show_progress_bar=False)
        if values.shape[1] != 384:
            raise ValueError("Embedding dimension mismatch")
        return values.tolist()


@lru_cache
def embedder():
    if settings().embedder == "fixture":
        return FixtureEmbedder()
    if settings().embedder == "bge":
        return BGEEmbedder()
    raise ValueError("Unknown embedder; no automatic fallback")


def embedding_identity():
    return FixtureEmbedder.identity if settings().embedder == "fixture" else BGEEmbedder.identity


def vector_json(vector):
    if len(vector) != 384 or not all(math.isfinite(v) for v in vector):
        raise ValueError("Invalid embedding")
    return "[" + ",".join(str(float(v)) for v in vector) + "]"
