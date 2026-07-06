# CampusCase Desk RAG Vector Upgrade

## What Changed

`search_rag` now supports local vector-style retrieval in addition to the previous keyword scorer.

The current implementation is dependency-free Python:

```text
knowledge/*.md
-> YAML frontmatter + body parsing
-> ## heading based chunks
-> TF-IDF sparse vectors
-> cosine similarity search
-> hybrid RRF merge with keyword search
-> MCP search_rag
```

This keeps Railway deployment simple while demonstrating the same architecture used by Vector DB based RAG.

## MCP Tools

`search_rag` now accepts:

```json
{
  "query": "실습 그만두면 학점은 어떻게 돼",
  "domain": "practicum",
  "case_type": "early_withdrawal",
  "mode": "hybrid",
  "limit": 5
}
```

Retrieval modes:

| Mode | Meaning |
|---|---|
| `hybrid` | Keyword scorer + local vector search, merged with reciprocal rank fusion |
| `vector` | Local TF-IDF/cosine vector search only |
| `keyword` | Previous deterministic keyword scorer |

`rag_vector_stats` returns index metadata:

```json
{
  "documents": 36,
  "chunks": 252,
  "terms": 10825,
  "backend": "local_vector_tfidf",
  "source_type": "synthetic_demo"
}
```

## Why This Helps

Keyword search works well when the user uses the same terms as the document.

Vector-style search helps when the user says the same thing differently:

```text
User: 실습 그만두면 학점은 어떻게 돼?
Document: 현장실습 중도 포기 처리 규정 / 현장실습 학점 인정 기준
```

The local vector layer also adds a small synonym map for common university operations terms:

```text
그만두다 -> 포기 / 중단 / early_withdrawal
서류 -> 증빙 / 문서
학부모 -> 보호자 / 개인정보 / 동의
중복수혜 -> duplicate_award
```

## Future Upgrade Path

The current `scripts/rag_vector_store.py` is intentionally small. It can be replaced by a full vector database without changing Slack tool names.

Recommended production path:

```text
Markdown source documents
-> LlamaIndex or LangChain loader
-> chunking + metadata extraction
-> embedding model
-> Vector DB
-> MCP search_rag
-> Slackbot
```

Recommended options:

| Layer | Good choices |
|---|---|
| RAG framework | LlamaIndex for RAG-first indexing, LangChain for agent/tool composition |
| Workflow | LangGraph for multi-step case -> policy -> approval orchestration |
| Vector DB | Qdrant, Chroma, pgvector, Pinecone, Weaviate |
| Metadata DB | Railway MySQL for cases/tasks/approvals/documents |

## Suggested Next Version

1. Add an embedding provider.
2. Persist chunks and embeddings in Qdrant or pgvector.
3. Keep Railway MySQL for operational metadata.
4. Add a `case_id` aware retriever:

```text
case_id
-> case_type/domain from MySQL
-> related_rag_paths
-> metadata-filtered vector search
-> grounded answer
```

5. Add RAG eval questions for synonym-heavy cases:

```text
실습 그만두면 학점은 어떻게 돼?
장학금 두 개 받으면 문제돼?
학부모가 성적 물어보면 알려줘도 돼?
비자 서류 빠진 유학생 케이스 찾아줘.
```

## Verification

```bash
python3 scripts/smoke_test_mcp.py
python3 scripts/verify_rag_refs.py
python3 scripts/validate_data.py
```

Expected:

```text
smoke_test_mcp.py  -> ok
verify_rag_refs.py -> ok
validate_data.py   -> ok
```
