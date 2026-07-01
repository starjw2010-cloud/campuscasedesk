#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_rag_refs.py — cases.jsonl의 모든 related_rag_path가 knowledge/ 아래 실제 파일로 존재하는지 검증.
+ knowledge/index.json 일관성 + applies_to_case_types 가 데이터셋 case_type와 매칭되는지 확인.
사용: python3 scripts/verify_rag_refs.py
"""
import json, sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
cases = [json.loads(l) for l in (ROOT / "data/cases.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

referenced = defaultdict(set)
for c in cases:
    for p in c["related_rag_paths"]:
        referenced[p].add(c["case_type"])

errors = []
# 1) 참조된 모든 경로에 파일 존재
for p in sorted(referenced):
    if not (ROOT / p).exists():
        errors.append(f"누락 RAG 파일: {p} (참조 case_type: {sorted(referenced[p])})")

# 2) index.json 일관성
idx_path = ROOT / "knowledge/index.json"
if not idx_path.exists():
    errors.append("knowledge/index.json 없음")
else:
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    idx_paths = {d["path"] for d in idx["documents"]}
    for p in referenced:
        if p not in idx_paths:
            errors.append(f"index.json 미등록: {p}")
    # 3) applies_to_case_types 매칭 (참조된 case_type이 문서 메타에 포함)
    meta = {d["path"]: set(d["applies_to_case_types"]) for d in idx["documents"]}
    for p, cts in referenced.items():
        if p in meta and not cts.issubset(meta[p]):
            errors.append(f"{p}: applies_to_case_types 불일치 (데이터 {sorted(cts)} ⊄ 문서 {sorted(meta[p])})")

if errors:
    print(f"❌ RAG 참조 무결성 실패 {len(errors)}건:")
    for e in errors[:30]:
        print("  -", e)
    sys.exit(1)
print(f"✅ RAG 참조 무결성 통과 — 참조 경로 {len(referenced)}개 전부 파일 존재 + index/case_type 매칭")
