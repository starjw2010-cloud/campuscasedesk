# CampusFlow / CampusCase Desk — Codex 구현 지시서 v2 (synthetic_demo)
# ※ 데이터·RAG 콘텐츠는 이미 생성 완료. Codex는 "구현(인덱싱·도구·배포)"만 한다.

## 0. 왜 (아키텍처 의도)
두 MCP 역할 분리: (A) CampusFlow RAG = "규칙이 무엇인가"(규정/절차 문서 검색) / (B) CampusCase Desk = "지금 무슨 일"(운영 케이스 현황).
교차참조: case.related_rag_paths ↔ rag.applies_to_case_types. Slack 스킬/작업이 현황(Case Desk)+근거(RAG)를 함께 호출.

## 1. ★ 이미 존재함 — 재생성/덮어쓰기 금지, 그대로 사용
- data/: cases.jsonl(84) tasks(213) approvals(60) documents(202) relationships(1661) slack_threads(160) + users/channels/canvases/students/workspace_map.json
- knowledge/: 도메인별 규정·절차 문서 36개(.md, frontmatter 포함) + index.json (메니페스트)
- scripts/: store.py, mcp_adapter.py(Case Desk 도구), validate_data.py, verify_integrity.py, verify_rag_refs.py (둘 다 통과 상태)
- 생성기: generate_campusflow.py(데이터), generate_rag_kb.py(RAG), seed_campusflow_slack.py / seed_case_threads.py / rename_channels_kr.py(Slack 반영 완료)
- Slack 반영 완료: 케이스-* 한국어 채널 8 + 캔버스 24 + 케이스 리스트 6 + 스레드/문서 시딩
- 불변값: 도메인 6(practicum/scholarship/academic/complaint/international/student_success), 채널 한국어 "케이스-*", source_type=synthetic_demo, 학생 PII 마스킹

## 2. CampusFlow RAG MCP — ★구현만 (콘텐츠 작성 X)
이미 만들어진 knowledge/*.md(36) + knowledge/index.json 을 로드해 검색/서빙하는 MCP 서버를 구현하라.
- 로드: knowledge/index.json 으로 문서 목록, 각 .md의 YAML frontmatter(doc_id,domain,title,applies_to_case_types) 파싱 + 본문 청킹(## 헤더 단위)
- 도구:
  - search_rag(query, domain=all, limit): 키워드+임베딩 하이브리드, 응답에 path·title·도메인·발췌·applies_to_case_types 포함
  - get_doc(path): 문서 전문 반환
  - list_docs(domain): 도메인별 문서 목록
- 응답에는 항상 출처 path 포함(스킬이 case→rag 연결 추적 가능하도록)
- 검증: python3 scripts/verify_rag_refs.py 가 통과 유지(케이스의 35개 참조 경로가 전부 존재). 새 문서 추가 시 index.json도 갱신.

## 3. CampusCase Desk MCP — 도구 확장 (데이터는 그대로)
mcp_adapter.py에 도구 추가(스킬/작업 지원):
- find_cases 필터 확장: owner_user_id, priority, risk_level, has_missing_documents, consent_on_file
- list_approvals_due_today(date): approvals.due_at==오늘 + 승인자별 그룹 (작업 T2)
- group_cases_by_owner(domain, filter) (작업 T3/T4)
- get_student_cases(student_ref|student_name)
- list_documents(case_id|status)  / get_rag_refs(case_id): related_rag_paths + (RAG MCP 호출해 요약)
- 회귀 금지: validate_data.py, verify_integrity.py 계속 통과(orphan 0, 볼륨 요건 유지)

## 4. 배포·연동
- 두 MCP 모두 HTTP JSON-RPC /mcp, GET /mcp/health, Railway 배포, MCP_AUTH_MODE=no_auth
- Slack 커넥터 2개 등록(현황=Case Desk, 근거=RAG). 스킬/작업이 둘을 함께 사용.

## 5. 인수 기준
1) verify_integrity.py + verify_rag_refs.py 통과(현 상태 유지)
2) RAG MCP: search_rag로 "장학 중복수혜 규정" → scholarship/duplicate-award.md 반환
3) Case Desk MCP: list_approvals_due_today / find_cases(has_missing_documents) 동작
4) E2E: "김하늘 현장실습 중도포기 어디까지?"(Case Desk) + "처리 규정 근거?"(RAG early-withdrawal.md)
5) 전부 synthetic_demo, PII 마스킹 유지

## 6. 주의
RAG 경로를 바꾸면 data/cases.jsonl의 related_rag_paths도 동시 갱신 후 verify_rag_refs.py 재검증할 것.
