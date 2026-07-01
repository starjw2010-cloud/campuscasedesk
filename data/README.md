# CampusCase Desk — 운영형 Seed Dataset (synthetic_demo)

한빛대학교 CampusFlow AI MCP/RAG 연계용 **합성 운영 데이터**입니다. 실제 개인정보를 포함하지 않으며 모든 레코드는 `source_type: synthetic_demo` 입니다.

생성: `python3 generate_campusflow.py` · 기준일 2026-07-01

## 도메인별 케이스
| 도메인 | 케이스 수 | 채널 |
|---|---|---|
| 현장실습 (`practicum`) | 14 | C_PRAC_OPS |
| 장학 (`scholarship`) | 14 | C_SCH_REVIEW |
| 학사 (`academic`) | 14 | C_ACAD_OPS |
| 민원 (`complaint`) | 14 | C_CIVIL_DESK |
| 유학생 (`international`) | 14 | C_INTL_SUPPORT |
| 학생성공 (`student_success`) | 14 | C_SUCCESS_CARE |

## 전체 수량
| 엔티티 | 수 |
|---|---|
| users | 28 |
| channels | 8 |
| students | 151 |
| cases | 84 |
| slack_threads | 160 |
| canvases | 24 |
| tasks | 213 |
| approvals | 60 |
| documents | 202 |
| relationships | 1661 |

## 파일
- `workspace_map.json` 메타·수량·ID 규칙
- `users.json` / `channels.json` / `students.json` / `canvases.json`
- `slack_threads.jsonl` / `cases.jsonl` / `tasks.jsonl` / `approvals.jsonl` / `documents.jsonl`
- `relationships.jsonl` 엔티티 간 관계(case↔student/owner/approver/channel/thread/canvas/document/rag, task/approval/document/thread→case)

## 무결성
`python3 scripts/verify_integrity.py` — orphan(case/thread/task/approval/document) 0, 모든 참조 유효해야 통과.
기존 `python3 scripts/validate_data.py`, MCP 어댑터(`scripts/mcp_adapter.py`)와 호환됩니다.
