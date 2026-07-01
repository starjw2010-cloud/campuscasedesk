#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_integrity.py — CampusCase Desk seed dataset 참조 무결성·요건 검사.
orphan(case/thread/task/approval/document) 0, 모든 상호참조 유효, 도메인/볼륨 요건 충족 확인.
사용: python3 scripts/verify_integrity.py
"""
import json, sys
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
def jl(name): return [json.loads(l) for l in (DATA/name).read_text(encoding="utf-8").splitlines() if l.strip()]
def jj(name): return json.loads((DATA/name).read_text(encoding="utf-8"))

users = {u["user_id"] for u in jj("users.json")}
channels = {c["channel_id"] for c in jj("channels.json")}
canvases = {c["canvas_id"] for c in jj("canvases.json")}
students = {s["student_ref"] for s in jj("students.json")}
cases = jl("cases.jsonl"); case_ids = {c["case_id"] for c in cases}
threads = jl("slack_threads.jsonl"); thread_ids = {t["thread_id"] for t in threads}
tasks = jl("tasks.jsonl"); approvals = jl("approvals.jsonl"); documents = jl("documents.jsonl")
doc_ids = {d["document_id"] for d in documents}
rels = jl("relationships.jsonl")
rag_paths = {p for c in cases for p in c["related_rag_paths"]}

errors, warns = [], []
def chk(cond, msg):
    if not cond: errors.append(msg)

# 1) case 필드 참조 무결성
for c in cases:
    cid = c["case_id"]
    chk(c["owner_user_id"] in users, f"{cid}: owner 미존재 {c['owner_user_id']}")
    chk(c["approver_user_id"] in users, f"{cid}: approver 미존재 {c['approver_user_id']}")
    chk(c["student_ref"] in students, f"{cid}: student 미존재 {c['student_ref']}")
    chk(c["related_channel_id"] in channels, f"{cid}: channel 미존재 {c['related_channel_id']}")
    chk(c["related_thread_id"] in thread_ids, f"{cid}: thread 미존재 {c['related_thread_id']}")
    chk(c["related_canvas_id"] in canvases, f"{cid}: canvas 미존재 {c['related_canvas_id']}")
    chk(len(c["related_rag_paths"]) >= 1, f"{cid}: rag_path 없음")
    chk(len(c["next_actions"]) >= 1, f"{cid}: next_action 없음")
    chk(c["source_type"] == "synthetic_demo", f"{cid}: source_type 누락")
    # 케이스당 최소 1 스레드 + 근거(문서 또는 rag)
    chk(any(t["case_id"] == cid for t in threads), f"{cid}: 연결 스레드 없음")
    chk(any(d["case_id"] == cid for d in documents) or c["related_rag_paths"], f"{cid}: 근거 문서/RAG 없음")

# 2) orphan 검사
for t in threads: chk(t["case_id"] in case_ids, f"orphan thread {t['thread_id']} → {t['case_id']}")
for t in tasks: chk(t["case_id"] in case_ids, f"orphan task {t['task_id']} → {t['case_id']}")
for a in approvals:
    chk(a["case_id"] in case_ids, f"orphan approval {a['approval_id']} → {a['case_id']}")
    chk(a["approver_user_id"] in users, f"{a['approval_id']}: approver 미존재")
for d in documents:
    chk(d["case_id"] in case_ids, f"orphan document {d['document_id']} → {d['case_id']}")
    chk(d["student_ref"] in students, f"{d['document_id']}: student 미존재")

# 3) relationships 양끝 유효성
task_ids = {t["task_id"] for t in tasks}; approval_ids = {a["approval_id"] for a in approvals}
RES = {"case": case_ids, "user": users, "channel": channels, "thread": thread_ids,
       "canvas": canvases, "document": doc_ids, "student": students, "rag_path": rag_paths,
       "task": task_ids, "approval": approval_ids}
def resolves(t, i):
    return i in RES.get(t, set())
for r in rels:
    if not resolves(r["from_type"], r["from_id"]): errors.append(f"rel {r['rel_id']}: from {r['from_type']}:{r['from_id']} 미해결")
    if not resolves(r["to_type"], r["to_id"]): errors.append(f"rel {r['rel_id']}: to {r['to_type']}:{r['to_id']} 미해결")
    if r["relation"].startswith("case_to"): chk(r["from_id"] in case_ids, f"rel {r['rel_id']}: case_to_* from 비케이스")

# 4) 볼륨·도메인 요건
from collections import Counter
dom = Counter(c["domain"] for c in cases)
req = {"cases": (len(cases), 80), "tasks": (len(tasks), 180), "approvals": (len(approvals), 60),
       "documents": (len(documents), 120), "threads": (len(threads), 150), "canvases": (len(canvases), 20)}
for k, (v, m) in req.items(): chk(v >= m, f"{k} {v} < 요건 {m}")
for d, cnt in dom.items(): chk(cnt >= 12, f"도메인 {d} 케이스 {cnt} < 12")
chk(len(dom) == 6, f"도메인 수 {len(dom)} != 6")

# 5) 모든 관계 종류 존재
need_rel = {"case_to_student","case_to_owner","case_to_approver","case_to_channel","case_to_thread",
            "case_to_canvas","case_to_document","case_to_rag_path","task_to_case","approval_to_case",
            "document_to_case","thread_to_case"}
have = {r["relation"] for r in rels}
for nr in need_rel: chk(nr in have, f"관계 종류 누락: {nr}")

if errors:
    print(f"❌ 무결성 실패 {len(errors)}건 (상위 20):")
    for e in errors[:20]: print("  -", e)
    sys.exit(1)
print("✅ 무결성 통과")
print(json.dumps({"cases": len(cases), "by_domain": dict(dom), "tasks": len(tasks),
                  "approvals": len(approvals), "documents": len(documents), "threads": len(threads),
                  "canvases": len(canvases), "relationships": len(rels),
                  "relation_kinds": len(have)}, ensure_ascii=False))
