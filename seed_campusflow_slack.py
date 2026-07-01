#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seed_campusflow_slack.py — CampusCase Desk 데이터셋을 실제 Slack 워크스페이스에 materialize.
- 도메인 채널 8개(공개) 생성 + 학장 초대 + topic/purpose
- 캔버스 24개 생성 (canvases.json)
- 도메인별 케이스 추적 리스트 6개 생성 (cases.jsonl → 상태·담당·마감·미제출서류 + 하위작업=next_actions)
- 채널별 인트로 + 핵심 케이스 하이라이트 게시
공개 채널 = 워크스페이스 전원 열람. (Enterprise org-wide 공유는 관리자 콘솔에서 수동)

사용: export $(grep -v '^#' /Volumes/jee_insight/슬랙앱/hanbit-sandbox/.env | xargs)
      python3 seed_campusflow_slack.py            # 실행
      python3 seed_campusflow_slack.py --dry-run  # 미리보기
"""
import os, sys, json, time, argparse
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent / "data"
BOT = os.environ["SLACK_BOT_TOKEN"]
TEAM = os.environ.get("HANBIT_TEAM_ID", "")
DEAN = "U06EF31M3HA"
API = "https://slack.com/api"
HJ = {"Authorization": f"Bearer {BOT}", "Content-Type": "application/json; charset=utf-8"}
HA = {"Authorization": f"Bearer {BOT}"}
IDS = Path(__file__).resolve().parent / "campus_channel_ids.json"

CHANNELS = json.load(open(DATA / "channels.json"))
CANVASES = json.load(open(DATA / "canvases.json"))
CASES = [json.loads(l) for l in open(DATA / "cases.jsonl") if l.strip()]
DOM_KO = {"practicum": "현장실습", "scholarship": "장학", "academic": "학사",
          "complaint": "민원", "international": "유학생", "student_success": "학생성공", "all": "공통"}
ST_KO = {"received": "접수", "in_review": "검토중", "evidence_requested": "서류대기",
         "approval_pending": "승인대기", "in_progress": "처리중", "completed": "완료",
         "on_hold": "보류", "rejected": "반려"}
PR_KO = {"urgent": "긴급", "high": "높음", "normal": "보통", "low": "낮음"}
ST_CHOICES = ["접수", "검토중", "서류대기", "승인대기", "처리중", "완료", "보류", "반려"]
PR_CHOICES = ["긴급", "높음", "보통", "낮음"]


def norm(name):  # '#practicum-ops' → 'practicum-ops'
    return name.lstrip("#").strip().lower()


def create_channel(name, private=False):
    body = {"name": name, "is_private": private}
    if TEAM:
        body["team_id"] = TEAM
    r = requests.post(f"{API}/conversations.create", headers=HJ, json=body, timeout=30).json()
    if r.get("ok"):
        return r["channel"]["id"]
    if r.get("error") == "name_taken":
        # 기존 채널 찾기
        cur = ""
        while True:
            params = {"types": "public_channel,private_channel", "limit": 200, "cursor": cur}
            if TEAM:
                params["team_id"] = TEAM
            rr = requests.get(f"{API}/conversations.list", headers=HA, params=params, timeout=30).json()
            for c in rr.get("channels", []):
                if c["name"] == name:
                    return c["id"]
            cur = rr.get("response_metadata", {}).get("next_cursor", "")
            if not cur:
                break
    print(f"   ✗ 채널 {name}: {r.get('error')}", file=sys.stderr)
    return None


def post(cid, text):
    requests.post(f"{API}/chat.postMessage", headers=HJ, json={"channel": cid, "text": text}, timeout=30)


def rt(s):
    return [{"type": "rich_text", "elements": [{"type": "rich_text_section", "elements": [{"type": "text", "text": str(s)}]}]}]


def build_list_schema():
    cols = [
        {"key": "name", "name": "케이스", "type": "text", "is_primary_column": True},
        {"key": "status", "name": "상태", "type": "select", "options": {"choices": [{"value": s, "label": s, "color": c} for s, c in zip(ST_CHOICES, ["gray", "blue", "orange", "purple", "yellow", "green", "gray", "red"])]}},
        {"key": "priority", "name": "우선순위", "type": "select", "options": {"choices": [{"value": s, "label": s, "color": c} for s, c in zip(PR_CHOICES, ["red", "orange", "blue", "gray"])]}},
        {"key": "owner", "name": "담당", "type": "text"},
        {"key": "report_to", "name": "보고/결재", "type": "user"},
        {"key": "due", "name": "마감", "type": "date"},
        {"key": "missing", "name": "미제출서류", "type": "text"},
        {"key": "case_id", "name": "case_id", "type": "text"},
    ]
    return cols


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    saved = json.load(open(IDS)) if IDS.exists() else {}

    # 1) 채널 생성
    print("■ 채널 생성 (공개)")
    name_to_id = {}
    for ch in CHANNELS:
        nm = norm(ch["name"])
        if args.dry_run:
            print(f"   # {nm} ({ch['ko_label']})")
            continue
        cid = saved.get(nm) or create_channel(nm, private=False)
        if not cid:
            continue
        name_to_id[ch["name"]] = cid
        saved[nm] = cid
        requests.post(f"{API}/conversations.join", headers=HJ, json={"channel": cid}, timeout=30)
        requests.post(f"{API}/conversations.setTopic", headers=HJ, json={"channel": cid, "topic": ch["purpose"][:240]}, timeout=30)
        requests.post(f"{API}/conversations.setPurpose", headers=HJ, json={"channel": cid, "purpose": ch["purpose"][:240]}, timeout=30)
        requests.post(f"{API}/conversations.invite", headers=HJ, json={"channel": cid, "users": DEAN}, timeout=30)
        print(f"   ✓ {nm} → {cid}")
        time.sleep(1.0)
    if args.dry_run:
        print("\n(드라이런: 캔버스 24 / 리스트 6 / 인트로 게시 예정)")
        return
    json.dump(saved, open(IDS, "w"), ensure_ascii=False, indent=2)

    # 채널명(#...) → id 맵 (dataset C_* id → 실제 id)
    cid_by_dataset = {ch["channel_id"]: name_to_id.get(ch["name"]) for ch in CHANNELS}
    cid_by_domain = {ch["domain"]: name_to_id.get(ch["name"]) for ch in CHANNELS if ch["domain"] != "all"}

    # 2) 캔버스 생성
    print("\n■ 캔버스 생성")
    n_cv = 0
    for cv in CANVASES:
        cid = cid_by_dataset.get(cv["channel_id"])
        if not cid:
            continue
        r = requests.post(f"{API}/conversations.canvases.create", headers=HJ, json={
            "channel_id": cid, "title": cv["title"],
            "document_content": {"type": "markdown", "markdown": cv["markdown"]}}, timeout=30).json()
        if r.get("ok"):
            n_cv += 1
        else:
            print(f"   ✗ canvas {cv['title']}: {r.get('error')}", file=sys.stderr)
        time.sleep(0.8)
    print(f"   ✓ 캔버스 {n_cv}개")

    # 3) 도메인별 케이스 추적 리스트
    print("\n■ 케이스 추적 리스트 (도메인별)")
    schema = build_list_schema()
    for dom, ko in [(d, DOM_KO[d]) for d in ["practicum", "scholarship", "academic", "complaint", "international", "student_success"]]:
        cid = cid_by_domain.get(dom)
        if not cid:
            continue
        r = requests.post(f"{API}/slackLists.create", headers=HJ,
                          json={"name": f"{ko} 케이스 추적", "schema": schema}, timeout=30).json()
        if not r.get("ok"):
            print(f"   ✗ list {ko}: {r.get('error')}", file=sys.stderr)
            continue
        lid = r["list_id"]
        colmap = {c["key"]: c["id"] for c in r["list_metadata"]["schema"]}
        dom_cases = [c for c in CASES if c["domain"] == dom]
        for c in dom_cases:
            due = (c["next_actions"][0]["due_at"][:10] if c.get("next_actions") else c["updated_at"][:10])
            fields = [
                {"column_id": colmap["name"], "rich_text": rt(c["title"])},
                {"column_id": colmap["status"], "select": [ST_KO.get(c["status"], c["status"])]},
                {"column_id": colmap["priority"], "select": [PR_KO.get(c["priority"], c["priority"])]},
                {"column_id": colmap["owner"], "rich_text": rt(c["owner_name"])},
                {"column_id": colmap["report_to"], "user": [DEAN]},
                {"column_id": colmap["due"], "date": [due]},
                {"column_id": colmap["missing"], "rich_text": rt(", ".join(c["missing_documents"]) or "없음")},
                {"column_id": colmap["case_id"], "rich_text": rt(c["case_id"])},
            ]
            ir = requests.post(f"{API}/slackLists.items.create", headers=HJ,
                               json={"list_id": lid, "initial_fields": fields}, timeout=30).json()
            iid = ir.get("item", {}).get("id")
            time.sleep(0.25)
            for na in c.get("next_actions", []):
                sub = [
                    {"column_id": colmap["name"], "rich_text": rt(na["action"])},
                    {"column_id": colmap["status"], "select": ["완료" if na.get("status") == "done" else "처리중"]},
                    {"column_id": colmap["owner"], "rich_text": rt(c["owner_name"])},
                    {"column_id": colmap["due"], "date": [na["due_at"][:10]]},
                ]
                body = {"list_id": lid, "initial_fields": sub}
                if iid:
                    body["parent_item_id"] = iid
                requests.post(f"{API}/slackLists.items.create", headers=HJ, json=body, timeout=30)
                time.sleep(0.2)
        requests.post(f"{API}/slackLists.access.set", headers=HJ,
                      json={"list_id": lid, "channel_ids": [cid], "access_level": "write"}, timeout=30)
        print(f"   ✓ {ko} 케이스 추적: {len(dom_cases)}건 (list {lid})")
        time.sleep(1.0)

    # 4) 채널 인트로 + 핵심 케이스 하이라이트
    print("\n■ 인트로/하이라이트 게시")
    for dom in ["practicum", "scholarship", "academic", "complaint", "international", "student_success"]:
        cid = cid_by_domain.get(dom)
        if not cid:
            continue
        ko = DOM_KO[dom]
        dom_cases = sorted([c for c in CASES if c["domain"] == dom],
                           key=lambda c: {"urgent": 0, "high": 1, "normal": 2, "low": 3}[c["priority"]])[:4]
        lines = [f":pushpin: *{ko} 운영 채널* — CampusCase Desk 연동 (synthetic_demo)",
                 f"케이스 현황·태스크·승인은 상단 *리스트* 와 *캔버스* 에서 추적합니다. 핵심 케이스 미리보기:"]
        for c in dom_cases:
            miss = f" · 미제출 {len(c['missing_documents'])}건" if c["missing_documents"] else ""
            lines.append(f"• `{c['case_id']}` {c['title']} — {ST_KO.get(c['status'])}/{PR_KO.get(c['priority'])} · 담당 {c['owner_name']}{miss}")
        post(cid, "\n".join(lines))
        time.sleep(0.8)
    # dean-report 인트로
    dr = name_to_id.get("#dean-report")
    if dr:
        post(dr, f":bar_chart: *학장 보고/결재 채널* — <@{DEAN}>\nCampusCase Desk 작업(Task)이 매일 *아침 브리핑·승인 큐·리스크*를 여기에 게시합니다. (synthetic_demo)")
    nt = name_to_id.get("#college-notice")
    if nt:
        post(nt, ":loudspeaker: *CampusFlow 운영 공지 채널* — 도메인별 케이스 운영 데이터가 채널·캔버스·리스트로 제공됩니다. (synthetic_demo)")
    print("\n완료. Slack에서 새 채널/캔버스/리스트를 확인하세요.")


if __name__ == "__main__":
    main()
