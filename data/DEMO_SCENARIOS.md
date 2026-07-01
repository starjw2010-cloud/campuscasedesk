# CampusCase Desk — 데모 시나리오 20선 (synthetic_demo)

CampusFlow AI MCP(`find_cases`, `get_case_detail`, `list_pending_tasks`, `trace_slack_context`, `create_task`)로
응답 가능한 한국어 실무 질문 모음. 모든 데이터는 합성(synthetic_demo)입니다.

> 도메인: 현장실습(practicum)·장학(scholarship)·학사(academic)·민원(complaint)·유학생(international)·학생성공(student_success)

## 핵심 5선
1. **"김하늘 학생 현장실습 중도 포기 건 지금 어디까지 진행됐어?"**
   → `find_cases(query="김하늘 현장실습")` → `case_prac_001` → `get_case_detail` (상태 evidence_requested, 미제출 서류·다음 액션)
2. **"장학금 중복 수혜 승인 대기 건 중 오늘 처리해야 할 것만 보여줘"**
   → `find_cases(domain="scholarship", status="approval_pending")` (case_sch_001~003) → approvals 중 `due_at`=오늘 필터
3. **"학부모 성적 문의 민원 중 개인정보 동의가 없는 건 안내문 초안 만들어줘"**
   → `find_cases(domain="complaint", query="학부모 성적 문의")` → `consent_on_file=false` 케이스 → 안내문 생성
4. **"유학생 비자 서류 누락 케이스를 담당자별로 묶어서 알려줘"**
   → `find_cases(domain="international", query="비자 서류 누락")` → `owner_user_id` 기준 그룹핑
5. **"이번 주 현장실습 중 리스크 높은 케이스와 근거 스레드를 찾아줘"**
   → `find_cases(domain="practicum")` → `risk_level=high`/`priority=urgent` → `trace_slack_context`로 근거 thread

## 도메인별 추가 15선
6. "현장실습 보험 미가입 케이스 전부 보여주고, 미제출 서류가 뭔지 알려줘" (practicum / insurance_missing)
7. "실습기관 변경 요청 중 지도교수 확인서가 빠진 건은?" (practicum / site_change)
8. "장학 서류 미비로 보류된 케이스에 후속 태스크 하나 만들어줘" (scholarship → `create_task`)
9. "소득분위 확인이 필요한 장학 케이스 담당자가 누구야?" (scholarship / income_verification)
10. "성적 이의신청 중 검토중(in_review)인 건과 근거 RAG 경로를 알려줘" (academic / grade_appeal)
11. "휴학·복학 학적변동 케이스를 상태별로 요약해줘" (academic / leave·return)
12. "졸업요건 미충족 케이스의 졸업사정표 제출 여부 확인해줘" (academic / graduation_requirement)
13. "행정처리 지연 민원 중 우선순위 높은 건의 Slack 스레드를 열어줘" (complaint / processing_delay → `trace_slack_context`)
14. "개인정보 열람 요청 민원의 본인확인 서류 누락 건은?" (complaint / info_disclosure)
15. "체류기간 만료 임박 유학생 케이스를 마감일 순으로 보여줘" (international / stay_expiry)
16. "유학생 보험 미가입 케이스 담당자에게 처리 요청 태스크를 만들어줘" (international → `create_task`)
17. "학사경고 상담이 필요한 학생성공 케이스와 상담 동의 여부를 알려줘" (student_success / academic_warning_care)
18. "중도탈락 위험 높은 학생 케이스를 위험도순으로 정리해줘" (student_success / dropout_risk)
19. "내가(담당자) 처리할 대기 태스크를 마감 임박 순으로 보여줘" (`list_pending_tasks(owner_user_id=...)`)
20. "case_prac_001의 전체 맥락(태스크·승인·문서·스레드·캔버스)을 한 번에 보여줘" (`get_case_detail` + `trace_slack_context`)

## 참조 무결성 보장
- 모든 케이스: ≥1 스레드 · 담당자 · 다음 액션 · 근거(문서 또는 RAG)
- orphan(case/thread/task/approval/document) 0 — `python3 scripts/verify_integrity.py` 통과
- 관계 13종(case↔student/owner/approver/channel/thread/canvas/document/rag, task/approval/document/thread→case)
