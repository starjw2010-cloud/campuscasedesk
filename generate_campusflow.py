#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generate_campusflow.py — CampusCase Desk 운영형 synthetic seed dataset 생성기.

기존 MCP 어댑터(scripts/mcp_adapter.py) 스키마를 유지하면서 6개 도메인 운영 데이터를
대량 생성한다. 모든 엔티티는 stable id + 상호참조 + 참조 무결성 보장. 전부 synthetic_demo.

출력: data/{workspace_map.json, users.json, channels.json, slack_threads.jsonl,
              canvases.json, cases.jsonl, tasks.jsonl, approvals.jsonl,
              documents.jsonl, relationships.jsonl, README.md, DEMO_SCENARIOS.md}
사용: python3 generate_campusflow.py
"""
import json, random
from pathlib import Path
from datetime import datetime, timedelta

random.seed(20260701)
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)
SRC = "synthetic_demo"
NOW = datetime(2026, 7, 1, 9, 0, 0)          # 데모 기준 '오늘'
TODAY = NOW.date().isoformat()


def iso(dt): return dt.strftime("%Y-%m-%dT%H:%M:%S")
def back(days, hours=0): return NOW - timedelta(days=days, hours=hours)


# ───────────────────────── 사용자(교직원) 로스터 ─────────────────────────
STAFF_NAMES = ["박민정","이도윤","정세린","김도현","최유나","한승호","오지훈","서가은","윤재호","강하린",
               "조민서","임수진","권태경","황보름","신예찬","송지아","전우성","홍서윤","배진우","문가람",
               "안소민","유준혁","고은별","남기훈","심다연","구본우","장하늘","노아름"]

def build_users():
    users = []
    def add(uid, name, role, dept, domains, mgr=None):
        users.append({"user_id": uid, "name": name, "role": role, "department": dept,
                      "domains": domains, "email": f"{uid}@campusflow.demo",
                      "manager_user_id": mgr, "source_type": SRC})
    ni = iter(STAFF_NAMES)
    add("u_dean", "강지원", "학장", "학장실", ["all"])
    add("u_vice", next(ni), "부학장", "학장실", ["all"], "u_dean")
    domain_meta = {
        "practicum": ("산학협력팀", "현장실습"), "scholarship": ("학생지원팀", "장학"),
        "academic": ("교학팀", "학사"), "complaint": ("행정지원팀", "민원"),
        "international": ("국제교류팀", "유학생"), "student_success": ("학생성공센터", "학생성공"),
    }
    officers = {}
    for code, (dept, ko) in domain_meta.items():
        mgr_id = f"u_{code}_mgr"
        add(mgr_id, next(ni), f"{ko} 담당 팀장", dept, [code], "u_vice")
        offs = []
        for i in range(1, 4):
            oid = f"u_{code}_{i:02d}"
            add(oid, next(ni), f"{ko} 담당자", dept, [code], mgr_id)
            offs.append(oid)
        officers[code] = {"officers": offs, "manager": mgr_id}
    add("u_registrar", next(ni), "학적 담당", "교학팀", ["academic", "student_success"], "u_academic_mgr")
    add("u_privacy", next(ni), "개인정보 보호 담당", "행정지원팀", ["complaint"], "u_complaint_mgr")
    return users, officers, domain_meta


USERS, OFFICERS, DMETA = build_users()
UNAME = {u["user_id"]: u["name"] for u in USERS}


# ───────────────────────── 채널 ─────────────────────────
CH_OF = {"practicum": ("C_PRAC_OPS", "#케이스-현장실습"), "scholarship": ("C_SCH_REVIEW", "#케이스-장학"),
         "academic": ("C_ACAD_OPS", "#케이스-학사"), "complaint": ("C_CIVIL_DESK", "#케이스-민원"),
         "international": ("C_INTL_SUPPORT", "#케이스-유학생"), "student_success": ("C_SUCCESS_CARE", "#케이스-학생성공")}

def build_channels():
    chans = []
    for code, (cid, nm) in CH_OF.items():
        dept, ko = DMETA[code]
        members = [OFFICERS[code]["manager"], *OFFICERS[code]["officers"], "u_vice", "u_dean"]
        chans.append({"channel_id": cid, "name": nm, "ko_label": f"{ko} 운영", "domain": code,
                      "purpose": f"{ko} 업무 케이스 협업·처리 채널", "members": members, "source_type": SRC})
    chans.append({"channel_id": "C_NOTICE", "name": "#케이스-운영공지", "ko_label": "단과대 공지",
                  "domain": "all", "purpose": "전체 공지", "members": [u["user_id"] for u in USERS], "source_type": SRC})
    chans.append({"channel_id": "C_DEAN_REPORT", "name": "#케이스-학장보고", "ko_label": "학장 보고",
                  "domain": "all", "purpose": "학장 보고·결재 라인", "members": ["u_dean", "u_vice", *[OFFICERS[c]["manager"] for c in CH_OF]], "source_type": SRC})
    return chans

CHANNELS = build_channels()
CH_NAME = {c["channel_id"]: c["name"] for c in CHANNELS}


# ───────────────────────── 학생(synthetic) ─────────────────────────
SUR = list("김이박최정강조윤장임한오서신권황안송류전")
GIV = ["하늘","민준","서연","지우","도윤","예준","시우","하준","주원","지호","수빈","채원","다은","서준","지민",
       "유진","현우","승현","예린","나윤","가은","태경","소율","건우","하율","지안","수아","연우","민서","준영"]
INTL = [("Nguyen Thi Mai","베트남"),("Wang Lei","중국"),("Aisha Khan","파키스탄"),("Tanaka Yuki","일본"),
        ("Chen Hao","중국"),("Pham Van Duc","베트남"),("Sofia Rossi","이탈리아"),("John Carter","미국"),
        ("Li Wei","중국"),("Mohammed Ali","이집트"),("Olga Petrova","러시아"),("Kim Anh","베트남"),
        ("Zhang Min","중국"),("Hiroshi Sato","일본"),("Maria Garcia","스페인"),("Rahul Sharma","인도")]

def build_students(n=150):
    studs = []
    used = set()
    # 국내 학생
    for i in range(1, n - len(INTL) + 1):
        while True:
            nm = random.choice(SUR) + random.choice(GIV)
            if nm not in used: used.add(nm); break
        sid = f"stu_2026_{i:04d}"
        studs.append({"student_ref": sid, "name": nm, "masked_name": nm[0] + "*" + nm[-1],
                      "student_no_masked": f"2026-{random.randint(1000,9999)//100*100+random.randint(0,9):04d}"[:4] + "****",
                      "department": random.choice(["경영학과","회계세무학과","재무금융학과","경영정보학과","국제통상학과"]),
                      "year": random.choice([1,2,3,4]), "nationality": "대한민국", "source_type": SRC})
    # 유학생
    for j, (nm, nat) in enumerate(INTL, start=len(studs)+1):
        sid = f"stu_2026_{j:04d}"
        studs.append({"student_ref": sid, "name": nm, "masked_name": nm.split()[0] + " *",
                      "student_no_masked": "2026-****", "department": random.choice(["국제통상학과","경영학과","경영정보학과"]),
                      "year": random.choice([1,2,3,4]), "nationality": nat, "source_type": SRC})
    return studs

STUDENTS = build_students()
KOR_STUDENTS = [s for s in STUDENTS if s["nationality"] == "대한민국"]
INTL_STUDENTS = [s for s in STUDENTS if s["nationality"] != "대한민국"]


# ───────────────────────── 도메인 케이스 설정 ─────────────────────────
# code: (ko_label, [ (case_type, 제목접미, [required_docs], [rag_paths]) ], [statuses])
DOC = {  # 공통 문서 약칭
}
DOMAINS = {
 "practicum": ("현장실습", "C_PRAC_OPS", [
    ("early_withdrawal", "현장실습 중도 포기", ["실습협약서","진단서","기관확인서","지도교수확인서"], ["knowledge/practicum/early-withdrawal.md","knowledge/practicum/credit-recognition.md"]),
    ("attendance_issue", "현장실습 출근 불량", ["출근부","실습일지","기관확인서"], ["knowledge/practicum/attendance.md"]),
    ("insurance_missing", "산재·상해보험 미가입", ["보험가입증명서","실습협약서"], ["knowledge/practicum/insurance-guide.md"]),
    ("site_change", "실습기관 변경 요청", ["실습기관변경신청서","신규협약서","학생서약서"], ["knowledge/practicum/site-change.md"]),
    ("journal_missing", "실습일지 미제출", ["실습일지","출근부"], ["knowledge/practicum/journal.md"]),
    ("evaluation_delay", "기관 평가서 지연", ["기관평가서","실습일지"], ["knowledge/practicum/evaluation.md"]),
    ("safety_incident", "실습 중 안전사고", ["사고경위서","진단서","보험가입증명서","기관확인서"], ["knowledge/practicum/safety-incident.md","knowledge/practicum/insurance-guide.md"]),
 ]),
 "scholarship": ("장학", "C_SCH_REVIEW", [
    ("duplicate_award", "장학금 중복 수혜", ["장학신청서","수혜내역확인서","성적증명서"], ["knowledge/scholarship/duplicate-award.md","knowledge/scholarship/payment-policy.md"]),
    ("eligibility_fail", "장학 자격 미달", ["장학신청서","성적증명서","재학증명서"], ["knowledge/scholarship/eligibility.md"]),
    ("document_missing", "장학 서류 미비", ["장학신청서","소득증빙서류","통장사본"], ["knowledge/scholarship/documents.md"]),
    ("clawback", "장학금 환수", ["환수통지서","수혜내역확인서"], ["knowledge/scholarship/clawback.md"]),
    ("recommendation_missing", "추천서 누락", ["추천서","장학신청서"], ["knowledge/scholarship/recommendation.md"]),
    ("income_verification", "소득분위 확인", ["소득증빙서류","가족관계증명서"], ["knowledge/scholarship/income-bracket.md"]),
 ]),
 "academic": ("학사", "C_ACAD_OPS", [
    ("grade_appeal", "성적 이의신청", ["성적이의신청서","근거자료"], ["knowledge/academic/grade-appeal.md"]),
    ("course_change", "수강 정정", ["수강변경원","지도교수확인서"], ["knowledge/academic/enrollment-change.md"]),
    ("leave_of_absence", "휴학 신청", ["휴학원","사유증빙"], ["knowledge/academic/leave-policy.md"]),
    ("return_from_leave", "복학 처리", ["복학원","등록금납부확인서"], ["knowledge/academic/return-policy.md"]),
    ("graduation_requirement", "졸업요건 미충족", ["졸업사정표","성적증명서"], ["knowledge/academic/graduation-audit.md"]),
    ("academic_warning", "학사경고 처리", ["학사경고확인서","상담일지"], ["knowledge/academic/academic-warning.md"]),
    ("transfer_major", "전과 신청", ["전과신청서","성적증명서","지도교수확인서"], ["knowledge/academic/transfer.md"]),
 ]),
 "complaint": ("민원", "C_CIVIL_DESK", [
    ("parent_grade_inquiry", "학부모 성적 문의", ["민원접수서","개인정보동의서"], ["knowledge/complaint/grade-info-policy.md","knowledge/complaint/privacy-guideline.md"]),
    ("refund_request", "등록금 환불 요청", ["환불신청서","통장사본","증빙자료"], ["knowledge/complaint/refund-policy.md"]),
    ("facility_complaint", "시설 불편 민원", ["민원접수서","현장사진"], ["knowledge/complaint/handling-policy.md"]),
    ("processing_delay", "행정처리 지연 민원", ["민원접수서","처리경위서"], ["knowledge/complaint/handling-policy.md"]),
    ("info_disclosure", "개인정보 열람 요청", ["개인정보열람청구서","본인확인서류","개인정보동의서"], ["knowledge/complaint/privacy-guideline.md"]),
    ("misconduct_report", "부정행위 제보", ["제보접수서","증빙자료"], ["knowledge/complaint/misconduct.md"]),
 ]),
 "international": ("유학생", "C_INTL_SUPPORT", [
    ("visa_document_missing", "비자 서류 누락", ["비자사본","표준입학허가서","재정증명서"], ["knowledge/international/visa-documents.md"]),
    ("immigration_report", "출입국 신고", ["외국인등록증","체류지변경신고서"], ["knowledge/international/alien-registration.md"]),
    ("insurance_enrollment", "유학생 보험 가입", ["보험증서","외국인등록증"], ["knowledge/international/insurance.md"]),
    ("korean_proficiency", "한국어 능력 미달", ["TOPIK성적표","수강계획서"], ["knowledge/international/korean.md"]),
    ("stay_expiry", "체류기간 만료 임박", ["외국인등록증","체류기간연장신청서","재학증명서"], ["knowledge/international/stay-management.md"]),
    ("tuition_installment", "등록금 분납 신청", ["분납신청서","재정증명서"], ["knowledge/international/tuition.md"]),
 ]),
 "student_success": ("학생성공", "C_SUCCESS_CARE", [
    ("academic_warning_care", "학사경고 상담", ["상담일지","학습계획서","상담동의서"], ["knowledge/student-success/warning-care.md","knowledge/student-success/counseling-consent.md"]),
    ("dropout_risk", "중도탈락 위험 관리", ["위험도평가서","상담일지","상담동의서"], ["knowledge/student-success/dropout-prevention.md"]),
    ("career_counseling", "진로 상담", ["진로상담신청서","상담일지"], ["knowledge/student-success/career.md"]),
    ("psych_referral", "심리상담 연계", ["상담동의서","연계의뢰서"], ["knowledge/student-success/counseling-consent.md"]),
    ("tutoring", "학습부진 튜터링", ["튜터링신청서","학습계획서"], ["knowledge/student-success/tutoring.md"]),
    ("attendance_alert", "출석 경고", ["출석현황표","상담일지"], ["knowledge/student-success/attendance-alert.md"]),
 ]),
}
STATUSES = ["received","in_review","evidence_requested","approval_pending","in_progress","completed","on_hold","rejected"]
PRIOS = ["urgent","high","high","normal","normal","normal","low"]
CODE3 = {"practicum":"prac","scholarship":"sch","academic":"acad","complaint":"civil","international":"intl","student_success":"succ"}

# 출력 누적
cases, tasks, approvals, documents, threads, rels = [], [], [], [], [], []
canvases = []
_tid = _doc = _tsk = _apr = _rel = 0
def nid(prefix, n): return f"{prefix}_{n:04d}"


def add_rel(relation, from_type, from_id, to_type, to_id):
    global _rel; _rel += 1
    rels.append({"rel_id": nid("rel", _rel), "relation": relation, "from_type": from_type,
                 "from_id": from_id, "to_type": to_type, "to_id": to_id, "source_type": SRC})


def make_thread(case, channel_id, n_msgs, kind="case"):
    global _tid; _tid += 1
    tid = f"thr_{CODE3[case['domain']]}_{_tid:04d}"
    owner = case["owner_user_id"]; appr = case["approver_user_id"]
    parts = list({owner, appr, *random.sample([u["user_id"] for u in USERS if case["domain"] in u["domains"] or "all" in u["domains"]], k=min(3, max(1,n_msgs-2)) )})
    base = datetime.fromisoformat(case["created_at"])
    msgs = []
    openers = [f"{case['student_name']} 학생 {DOMAINS[case['domain']][2][0][1]} 건 공유합니다. 현재 상태 {case['status']}입니다.",
               f"[{case['title']}] 진행 상황 정리해 올립니다. 확인 부탁드려요.",
               f"{case['title']} 관련 후속 처리 논의 스레드입니다."]
    msgs.append({"user_id": owner, "name": UNAME[owner], "ts": iso(base), "text": random.choice(openers)})
    follow = ["필요 서류 다시 안내드렸습니다. 회신 기다리는 중입니다.",
              f"근거 규정은 {case['related_rag_paths'][0]} 참고하면 됩니다.",
              "기관/학생 측 확인 후 다음 액션 진행하겠습니다.",
              f"승인 라인은 {UNAME[appr]} 팀장님으로 걸어두었습니다.",
              "리스크가 있어 우선순위 올려 처리하겠습니다.",
              "처리 결과는 캔버스 체크리스트에 업데이트했습니다."]
    for k in range(1, n_msgs):
        spk = parts[k % len(parts)]
        msgs.append({"user_id": spk, "name": UNAME[spk], "ts": iso(base + timedelta(hours=3*k)),
                     "text": random.choice(follow)})
    th = {"thread_id": tid, "channel_id": channel_id, "channel_name": CH_NAME[channel_id],
          "case_id": case["case_id"], "title": case["title"], "participants": parts,
          "message_count": len(msgs), "messages": msgs, "created_at": iso(base),
          "source_type": SRC}
    threads.append(th)
    add_rel("thread_to_case", "thread", tid, "case", case["case_id"])
    return tid


def make_case(domain, idx, ctype_row, student, status=None, prio=None, consent=None, risk=None):
    global _tsk, _apr, _doc
    code = CODE3[domain]
    ctype, label, req_docs, rag = ctype_row
    cid = f"case_{code}_{idx:03d}"
    status = status or random.choice(STATUSES)
    prio = prio or random.choice(PRIOS)
    off = OFFICERS[domain]; owner = random.choice(off["officers"]); appr = off["manager"]
    if prio == "urgent": appr = random.choice([off["manager"], "u_vice"])
    ch = DOMAINS[domain][1]
    created = back(random.randint(2, 110), random.randint(0, 12))
    updated = created + timedelta(days=random.randint(0, 25), hours=random.randint(1, 20))
    if updated > NOW: updated = NOW - timedelta(hours=random.randint(1, 30))
    # 문서 제출/미제출 분배
    n_sub = random.randint(0, len(req_docs))
    submitted = req_docs[:n_sub]; missing = req_docs[n_sub:]
    if status in ("completed",): submitted, missing = req_docs, []
    if status in ("evidence_requested", "received") and not missing: missing = [req_docs[-1]]; submitted = req_docs[:-1]
    rag_sel = rag if len(rag) <= 2 else random.sample(rag, 2)
    # next actions
    na_pool = [f"{missing[0] if missing else req_docs[0]} 제출 요청 및 회신 확인",
               "담당자 검토 후 승인 라인 상신", "학생/기관 유선 안내 및 일정 확정",
               "근거 규정 확인 후 처리 방침 결정", "캔버스 체크리스트 업데이트"]
    n_na = random.randint(1, 3)
    next_actions = []
    for j in range(n_na):
        due = NOW + timedelta(days=random.choice([0, 0, 1, 2, 3, 5, 7]))
        next_actions.append({"action": na_pool[j % len(na_pool)], "owner_user_id": owner,
                             "due_at": iso(due.replace(hour=18, minute=0, second=0)),
                             "status": "open" if status not in ("completed",) else "done"})
    summary = f"{student['name']} 학생 {label} 건. 현재 상태 {status}, 미제출 서류 {len(missing)}건."
    if consent is False:
        summary += " 개인정보 제공 동의가 확인되지 않아 안내 필요."
    timeline = [f"{student['masked_name']} 관련 {label} 접수",
                f"{CH_NAME[ch]} 스레드에서 담당자 검토",
                f"필요 서류 {len(req_docs)}건 중 {len(submitted)}건 확인",
                ("승인 대기 상태" if status == "approval_pending" else "후속 액션 진행")]
    if risk: timeline.append("리스크 높음 — 우선 처리 대상으로 표시")
    case = {
        "case_id": cid, "title": f"{student['name']} {label}", "domain": domain, "case_type": ctype,
        "status": status, "priority": prio, "student_ref": student["student_ref"],
        "student_name": student["name"], "owner_user_id": owner, "owner_name": UNAME[owner],
        "approver_user_id": appr, "approver_name": UNAME[appr],
        "related_channel_id": ch, "related_channel_name": CH_NAME[ch],
        "related_thread_id": None, "related_canvas_id": None, "related_canvas_title": None,
        "related_rag_paths": rag_sel, "required_documents": req_docs, "submitted_documents": submitted,
        "missing_documents": missing, "next_actions": next_actions, "next_action": next_actions[0]["action"],
        "summary": summary, "timeline": timeline, "consent_on_file": consent if consent is not None else True,
        "risk_level": "high" if risk else random.choice(["low","medium","medium"]),
        "created_at": iso(created), "updated_at": iso(updated), "source_type": SRC,
    }
    cases.append(case)
    # 관계: student/owner/approver/channel/rag
    add_rel("case_to_student", "case", cid, "student", student["student_ref"])
    add_rel("case_to_owner", "case", cid, "user", owner)
    add_rel("case_to_approver", "case", cid, "user", appr)
    add_rel("case_to_channel", "case", cid, "channel", ch)
    for rp in rag_sel: add_rel("case_to_rag_path", "case", cid, "rag_path", rp)
    # 스레드 1~2개
    n_thr = 2 if (risk or prio in ("urgent", "high") or random.random() < 0.4) else 1
    first_tid = None
    for t in range(n_thr):
        tid = make_thread(case, ch, n_msgs=random.randint(4, 6))
        if t == 0: first_tid = tid
        add_rel("case_to_thread", "case", cid, "thread", tid)
    case["related_thread_id"] = first_tid
    # 문서 엔티티 (필요서류별)
    for d in req_docs:
        _doc += 1; did = nid("doc", _doc)
        st = "제출완료" if d in submitted else ("검토중" if (status == "in_review" and random.random()<0.3) else "미제출")
        masked = (domain == "complaint" and consent is False and d == "개인정보동의서")
        documents.append({"document_id": did, "case_id": cid, "doc_type": d,
                          "title": f"{student['masked_name']} {d}", "status": st,
                          "student_ref": student["student_ref"], "owner_user_id": owner,
                          "rag_path": rag_sel[0], "file_ref": f"vault://{code}/{cid}/{did}.pdf",
                          "pii_masked": True, "consent_required": (d == "개인정보동의서"),
                          "created_at": iso(created + timedelta(days=1)), "source_type": SRC})
        add_rel("document_to_case", "document", did, "case", cid)
        add_rel("case_to_document", "case", cid, "document", did)
    # 태스크 2~3개
    n_tsk = random.randint(2, 3)
    for t in range(n_tsk):
        _tsk += 1; tkid = f"task_{code}_{_tsk:04d}"
        tstat = "done" if (status == "completed" and t == 0) else random.choice(["open","open","in_progress"])
        due = NOW + timedelta(days=random.choice([0, 1, 2, 3, 5, 7, 10]))
        tasks.append({"task_id": tkid, "case_id": cid,
                      "title": next_actions[t % len(next_actions)]["action"],
                      "owner_user_id": owner, "owner_name": UNAME[owner], "status": tstat,
                      "priority": prio, "due_at": iso(due.replace(hour=18, minute=0, second=0)),
                      "created_at": iso(created + timedelta(days=1)), "source_type": SRC})
        add_rel("task_to_case", "task", tkid, "case", cid)
    # 승인 (해당 상태면 생성)
    if status in ("approval_pending","in_progress","completed","rejected") or random.random() < 0.4:
        _apr += 1; aid = nid("apr", _apr)
        astat = {"approval_pending":"pending","completed":"approved","rejected":"rejected","in_progress":"approved"}.get(status, "pending")
        req_at = created + timedelta(days=2)
        decided = None if astat == "pending" else iso(req_at + timedelta(days=random.randint(1,4)))
        due_at = TODAY + "T18:00:00" if (status == "approval_pending" and random.random() < 0.5) else iso(NOW + timedelta(days=random.randint(1,5)))
        approvals.append({"approval_id": aid, "case_id": cid, "type": f"{ctype}_approval",
                          "requester_user_id": owner, "requester_name": UNAME[owner],
                          "approver_user_id": appr, "approver_name": UNAME[appr],
                          "status": astat, "requested_at": iso(req_at), "decided_at": decided,
                          "due_at": due_at, "comment": "" if astat=="pending" else ("승인 처리" if astat=="approved" else "보완 요청 후 반려"),
                          "source_type": SRC})
        add_rel("approval_to_case", "approval", aid, "case", cid)
        add_rel("case_to_approver", "case", cid, "approval", aid)
    return case


# ───────────────────────── 케이스 생성 (14/도메인 = 84) ─────────────────────────
def students_for(domain):
    return INTL_STUDENTS if domain == "international" else KOR_STUDENTS

idx_by = {c: 0 for c in DOMAINS}
def next_idx(domain):
    idx_by[domain] += 1; return idx_by[domain]

# ▶ 앵커 케이스 (데모 질문 직접 대응)
anchor_students = {
    "김하늘": {"student_ref":"stu_2026_0142","name":"김하늘","masked_name":"김*늘","student_no_masked":"2026-****","department":"경영학과","year":3,"nationality":"대한민국","source_type":SRC},
}
STUDENTS.append(anchor_students["김하늘"]); KOR_STUDENTS.append(anchor_students["김하늘"])
# 1) 김하늘 현장실습 중도포기 = case_prac_001
make_case("practicum", next_idx("practicum"),
          DOMAINS["practicum"][2][0], anchor_students["김하늘"],
          status="evidence_requested", prio="high", risk=True)
# 2) 장학 중복수혜 승인대기 (오늘 처리) ×3
for _ in range(3):
    make_case("scholarship", next_idx("scholarship"), DOMAINS["scholarship"][2][0],
              random.choice(KOR_STUDENTS), status="approval_pending", prio="high")
# 3) 학부모 성적문의 민원 (개인정보 동의 없음) ×3
for _ in range(3):
    make_case("complaint", next_idx("complaint"), DOMAINS["complaint"][2][0],
              random.choice(KOR_STUDENTS), status="evidence_requested", prio="high", consent=False)
# 4) 유학생 비자서류 누락 ×4 (담당자 분산)
for _ in range(4):
    make_case("international", next_idx("international"), DOMAINS["international"][2][0],
              random.choice(INTL_STUDENTS), status="evidence_requested", prio=random.choice(["urgent","high"]))
# 5) 현장실습 리스크 높은 케이스 ×3
for _ in range(3):
    make_case("practicum", next_idx("practicum"), random.choice(DOMAINS["practicum"][2][:5]),
              random.choice(KOR_STUDENTS), status=random.choice(["in_review","in_progress"]), prio="urgent", risk=True)

# ▶ 나머지 채워 도메인당 14개
for domain, (ko, ch, ctypes) in DOMAINS.items():
    while idx_by[domain] < 14:
        ctype_row = random.choice(ctypes)
        stu = random.choice(students_for(domain))
        consent = False if (domain == "complaint" and random.random() < 0.3) else None
        risk = True if random.random() < 0.18 else None
        make_case(domain, next_idx(domain), ctype_row, stu, consent=consent, risk=risk)


# ───────────────────────── 캔버스 (도메인당 4 = 24) ─────────────────────────
CANVAS_DEFS = {
 "practicum": ["현장실습 중도 포기 처리 체크리스트","산재·상해보험 가입 가이드","실습기관 변경 절차","현장실습 리스크 모니터링 보드"],
 "scholarship": ["장학금 중복 수혜 심사 기준","장학 서류 점검 체크리스트","소득분위 확인 절차","장학금 환수 처리 가이드"],
 "academic": ["성적 이의신청 처리 절차","학적변동(휴·복학) 가이드","졸업요건 점검 체크리스트","학사경고 관리 보드"],
 "complaint": ["민원 처리 표준 절차","개인정보 제공 동의 가이드","성적정보 제공 기준","등록금 환불 처리 절차"],
 "international": ["유학생 비자 서류 안내","외국인등록·체류 관리","유학생 보험 가입 가이드","체류기간 만료 모니터링 보드"],
 "student_success": ["학사경고 상담 매뉴얼","중도탈락 위험 관리 보드","상담 동의 절차","학습부진 튜터링 운영"],
}
for domain, titles in CANVAS_DEFS.items():
    ch = DOMAINS[domain][1]
    dcases = [c for c in cases if c["domain"] == domain]
    for k, title in enumerate(titles):
        cv_id = f"can_{CODE3[domain]}_{k+1:02d}"
        # 관련 케이스: 같은 도메인 케이스 일부 연결
        linked = [c["case_id"] for c in dcases[k::4]][:6]
        md = (f"# {title}\n\n> {DOMAINS[domain][0]} 도메인 운영 캔버스 (synthetic_demo)\n\n"
              f"## 처리 단계\n- [ ] 접수 확인\n- [ ] 필요 서류 점검\n- [ ] 담당자 검토\n- [ ] 승인 라인 상신\n- [ ] 결과 통보\n\n"
              f"## 연결 케이스\n" + "\n".join(f"- {cid}" for cid in linked) +
              f"\n\n## 근거 RAG\n- knowledge/{domain}/" )
        canvases.append({"canvas_id": cv_id, "channel_id": ch, "channel_name": CH_NAME[ch],
                         "domain": domain, "title": title, "markdown": md,
                         "related_case_ids": linked, "source_type": SRC})
        for cid in linked:
            add_rel("canvas_to_case", "canvas", cv_id, "case", cid)
    # 각 케이스에 도메인 대표 캔버스 연결 (related_canvas)
    dom_canvas = [cv for cv in canvases if cv["domain"] == domain]
    for c in dcases:
        cv = random.choice(dom_canvas)
        c["related_canvas_id"] = cv["canvas_id"]; c["related_canvas_title"] = cv["title"]
        add_rel("case_to_canvas", "case", c["case_id"], "canvas", cv["canvas_id"])

# ───────────────────────── 추가 일반 스레드 (150+ 보장) ─────────────────────────
while len(threads) < 160:
    c = random.choice(cases)
    make_thread(c, c["related_channel_id"], n_msgs=random.randint(3, 5))
    add_rel("case_to_thread", "case", c["case_id"], "thread", threads[-1]["thread_id"])


# ───────────────────────── 쓰기 ─────────────────────────
def write_json(name, obj): (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
def write_jsonl(name, rows):
    with (DATA / name).open("w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")

workspace_map = {
    "workspace": "한빛대학교 CampusFlow 운영 데모", "source_type": SRC, "generated_at": iso(NOW),
    "id_prefixes": {"case":"case_<domain>_NNN","user":"u_*","channel":"C_*","thread":"thr_*","canvas":"can_*","task":"task_*","approval":"apr_NNNN","document":"doc_NNNN","student":"stu_2026_NNNN","relationship":"rel_NNNN"},
    "rag_root": "knowledge/", "domains": [
        {"id": d, "ko_label": DOMAINS[d][0], "channel_id": DOMAINS[d][1],
         "case_count": sum(1 for c in cases if c["domain"] == d)} for d in DOMAINS],
    "counts": {"users": len(USERS), "channels": len(CHANNELS), "students": len(STUDENTS),
               "cases": len(cases), "threads": len(threads), "canvases": len(canvases),
               "tasks": len(tasks), "approvals": len(approvals), "documents": len(documents),
               "relationships": len(rels)},
    "mcp_compat": {"adapter": "scripts/mcp_adapter.py", "validate": "scripts/validate_data.py"},
}

write_json("workspace_map.json", workspace_map)
write_json("users.json", USERS)
write_json("channels.json", CHANNELS)
write_json("canvases.json", canvases)
write_json("students.json", STUDENTS)
write_jsonl("slack_threads.jsonl", threads)
write_jsonl("cases.jsonl", cases)
write_jsonl("tasks.jsonl", tasks)
write_jsonl("approvals.jsonl", approvals)
write_jsonl("documents.jsonl", documents)
write_jsonl("relationships.jsonl", rels)

# README
dom_lines = "\n".join(f"| {DOMAINS[d][0]} (`{d}`) | {sum(1 for c in cases if c['domain']==d)} | {DOMAINS[d][1]} |" for d in DOMAINS)
readme = f"""# CampusCase Desk — 운영형 Seed Dataset (synthetic_demo)

