# CampusCase Desk MariaDB Integration

이 문서는 CampusCase Desk MCP를 JSONL 데모 저장소에서 MariaDB 관계형 저장소로 확장하는 방법을 설명합니다.

## 지금 다운로드가 필요한가?

아직은 필요 없습니다.

이번 단계에서 추가한 것은 MariaDB 설치가 아니라, 나중에 MariaDB가 준비되면 바로 연결할 수 있는 준비물입니다.

- MariaDB schema
- JSONL -> MariaDB import script
- `DATA_BACKEND=jsonl|mariadb` 저장소 전환 구조
- RAG 문서 metadata import

기본값은 여전히 JSONL입니다.

```text
DATA_BACKEND=jsonl
```

따라서 현재 Slack MCP 데모는 그대로 동작합니다.

## Railway 연결 상태

Railway 프로젝트에는 MySQL 서비스가 추가되어 있습니다.

```text
Railway Database: MySQL
Connected app service: campuscasedesk
DATA_BACKEND=mariadb
MARIADB_URL=${{MySQL.MYSQL_URL}}
IMPORT_MARIADB_ON_START=true
```

Railway가 제공하는 database 옵션은 `mysql`이며, 이번 MCP에서는 MariaDB/MySQL wire protocol 호환 connector로 연결합니다.

## 추가된 파일

```text
database/mariadb_schema.sql
scripts/mariadb_store.py
scripts/import_mariadb.py
MARIADB_INTEGRATION.md
```

## 목표 아키텍처

```text
Slack / Slackbot
  -> MCP Server
  -> store.py
  -> DATA_BACKEND=jsonl     # 현재 데모 기본값
  -> DATA_BACKEND=mariadb   # 실제 운영형 DB 연결
  -> MariaDB
```

MCP 도구 이름은 바꾸지 않습니다.

```text
find_cases
get_case_detail
list_documents
list_approvals_due_today
get_rag_refs
search_rag
```

뒤쪽 저장소만 JSONL에서 MariaDB로 바뀝니다.

## MariaDB 연결 방식

둘 중 하나를 사용합니다.

### 1. URL 방식

```bash
export DATA_BACKEND=mariadb
export MARIADB_URL='mysql://user:password@host:3306/campusflow'
```

Railway MySQL/MariaDB 계열 플러그인이나 managed DB가 URL을 주면 이 방식이 편합니다.

### 2. 개별 변수 방식

```bash
export DATA_BACKEND=mariadb
export MARIADB_HOST=127.0.0.1
export MARIADB_PORT=3306
export MARIADB_USER=root
export MARIADB_PASSWORD=''
export MARIADB_DATABASE=campusflow
```

## Import

MariaDB 서버가 준비된 뒤 실행합니다.

```bash
cd /Volumes/jee_insight/codex/campuscasedesk
python3 scripts/import_mariadb.py
```

이 스크립트가 하는 일:

1. database가 없으면 생성
2. `database/mariadb_schema.sql` 적용
3. `data/*.json`, `data/*.jsonl` import
4. `knowledge/index.json`과 markdown RAG 문서 metadata import

Railway에서는 `IMPORT_MARIADB_ON_START=true`일 때 app startup에서 같은 import가 자동 실행됩니다.

## 테이블

주요 테이블:

```text
users
students
channels
canvases
cases
tasks
approvals
documents
relationships
slack_threads
rag_documents
workspace_map
audit_logs
```

운영 조회용 view:

```text
case_document_summary
approval_due_summary
```

## Schema 설계 원칙

각 테이블은 두 가지를 동시에 가집니다.

1. 자주 조회하는 관계형 컬럼
2. 원본 JSON 전체를 담는 `payload`

예:

```text
cases.domain
cases.status
cases.owner_user_id
cases.risk_level
cases.payload
```

이렇게 하면 SQL 조회와 원본 MCP 응답 호환성을 모두 유지할 수 있습니다.

## 검증

MariaDB가 없는 현재 상태에서는 JSONL backend 검증만 돌립니다.

```bash
python3 scripts/validate_data.py
python3 scripts/verify_integrity.py
python3 scripts/verify_rag_refs.py
python3 scripts/smoke_test_mcp.py
```

MariaDB 준비 후:

```bash
DATA_BACKEND=mariadb python3 scripts/smoke_test_mcp.py
```

## 운영 전 주의

현재 데이터는 synthetic demo입니다.

```text
source_type=synthetic_demo
```

실제 고객 데이터로 전환할 때는 반드시 아래가 필요합니다.

- Slack Identity Auth 또는 OAuth
- DB network allowlist
- TLS connection
- least privilege DB user
- audit_logs 기록
- 개인정보 마스킹
- backup/restore 정책
