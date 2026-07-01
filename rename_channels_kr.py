#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rename_channels_kr.py — CampusFlow 운영 채널 8개를 한국어명으로 rename + 데이터셋 동기화.
Slack conversations.rename + data/*.json(l) 의 채널명 참조를 일괄 치환해 MCP 일관성 유지.
사용: export $(grep -v '^#' /Volumes/jee_insight/슬랙앱/hanbit-sandbox/.env | xargs); python3 rename_channels_kr.py
"""
import os, sys, json, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
BOT = os.environ["SLACK_BOT_TOKEN"]
API = "https://slack.com/api"
HJ = {"Authorization": f"Bearer {BOT}", "Content-Type": "application/json; charset=utf-8"}

# eng norm name → (korean name, ko_label, domain)
MAP = {
    "practicum-ops":     ("케이스-현장실습", "현장실습 운영", "practicum"),
    "scholarship-review":("케이스-장학",     "장학 운영", "scholarship"),
    "academic-ops":      ("케이스-학사",     "학사 운영", "academic"),
    "civil-desk":        ("케이스-민원",     "민원 운영", "complaint"),
    "intl-support":      ("케이스-유학생",   "유학생 운영", "international"),
    "success-care":      ("케이스-학생성공", "학생성공 운영", "student_success"),
    "dean-report":       ("케이스-학장보고", "학장 보고", "all"),
    "college-notice":    ("케이스-운영공지", "운영 공지", "all"),
}

ids = json.load(open(ROOT / "campus_channel_ids.json"))

# 1) Slack rename
print("■ Slack 채널 rename")
new_ids = {}
for eng, cid in ids.items():
    if eng not in MAP:
        new_ids[eng] = cid; continue
    kor, label, dom = MAP[eng]
    r = requests.post(f"{API}/conversations.rename", headers=HJ, json={"channel": cid, "name": kor}, timeout=30).json()
    if r.get("ok"):
        print(f"   ✓ {eng} → {kor}")
    elif r.get("error") in ("name_taken",):
        print(f"   · {eng}: 이미 {kor} 인 듯 (스킵)")
    else:
        print(f"   ✗ {eng}: {r.get('error')}", file=sys.stderr)
    new_ids[kor] = cid
    time.sleep(1.0)
json.dump(new_ids, open(ROOT / "campus_channel_ids.json", "w"), ensure_ascii=False, indent=2)

# 2) 데이터셋 텍스트 치환 ("#eng" → "#kor")
print("\n■ 데이터셋 채널명 동기화")
files = ["channels.json", "cases.jsonl", "slack_threads.jsonl", "canvases.json", "workspace_map.json"]
for fn in files:
    p = DATA / fn
    if not p.exists(): continue
    txt = p.read_text(encoding="utf-8")
    for eng, (kor, label, dom) in MAP.items():
        txt = txt.replace(f"#{eng}", f"#{kor}")
    p.write_text(txt, encoding="utf-8")
    print(f"   ✓ {fn}")

# 3) channels.json ko_label 갱신
ch = json.load(open(DATA / "channels.json"))
for c in ch:
    nm = c["name"].lstrip("#")
    for eng, (kor, label, dom) in MAP.items():
        if nm == kor:
            c["ko_label"] = label
json.dump(ch, open(DATA / "channels.json", "w"), ensure_ascii=False, indent=2)
print("   ✓ channels.json ko_label")

print("\n완료. verify_integrity 로 무결성 재확인하세요.")
