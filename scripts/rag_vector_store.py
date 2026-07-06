from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from functools import lru_cache

import rag_store


SYNONYMS = {
    "그만": ["포기", "중단", "중도포기", "early_withdrawal"],
    "그만두": ["포기", "중단", "중도포기", "early_withdrawal"],
    "중단": ["포기", "중도포기", "early_withdrawal"],
    "철회": ["포기", "중도포기", "early_withdrawal"],
    "학점": ["학점인정", "credit", "credit_recognition"],
    "인정": ["학점인정", "credit_recognition"],
    "중복수혜": ["중복 수혜", "duplicate_award"],
    "중복": ["중복수혜", "duplicate_award"],
    "장학": ["장학금", "scholarship"],
    "비자": ["visa", "체류", "유학생"],
    "성적": ["grade", "학점", "성적문의"],
    "학부모": ["보호자", "개인정보", "동의"],
    "개인정보": ["privacy", "동의", "consent"],
    "서류": ["증빙", "문서", "documents"],
    "증빙": ["서류", "문서", "documents"],
    "승인": ["approval", "결재", "심사"],
    "마감": ["due", "기한", "deadline"],
    "상담": ["counseling", "학생성공"],
}


def _normalize(text: str) -> str:
    return re.sub(r"[\s·_\-/]+", "", str(text or "").lower())


def _word_tokens(text: str) -> list[str]:
    return [
        token
        for token in re.split(r"[\s,.;:()\[\]{}|/\\#*`\"'<>!?]+", str(text or "").lower())
        if len(token) >= 2
    ]


def _char_ngrams(text: str) -> list[str]:
    compact = _normalize(text)
    grams = []
    for size in (2, 3, 4):
        grams.extend(compact[i : i + size] for i in range(0, max(0, len(compact) - size + 1)))
    return grams


def _tokens(text: str) -> list[str]:
    tokens = _word_tokens(text)
    tokens.extend(_char_ngrams(text))
    compact = _normalize(text)
    for key, values in SYNONYMS.items():
        if key in compact or key in tokens:
            tokens.extend(values)
    return [token for token in tokens if token]


def _chunk_text(doc: dict, chunk: dict) -> str:
    return " ".join(
        [
            str(doc.get("title", "")),
            str(doc.get("domain", "")),
            " ".join(doc.get("applies_to_case_types", []) or []),
            str(chunk.get("heading", "")),
            str(chunk.get("text", "")),
        ]
    )


def _excerpt(text: str, limit: int = 320) -> str:
    clean = str(text or "").replace("\n", " ").strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    counts = Counter(tokens)
    total = sum(counts.values()) or 1
    vector = {term: (count / total) * idf.get(term, 1.0) for term, count in counts.items()}
    norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
    return {term: value / norm for term, value in vector.items()}


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(term, 0.0) for term, value in left.items())


@lru_cache(maxsize=1)
def build_index():
    rows = []
    document_frequency = defaultdict(int)
    for doc in rag_store.load_documents():
        for index, chunk in enumerate(doc.get("chunks", [])):
            text = _chunk_text(doc, chunk)
            tokens = _tokens(text)
            row = {
                "chunk_id": f"{doc.get('path')}#{index}",
                "path": doc.get("path"),
                "doc_id": doc.get("doc_id"),
                "domain": doc.get("domain"),
                "title": doc.get("title"),
                "heading": chunk.get("heading", ""),
                "text": chunk.get("text", ""),
                "applies_to_case_types": doc.get("applies_to_case_types", []),
                "source_type": doc.get("source_type", "synthetic_demo"),
                "tokens": tokens,
            }
            rows.append(row)
            for token in set(tokens):
                document_frequency[token] += 1
    count = len(rows) or 1
    idf = {term: math.log((count + 1) / (freq + 1)) + 1.0 for term, freq in document_frequency.items()}
    for row in rows:
        row["vector"] = _tfidf_vector(row.pop("tokens"), idf)
    return {"count": len(rows), "idf": idf, "rows": rows}


def search(query: str, domain: str = "all", limit: int = 5, case_type: str = ""):
    query = str(query or "").strip()
    if not query:
        return []
    index = build_index()
    query_vector = _tfidf_vector(_tokens(query), index["idf"])
    results = []
    for row in index["rows"]:
        if domain and domain != "all" and row.get("domain") != domain:
            continue
        if case_type and case_type not in (row.get("applies_to_case_types") or []):
            continue
        score = _cosine(query_vector, row["vector"])
        if score <= 0:
            continue
        results.append(
            {
                "score": round(score, 6),
                "path": row.get("path"),
                "doc_id": row.get("doc_id"),
                "chunk_id": row.get("chunk_id"),
                "domain": row.get("domain"),
                "title": row.get("title"),
                "heading": row.get("heading", ""),
                "excerpt": _excerpt(row.get("text", "")),
                "applies_to_case_types": row.get("applies_to_case_types", []),
                "source_type": row.get("source_type", "synthetic_demo"),
                "retrieval": "local_vector_tfidf",
            }
        )
    results.sort(key=lambda item: (-item["score"], item["path"], item.get("heading", "")))
    return results[: int(limit or 5)]


def stats():
    index = build_index()
    docs = rag_store.load_documents()
    return {
        "documents": len(docs),
        "chunks": index["count"],
        "terms": len(index["idf"]),
        "backend": "local_vector_tfidf",
        "source_type": "synthetic_demo",
    }
