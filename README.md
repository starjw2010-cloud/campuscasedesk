# CampusCase Desk MCP

대학 업무 케이스, 태스크, 승인, Slack 스레드/캔버스 맥락을 조회하는 synthetic demo MCP 서버입니다.

기존 `CampusFlow RAG MCP`가 규정과 절차 문서를 찾는다면, 이 서버는 실제 업무 케이스의 현재 상태와 후속 작업을 보여줍니다.

## Tools

Case Desk:

- `find_cases`
- `get_case_detail`
- `list_pending_tasks`
- `trace_slack_context`
- `create_task`
- `list_approvals_due_today`
- `group_cases_by_owner`
- `get_student_cases`
- `list_documents`
- `get_rag_refs`

Local RAG index:

- `search_rag`
- `get_doc`
- `list_docs`

`search_rag`, `get_doc`, `list_docs` load the existing `knowledge/*.md` corpus through `knowledge/index.json`.
No RAG content is generated at runtime.

## Local

```bash
python3 app.py
curl -s -X POST http://127.0.0.1:8771/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":"tools","method":"tools/list"}'
```

## Slack MCP

```text
Name: CampusCase Desk MCP
URL: https://<railway-url>/mcp
Auth type: No Auth
```

Set `MCP_AUTH_MODE=no_auth` for demo use.

## Verification

```bash
python3 scripts/validate_data.py
python3 scripts/verify_integrity.py
python3 scripts/verify_rag_refs.py
python3 scripts/smoke_test_mcp.py
```

## MariaDB

The default backend is still JSONL:

```text
DATA_BACKEND=jsonl
```

For an operating-system-like demo, the same MCP tools can be backed by MariaDB:

```text
DATA_BACKEND=mariadb
MARIADB_URL=mysql://user:password@host:3306/campusflow
```

See `MARIADB_INTEGRATION.md`.

### Local MariaDB with Docker

This repo includes a reproducible local MariaDB path for demos and reviewers.
It uses Docker Compose, so you do not need to install MariaDB directly on macOS.

```bash
docker compose up -d mariadb
python3 -m pip install -r requirements.txt
DATA_BACKEND=mariadb \
MARIADB_URL=mysql://campusflow:campusflow_dev@127.0.0.1:3307/campusflow \
python3 scripts/import_mariadb.py
DATA_BACKEND=mariadb \
MARIADB_URL=mysql://campusflow:campusflow_dev@127.0.0.1:3307/campusflow \
python3 scripts/check_mariadb_backend.py
```

Or run the bundled make target:

```bash
make local-db-demo
```

The local Docker database is exposed on host port `3307` to avoid collisions with a native MySQL/MariaDB running on `3306`.

Current enriched synthetic dataset:

```text
students      520
cases         360
tasks         1041
approvals     273
documents     868
threads       635
canvases       54
relationships 7186
```
