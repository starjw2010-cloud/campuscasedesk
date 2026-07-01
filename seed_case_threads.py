#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seed_case_threads.py — 케이스-* 채널에 케이스 기반 스레드(5+ 답글) + 문서 핑퐁 시딩.
담당 교직원을 username+icon_url 로 위장 발화. cases.jsonl 의 실제 케이스를 근거로 대화 구성.
사용: export $(grep -v '^#' /Volumes/jee_insight/슬랙앱/hanbit-sandbox/.env | xargs); python3 seed_case_threads.py
"""
import os, sys, json, time, random
from pathlib import Path
import requests

random.seed(7)
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"; DOCS = ROOT / "demo_docs"
BOT = os.environ["SLACK_BOT_TOKEN"]
API = "https://slack.com/api"
HJ = {"Authorization": f"Bearer {BOT}", "Content-Type": "application/json; charset=utf-8"}
HA = {"Authorization": f"Bearer {BOT}"}

CASES = [json.loads(l) for l in open(DATA / "cases.jsonl") if l.strip()]
CHJSON = json.load(open(DATA / "channels.json"))
CIDS = json.load(open(ROOT / "campus_channel_ids.json"))   # {한글채널명: id}
USERS = json.load(open(DATA / "users.json"))
DOM_STAFF = {}
for u in USERS:
    for d in u["domains"]:
        DOM_STAFF.setdefault(d, []).append(u["name"])

ST_KO = {"received":"접수","in_review":"검토중","evidence_requested":"서류대기","approval_pending":"승인대기",
         "in_progress":"처리중","completed":"완료","on_hold":"보류","rejected":"반려"}
DOM_KO = {"practicum":"현장실습","scholarship":"장학","academic":"학사","complaint":"민원",
          "international":"유학생","student_success":"학생성공"}
# domain → 채널 id
DOM_CID = {}
for c in CHJSON:
    if c["domain"] in DOM_KO:
        DOM_CID[c["domain"]] = CIDS.get(c["name"].lstrip("#"))

# case_type → 첨부 문서
DOC_FOR = {
    "early_withdrawal":"현장실습_표준협약서.pdf","safety_incident":"산재보험_가입안내.pdf",
    "insurance_missing":"산재보험_가입안내.pdf","site_change":"현장실습_표준협약서.pdf",
    "duplicate_award":"장학_중복수혜_심사기준.pdf","document_missing":"장학_서류_체크리스트.docx",
    "grade_appeal":"성적이의신청_처리절차.docx","parent_grade_inquiry":"민원_개인정보제공_안내문.docx",
    "visa_document_missing":"유학생_비자서류_체크리스트.pdf","academic_warning_care":"학사경고_상담가이드.docx",
}

def mask(name):
    parts = name.split()
    if len(parts) > 1: return parts[0] + " *"
    return name[0] + "*" + name[-1] if len(name) >= 2 else name

def avatar(name): return f"https://api.dicebear.com/9.x/notionists-neutral/png?seed={name}&size=72&cb={abs(hash(name))%9999}"

def post(cid, name, text, thread_ts=None):
    body = {"channel": cid, "text": text, "username": name, "icon_url": avatar(name)}
    if thread_ts: body["thread_ts"] = thread_ts
    r = requests.post(f"{API}/chat.postMessage", headers=HJ, json=body, timeout=30).json()
    return r.get("ts") if r.get("ok") else None

def upload(cid, fn, name, comment, thread_ts):
    fp = DOCS / fn
    if not fp.exists(): return
    size = fp.stat().st_size
    r = requests.get(f"{API}/files.getUploadURLExternal", headers=HA, params={"filename": fn, "length": size}, timeout=30).json()
    if not r.get("ok"): return
    requests.post(r["upload_url"], data=fp.read_bytes(), timeout=60)
    body = {"files": [{"id": r["file_id"], "title": fn}], "channel_id": cid, "initial_comment": comment}
    if thread_ts: body["thread_ts"] = thread_ts
    requests.post(f"{API}/files.completeUploadExternal", headers=HJ, json=body, timeout=30)

# 도메인별 답글 흐름 템플릿 (5~7개)
def reply_lines(case, staff):
    dom = case["domain"]; ms = mask(case["student_name"]); miss = case["missing_documents"]
    na = case["next_actions"][0]["action"] if case["next_actions"] else "후속 처리"
    rag = case["related_rag_paths"][0] if case["related_rag_paths"] else ""
    common = [
        f"필요 서류 다시 안내했습니다. 미제출 {len(miss)}건 회신 받는 대로 진행하겠습니다." if miss else "서류는 모두 확인됐습니다. 다음 단계로 넘어갑니다.",
        f"근거는 `{rag}` 기준입니다. 처리 방향 이대로 가시죠.",
        f"다음 액션: {na}. 제가 담당해서 마감까지 처리하겠습니다.",
    ]
    flavor = {
        "practicum": ["기관 담당자와 통화했고 출근/실습일지 상황 확인했습니다.", "보험 가입 여부부터 확인이 필요합니다. 미가입이면 실습 중단 사유입니다.", "지도교수 면담 일정 잡아 학점 처리 기준 안내하겠습니다."],
        "scholarship": ["수혜내역 대조했더니 중복 가능성 있어 보입니다. 초과분 조정 검토 필요합니다.", "소득분위 8분위 이하 맞는지 증빙 다시 확인하겠습니다.", "성적 기준은 충족합니다. 서류만 보완되면 승인 가능합니다."],
        "academic": ["담당 교수 확인 결과 정정 사유 검토 중입니다.", "성적공시 후 이의신청 기한 내 접수된 건 맞습니다.", "학적 변동은 등록금 처리와 같이 봐야 합니다."],
        "complaint": ["학생 본인 개인정보 제공 동의가 확인되지 않습니다. 동의 없이는 성적 제공 불가입니다.", "민원인께는 동의 절차부터 안내드리는 게 맞겠습니다.", "처리결과 통보서는 규정 문구로 작성하겠습니다."],
        "international": ["비자/체류 서류 누락분 리스트업했습니다. 만료 임박 건 우선입니다.", "외국인등록·보험 가입 여부 같이 점검하겠습니다.", "체류기간 연장 신청 일정 학생에게 안내했습니다."],
        "student_success": ["상담 동의서부터 받고 진행하겠습니다.", "위험도 평가 결과 중점관리 대상입니다. 튜터링 연계하겠습니다.", "학습계획서 작성 도와드리고 후속 모니터링하겠습니다."],
    }[dom]
    pool = flavor + common
    out = []
    for i in range(random.randint(5, 7)):
        spk = staff[(i + 1) % len(staff)]
        out.append((spk, pool[i % len(pool)]))
    # 마지막 승인/마무리
    out.append((case["approver_name"], "확인했습니다. 승인 라인 검토 후 결과 회신하겠습니다."))
    return out

def main():
    total_t = total_m = total_f = 0
    for dom, cid in DOM_CID.items():
        if not cid:
            print(f"   ✗ {dom}: 채널 id 없음", file=sys.stderr); continue
        staff = list(dict.fromkeys(DOM_STAFF.get(dom, []) + ["강지원"]))
        dcases = [c for c in CASES if c["domain"] == dom]
        # 다양성: 리스크/승인대기/서류대기 우선 4건 + 짧은 공지 1건
        pick = sorted(dcases, key=lambda c: (c["priority"] != "urgent", c["risk_level"] != "high", c["status"] != "approval_pending"))[:4]
        print(f"\n# {DOM_KO[dom]} 채널 ({cid}) — 스레드 {len(pick)}")
        for c in pick:
            ms = mask(c["student_name"])
            opener = (f":pushpin: *[{c['case_id']}] {c['title'].replace(c['student_name'], ms)}*\n"
                      f"상태 {ST_KO.get(c['status'])} · 우선순위 {c['priority']} · 담당 {c['owner_name']}\n"
                      f"{c['summary'].replace(c['student_name'], ms)}")
            ts = post(cid, c["owner_name"], opener)
            total_t += 1; total_m += 1
            if not ts: continue
            # 문서 첨부 (해당 case_type)
            doc = DOC_FOR.get(c["case_type"])
            if doc:
                upload(cid, doc, c["owner_name"], f":paperclip: 관련 양식/안내 공유합니다 — {doc}", ts)
                total_f += 1; time.sleep(0.5)
            for spk, line in reply_lines(c, staff):
                if post(cid, spk, line, thread_ts=ts): total_m += 1
                time.sleep(0.5)
            time.sleep(0.8)
        # 짧은 공지성 게시글 1건
        post(cid, staff[0], f":mega: {DOM_KO[dom]} 운영 안내 — 케이스 처리 현황은 상단 *리스트* 와 *캔버스* 에서 확인하세요. 미제출 서류 회신 협조 부탁드립니다. (synthetic_demo)")
        total_m += 1; time.sleep(0.6)
    print(f"\n완료 — 스레드 {total_t} · 메시지 {total_m} · 문서첨부 {total_f}")

if __name__ == "__main__":
    main()