한빛대학교 CampusFlow AI MCP/RAG 연계용 **합성 운영 데이터**입니다. 실제 개인정보를 포함하지 않으며 모든 레코드는 `source_type: synthetic_demo` 입니다.

생성: `python3 generate_campusflow.py` · 기준일 {TODAY}

## 도메인별 케이스
| 도메인 | 케이스 수 | 채널 |
|---|---|---|
{dom_lines}

## 전체 수량
| 엔티티 | 수 |
|---|---|
| users | {len(USERS)} |
| channels | {len(CHANNELS)} |
| students | {len(STUDENTS)} |
| cases | {len(cases)} |
| slack_threads | {len(threads)} |
| canvases | {len(canvases)} |
| tasks | {len(tasks)} |
| approvals | {len(approvals)} |
| documents | {len(documents)} |
| relationships | {len(rels)} |

## 파일
- `workspace_map.json` 메타·수량·ID 규칙
- `users.json` / `channels.json` / `students.json` / `canvases.json`
- `slack_threads.jsonl` / `cases.jsonl` / `tasks.jsonl` / `approvals.jsonl` / `documents.jsonl`
- `relationships.jsonl` 엔티티 간 관계(case↔student/owner/approver/channel/thread/canvas/document/rag, task/approval/document/thread→case)

## 무결성
`python3 scripts/verify_integrity.py` — orphan(case/thread/task/approval/document) 0, 모든 참조 유효해야 통과.
기존 `python3 scripts/validate_data.py`, MCP 어댑터(`scripts/mcp_adapter.py`)와 호환됩니다.
"""
(DATA / "README.md").write_text(readme, encoding="utf-8")

print(json.dumps(workspace_map["counts"], ensure_ascii=False, indent=2))
