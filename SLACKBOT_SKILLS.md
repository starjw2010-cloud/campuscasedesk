# Slackbot 사용자 지정 스킬 프롬프트 5선 — CampusCase Desk MCP 활용

> Slackbot → 기술(스킬) → **사용자 지정으로 만들기** 에 아래 프롬프트를 그대로 붙여넣으세요.
> 전제: **CampusCase Desk MCP** 커넥터 연결됨(도구: find_cases, get_case_detail, list_pending_tasks, trace_slack_context, create_task).
> 규정·절차가 필요하면 **CampusFlow RAG MCP** 를 함께 사용. 모든 데이터는 synthetic_demo이며 학생 개인정보는 마스킹된 값만 노출.

---

## 1) 학장 아침 케이스 브리핑

```
스킬 이름: 학장 아침 브리핑
목적: 매일 아침 경영대학 학장에게 오늘 챙겨야 할 케이스를 한 화면으로 브리핑한다.
사용 도구: CampusCase Desk MCP 의 find_cases, list_pending_tasks (필요 시 trace_slack_context).
동작 순서:
1. find_cases 로 status=approval_pending 이면서 승인 마감(due_at)이 오늘인 케이스를 모은다.
2. find_cases 로 priority=urgent 또는 risk_level=high 인 케이스를 도메인(현장실습·장학·학사·민원·유학생·학생성공)별로 모은다.
3. list_pending_tasks 로 오늘·내일 마감인 대기 태스크를 우선순위순으로 추린다.
4. 미제출 서류(missing_documents)가 있는 케이스를 별도로 표시한다.
출력 형식(한국어 실무체, 불릿):
- 🔴 오늘 승인 처리 필요 N건 (case_id · 제목 · 담당 · 마감)
- ⚠️ 긴급/리스크 케이스 (도메인별)
- 📋 오늘 마감 태스크 Top 5
- 📎 서류 누락 케이스 요약
- 한 줄 코멘트: "오늘 가장 먼저 볼 것은 ___ 입니다."
주의: 학생 이름은 마스킹된 값(예: 김*늘)으로만 표기. 데이터는 synthetic_demo임을 하단에 한 줄 명시.
트리거: 매일 오전 8시 30분 또는 "오늘 브리핑" 요청 시.
```

---

## 2) 케이스 딥다이브 & 다음 액션 초안

```
스킬 이름: 케이스 딥다이브
목적: 특정 학생/케이스의 현재 상태와 막힌 지점을 정리하고, 담당자가 보낼 다음 액션 메시지 초안까지 만든다.
입력: 학생 이름 또는 case_id (예: "김하늘 현장실습", "case_prac_001").
사용 도구: find_cases → get_case_detail → trace_slack_context. 규정 근거는 케이스의 related_rag_paths 를 CampusFlow RAG MCP 로 조회.
동작 순서:
1. 입력으로 find_cases 해서 대상 케이스를 특정한다(여러 건이면 후보 목록을 먼저 보여주고 선택받는다).
2. get_case_detail 로 상태·우선순위·담당자(owner)·승인자(approver)·필요/제출/미제출 서류·다음 액션·태스크·승인 현황을 가져온다.
3. trace_slack_context 로 관련 채널·스레드·캔버스·타임라인을 가져온다.
4. related_rag_paths 의 규정을 근거로 "지금 막힌 이유 + 다음에 할 일"을 1~3개로 정리한다.
출력 형식:
- 한눈 요약: 상태 / 우선순위 / 담당 / 승인자 / 미제출 서류
- 진행 타임라인 (timeline)
- ✅ 다음 액션 체크리스트 (책임자·마감 포함)
- ✉️ 담당자/학생 안내 메시지 초안 (정중한 한국어 실무체)
- 🔗 근거: 관련 스레드 thread_id, 캔버스, RAG 경로
주의: 개인정보는 마스킹. 안내 메시지에는 학번/연락처 등 민감정보를 넣지 않는다. synthetic_demo 표기.
```

---

## 3) 오늘 처리할 승인 정리

