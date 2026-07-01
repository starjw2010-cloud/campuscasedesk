#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import mariadb_store


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
KNOWLEDGE = ROOT / "knowledge"


ORDERED_JSON = [
    ("users.json", "users"),
    ("students.json", "students"),
    ("channels.json", "channels"),
    ("canvases.json", "canvases"),
]

ORDERED_JSONL = [
    ("cases.jsonl", "cases"),
    ("tasks.jsonl", "tasks"),
    ("approvals.jsonl", "approvals"),
    ("documents.jsonl", "documents"),
    ("relationships.jsonl", "relationships"),
    ("slack_threads.jsonl", "slack_threads"),
]


def split_sql_statements(sql: str):
    sql = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--"))
    statements = []
    current = []
    in_string = None
    escaped = False
    for char in sql:
        current.append(char)
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
        elif char in {"'", '"'}:
            in_string = char
        elif char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement[:-1].strip())
            current = []
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return [stmt for stmt in statements if stmt]


def ensure_database():
    cfg = mariadb_store._config()
    db_name = cfg["database"]
    with mariadb_store.connect(database=False) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )


def apply_schema():
    ensure_database()
    sql = mariadb_store.SCHEMA_PATH.read_text(encoding="utf-8")
    with mariadb_store.connect() as conn:
        cursor = conn.cursor()
        for statement in split_sql_statements(sql):
            cursor.execute(statement)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def parse_frontmatter(text: str):
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :].lstrip()
    meta = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            value = [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]
        else:
            value = value.strip('"').strip("'")
        meta[key.strip()] = value
    return meta, body


def import_json_files():
    counts = {}
    for filename, table in ORDERED_JSON:
        path = DATA / filename
        if not path.exists():
            continue
        rows = read_json(path)
        if not isinstance(rows, list):
            rows = [rows]
        mariadb_store.bulk_insert_payloads(table, rows)
        counts[table] = len(rows)
    workspace = DATA / "workspace_map.json"
    if workspace.exists():
        row = read_json(workspace)
        mariadb_store.bulk_insert_payloads("workspace_map", [row])
        counts["workspace_map"] = 1
    return counts


def import_jsonl_files():
    counts = {}
    for filename, table in ORDERED_JSONL:
        path = DATA / filename
        if not path.exists():
            continue
        rows = read_jsonl(path)
        mariadb_store.bulk_insert_payloads(table, rows)
        counts[table] = len(rows)
    return counts


def import_rag_documents():
    index_path = KNOWLEDGE / "index.json"
    if not index_path.exists():
        return 0
    index = read_json(index_path)
    count = 0
    rows_to_insert = []
    for item in index.get("documents", []):
        path = ROOT / item.get("path", "")
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(raw)
        row = dict(item)
        row.update({key: value for key, value in frontmatter.items() if value not in (None, "")})
        row["path"] = item["path"]
        row["body"] = body
        row["source_type"] = row.get("source_type", "synthetic_demo")
        rows_to_insert.append(row)
        count += 1
    mariadb_store.bulk_insert_payloads("rag_documents", rows_to_insert)
    return count


def main():
    apply_schema()
    counts = {}
    counts.update(import_json_files())
    counts.update(import_jsonl_files())
    counts["rag_documents"] = import_rag_documents()
    print(json.dumps({"ok": True, "imported": counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), file=sys.stderr)
        raise
