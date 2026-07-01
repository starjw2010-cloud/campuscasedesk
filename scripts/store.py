from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def backend_name():
    return os.environ.get("DATA_BACKEND", "jsonl").strip().lower()


def _mariadb():
    import mariadb_store

    return mariadb_store


def using_mariadb():
    return backend_name() in {"mariadb", "mysql"}


def load_json(name):
    if using_mariadb():
        return _mariadb().load_json(name)
    path = DATA / name
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(name):
    if using_mariadb():
        return _mariadb().load_jsonl(name)
    path = DATA / name
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def append_jsonl(name, row):
    if using_mariadb():
        return _mariadb().append_jsonl(name, row)
    path = DATA / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def now_text():
    return datetime.now().isoformat(timespec="seconds")


def get_case(case_id):
    if using_mariadb():
        return _mariadb().get_case(case_id)
    for case in load_jsonl("cases.jsonl"):
        if case.get("case_id") == case_id:
            return case
    return None


def related_items(case_id):
    if using_mariadb():
        return _mariadb().related_items(case_id)
    return [row for row in load_jsonl("relationships.jsonl") if row.get("from_id") == case_id or row.get("to_id") == case_id]
