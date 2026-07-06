from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
INDEX_PATH = KNOWLEDGE / "index.json"


def _parse_scalar(value: str):
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip('"').strip("'") for item in inner.split(",")]
    return value


def _parse_frontmatter(text: str):
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :].lstrip()
    meta = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = _parse_scalar(value)
    return meta, body


def _chunks(body: str):
    parts = re.split(r"(?m)^(## .+)$", body)
    if len(parts) == 1:
        return [{"heading": "", "text": body.strip()}]
    chunks = []
    intro = parts[0].strip()
    if intro:
        chunks.append({"heading": "", "text": intro})
    for i in range(1, len(parts), 2):
        heading = parts[i].strip("# ").strip()
        text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if text:
            chunks.append({"heading": heading, "text": text})
    return chunks


def _normalize(text: str):
    text = str(text or "").lower()
    return re.sub(r"[\s·_\-/]+", "", text)


def _tokens(text: str):
    raw = re.split(r"[\s,.;:()\[\]{}|/\\#*`\"'<>!?]+", str(text or "").lower())
    tokens = [token for token in raw if len(token) >= 2]
    compact = _normalize(text)
    if compact and compact not in tokens:
        tokens.append(compact)
    return tokens


@lru_cache(maxsize=1)
def load_index():
    if not INDEX_PATH.exists():
        return {"source_type": "synthetic_demo", "count": 0, "documents": []}
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_documents():
    docs = []
    for item in load_index().get("documents", []):
        path = item.get("path", "")
        full_path = ROOT / path
        if not path or not full_path.exists():
            continue
        raw = full_path.read_text(encoding="utf-8")
        frontmatter, body = _parse_frontmatter(raw)
        doc = dict(item)
        doc.update({key: value for key, value in frontmatter.items() if value not in (None, "")})
        doc["path"] = path
        doc["body"] = body
        doc["chunks"] = _chunks(body)
        docs.append(doc)
    return docs


def list_docs(domain="all"):
    docs = load_documents()
    if domain and domain != "all":
        docs = [doc for doc in docs if doc.get("domain") == domain]
    return [
        {
            "path": doc.get("path"),
            "doc_id": doc.get("doc_id"),
            "domain": doc.get("domain"),
            "title": doc.get("title"),
            "applies_to_case_types": doc.get("applies_to_case_types", []),
            "source_type": doc.get("source_type", "synthetic_demo"),
        }
        for doc in docs
    ]


def get_doc(path: str):
    normalized = str(path or "").strip()
    for doc in load_documents():
        if doc.get("path") == normalized:
            return doc
    return None


def _keyword_search(query: str, domain="all", limit=5):
    query = str(query or "").strip()
    query_tokens = _tokens(query)
    query_compact = _normalize(query)
    results = []
    for doc in load_documents():
        if domain and domain != "all" and doc.get("domain") != domain:
            continue
        best_chunk = {"heading": "", "text": doc.get("body", "")[:500]}
        best_score = 0
        for chunk in doc.get("chunks", []):
            haystack = " ".join(
                [
                    doc.get("title", ""),
                    doc.get("domain", ""),
                    " ".join(doc.get("applies_to_case_types", [])),
                    chunk.get("heading", ""),
                    chunk.get("text", ""),
                ]
            )
            haystack_lower = haystack.lower()
            haystack_compact = _normalize(haystack)
            score = 0
            for token in query_tokens:
                if token in haystack_lower or token in haystack_compact:
                    score += 3 if token == query_compact else 1
            if query_compact and query_compact in haystack_compact:
                score += 6
            if score > best_score:
                best_score = score
                best_chunk = chunk
        if best_score:
            excerpt = best_chunk.get("text", "").replace("\n", " ").strip()
            if len(excerpt) > 320:
                excerpt = excerpt[:317].rstrip() + "..."
            results.append(
                {
                    "score": best_score,
                    "path": doc.get("path"),
                    "doc_id": doc.get("doc_id"),
                    "domain": doc.get("domain"),
                    "title": doc.get("title"),
                    "heading": best_chunk.get("heading", ""),
                    "excerpt": excerpt,
                    "applies_to_case_types": doc.get("applies_to_case_types", []),
                    "source_type": doc.get("source_type", "synthetic_demo"),
                }
            )
    results.sort(key=lambda item: (-item["score"], item["path"]))
    return results[: int(limit or 5)]


def _rrf_merge(keyword_results, vector_results, limit):
    merged = {}
    for source, weight, rows in [("keyword", 1.0, keyword_results), ("vector", 1.2, vector_results)]:
        for rank, row in enumerate(rows, start=1):
            key = row.get("chunk_id") or f"{row.get('path')}#{row.get('heading', '')}"
            if key not in merged:
                merged[key] = dict(row)
                merged[key]["score"] = 0.0
                merged[key]["retrieval_sources"] = []
            merged[key]["score"] += weight * (1.0 / (60 + rank))
            merged[key]["retrieval_sources"].append(source)
            if source == "vector":
                merged[key]["vector_score"] = row.get("score")
            else:
                merged[key]["keyword_score"] = row.get("score")
    results = list(merged.values())
    for row in results:
        row["score"] = round(row["score"], 6)
        row["retrieval"] = "hybrid_rrf"
    results.sort(key=lambda item: (-item["score"], item["path"], item.get("heading", "")))
    return results[: int(limit or 5)]


def search_rag(query: str, domain="all", limit=5, mode="hybrid", case_type=""):
    mode = (mode or "hybrid").strip().lower()
    if mode == "keyword":
        results = _keyword_search(query, domain=domain, limit=limit)
        for row in results:
            row["retrieval"] = "keyword"
        return results
    try:
        import rag_vector_store
    except Exception:
        results = _keyword_search(query, domain=domain, limit=limit)
        for row in results:
            row["retrieval"] = "keyword_fallback"
        return results
    vector_results = rag_vector_store.search(query, domain=domain, limit=max(int(limit or 5) * 3, 10), case_type=case_type)
    if mode == "vector":
        return vector_results[: int(limit or 5)]
    keyword_results = _keyword_search(query, domain=domain, limit=max(int(limit or 5) * 3, 10))
    return _rrf_merge(keyword_results, vector_results, limit)


def vector_stats():
    try:
        import rag_vector_store

        return rag_vector_store.stats()
    except Exception as exc:
        return {"backend": "unavailable", "error": f"{type(exc).__name__}: {exc}"}