```
스킬 이름: 오늘의 승인 큐
목적: 승인 대기(approval_pending) 건 중 오늘 처리해야 할 것만 골라 승인자별로 정리하고, 결재 요약을 만든다.
사용 도구: find_cases(status=approval_pending), get_case_detail (승인·근거 확인).
동작 순서:
1. find_cases 로 status=approval_pending 케이스를 전부 가져온다.
2. 각 케이스의 approvals 중 due_at(마감)이 '오늘'인 건만 필터한다.
3. approver_user_id(승인자) 기준으로 그룹핑하고, 도메인·우선순위 순으로 정렬한다.
4. 각 건의 승인 사유 요약 + 미제출 서류 여부 + 근거 RAG를 붙인다.
출력 형식:
- 승인자별 섹션 (예: 장학 담당 팀장 → N건)
  - case_id · 제목 · 우선순위 · 사유 한 줄 · 미제출서류 유무
- 하단: "지금 바로 승인 가능 vs 보완 필요" 분류
- 옵션: 사용자가 "처리 태스크 만들어줘" 하면 create_task 로 후속 태스크 생성.
주의: 장학금 중복 수혜처럼 규정 충돌이 의심되면 관련 RAG(예: knowledge/scholarship/duplicate-award.md)를 근거로 표시. synthetic_demo 표기.
트리거: "오늘 승인 뭐 처리해야 해?" 또는 매일 오전.
```

---

## 4) 도메인 리스크 모니터 (유학생·현장실습)

```
스킬 이름: 리스크 모니터
목적: 유학생 비자/체류, 현장실습 안전·보험 등 리스크가 큰 케이스를 담당자별로 묶고 근거 스레드와 함께 경보한다.
입력: 도메인 선택(기본: international, practicum) 또는 "전체".
사용 도구: find_cases(domain=...), trace_slack_context, list_pending_tasks.
동작 순서:
1. find_cases 로 해당 도메인에서 risk_level=high 또는 priority(urgent/high), 또는 missing_documents 가 있는 케이스를 모은다.
2. 유학생: 체류기간 만료 임박(stay_expiry)·비자 서류 누락(visa_document_missing)을 우선. 현장실습: 안전사고·보험 미가입·중도포기를 우선.
3. owner_user_id(담당자)별로 그룹핑한다.
4. 각 케이스에 trace_slack_context 로 근거 스레드(thread_id)와 캔버스를 연결한다.
출력 형식:
- 도메인 → 담당자별 묶음
  - case_id · 제목 · 리스크/우선순위 · 누락 서류 · 마감 · 근거 thread_id
- 🚨 즉시 조치 Top 5 (마감 임박순)
- 담당자별 한 줄 요청 문구
주의: 마스킹된 학생명만. 비자/체류 등은 민감하므로 수치·문서명 위주로 요약. synthetic_demo 표기.
트리거: "이번 주 리스크 높은 케이스 보여줘", 매주 월요일 오전.
```

---

## 5) 민원 응대 초안 + 개인정보 동의 점검

```
스킬 이름: 민원 응대 도우미
목적: 민원(complaint) 케이스에 대해 개인정보 제공 동의 여부를 먼저 점검하고, 규정에 맞는 안내문 초안을 만든다.
입력: 민원 키워드 또는 case_id (예: "학부모 성적 문의").
사용 도구: find_cases(domain=complaint), get_case_detail. 규정 근거는 RAG(knowledge/complaint/privacy-guideline.md, grade-info-policy.md) 사용.
동작 순서:
1. find_cases 로 대상 민원 케이스를 특정한다.
2. get_case_detail 에서 consent_on_file(개인정보 제공 동의) 값을 확인한다.
3. 동의가 없으면(consent_on_file=false): "개인정보 보호 사유로 제3자(학부모 등)에게 성적 등 정보를 제공할 수 없음"을 안내하는 정중한 거절·안내문 초안을 만든다. 본인 동의 절차(개인정보동의서 제출)를 함께 안내한다.
4. 동의가 있으면: 요청 범위 내에서 처리 절차와 다음 단계를 안내하는 초안을 만든다.
출력 형식:
- 케이스 요약 + 개인정보 동의 상태(있음/없음)
- ✉️ 민원 회신 초안 (한국어 공문 톤, 근거 규정 1줄 포함)
- ⚠️ 컴플라이언스 체크: 노출 금지 정보 목록(성적·학번·연락처 등)
- 다음 단계(동의서 수령 등)
주의: 절대 실제·미마스킹 개인정보를 본문에 넣지 않는다. 동의 없는 건은 정보 제공 대신 절차 안내만. synthetic_demo 표기.
트리거: "이 민원 답변 초안 만들어줘", "개인정보 동의 없는 성적 문의 처리해줘".
```

---

### 공통 팁 (5개 스킬 모두 적용)
- 데이터 출처는 **CampusCase Desk MCP**(케이스 현황) + **CampusFlow RAG MCP**(규정·절차). 현황은 전자, 근거는 후자.
- 학생 식별정보는 마스킹된 값(masked_name, student_no_masked)만 사용.
- 모든 결과 하단에 `※ 데이터: synthetic_demo` 표기.
- "후속 태스크 만들어줘" 요청 시 **create_task** 로 케이스에 태스크를 생성.
