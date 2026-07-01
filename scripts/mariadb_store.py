from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "database" / "mariadb_schema.sql"

JSONL_TABLES = {
    "cases.jsonl": "cases",
    "tasks.jsonl": "tasks",
    "approvals.jsonl": "approvals",
    "documents.jsonl": "documents",
    "relationships.jsonl": "relationships",
    "slack_threads.jsonl": "slack_threads",
}

JSON_TABLES = {
    "users.json": "users",
    "students.json": "students",
    "channels.json": "channels",
    "canvases.json": "canvases",
}

PRIMARY_KEYS = {
    "users": "user_id",
    "students": "student_ref",
    "channels": "channel_id",
    "canvases": "canvas_id",
    "cases": "case_id",
    "tasks": "task_id",
    "approvals": "approval_id",
    "documents": "document_id",
    "relationships": "rel_id",
    "slack_threads": "thread_id",
    "rag_documents": "path",
    "workspace_map": "workspace_key",
}


def _connector():
    try:
        import mysql.connector  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "MariaDB backend requires mysql-connector-python. "
            "Install dependencies or keep DATA_BACKEND=jsonl."
        ) from exc
    return mysql.connector


def _config():
    url = os.environ.get("MARIADB_URL") or os.environ.get("DATABASE_URL")
    if url:
        parsed = urlparse(url)
        return {
            "host": parsed.hostname or "127.0.0.1",
            "port": parsed.port or 3306,
            "user": parsed.username or "root",
            "password": parsed.password or "",
            "database": parsed.path.lstrip("/") or os.environ.get("MARIADB_DATABASE", "campusflow"),
        }
    return {
        "host": os.environ.get("MARIADB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MARIADB_PORT", "3306")),
        "user": os.environ.get("MARIADB_USER", "root"),
        "password": os.environ.get("MARIADB_PASSWORD", ""),
        "database": os.environ.get("MARIADB_DATABASE", "campusflow"),
    }


@contextmanager
def connect(database=True):
    mysql = _connector()
    cfg = _config()
    if not database:
        cfg = dict(cfg)
        cfg.pop("database", None)
    conn = mysql.connect(charset="utf8mb4", collation="utf8mb4_unicode_ci", autocommit=False, **cfg)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _json(value):
    return json.dumps(value, ensure_ascii=False)


def _loads_payload(row):
    payload = row.get("payload")
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        return json.loads(payload)
    return payload


def _select_payloads(table):
    with connect() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SELECT payload FROM {table}")
        return [_loads_payload(row) for row in cursor.fetchall()]


def load_jsonl(name):
    table = JSONL_TABLES.get(name)
    if not table:
        return []
    return _select_payloads(table)


def load_json(name):
    if name == "workspace_map.json":
        rows = _select_payloads("workspace_map")
        return rows[0] if rows else {}
    table = JSON_TABLES.get(name)
    if not table:
        return []
    return _select_payloads(table)


def get_case(case_id):
    with connect() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT payload FROM cases WHERE case_id = %s", (case_id,))
        row = cursor.fetchone()
        return _loads_payload(row) if row else None


def related_items(entity_id):
    with connect() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT payload FROM relationships WHERE from_id = %s OR to_id = %s",
            (entity_id, entity_id),
        )
        return [_loads_payload(row) for row in cursor.fetchall()]


def insert_payload(table, row):
    with connect() as conn:
        cursor = conn.cursor()
        execute_insert(cursor, table, row)


def execute_insert(cursor, table, row):
    pk = PRIMARY_KEYS[table]
    columns = _table_columns(table, row)
    names = list(columns)
    values = [columns[name] for name in names]
    placeholders = ", ".join(["%s"] * len(names))
    updates = ", ".join([f"{name}=VALUES({name})" for name in names if name != pk])
    sql = f"INSERT INTO {table} ({', '.join(names)}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {updates}"
    cursor.execute(sql, values)


def bulk_insert_payloads(table, rows):
    rows = list(rows)
    if not rows:
        return 0
    with connect() as conn:
        cursor = conn.cursor()
        for row in rows:
            execute_insert(cursor, table, row)
    return len(rows)


def append_jsonl(name, row):
    table = JSONL_TABLES.get(name)
    if not table:
        raise ValueError(f"Unsupported MariaDB JSONL target: {name}")
    insert_payload(table, row)


def _table_columns(table, row):
    payload = _json(row)
    if table == "users":
        return {
            "user_id": row.get("user_id"),
            "name": row.get("name", ""),
            "email": row.get("email"),
            "role": row.get("role"),
            "department": row.get("department"),
            "manager_user_id": row.get("manager_user_id"),
            "domains": _json(row.get("domains", [])),
            "source_type": row.get("source_type", "synthetic_demo"),
            "payload": payload,
        }
    if table == "students":
        return {
            "student_ref": row.get("student_ref"),
            "name": row.get("name"),
            "masked_name": row.get("masked_name"),
            "student_no_masked": row.get("student_no_masked"),
            "department": row.get("department"),
            "year": row.get("year"),
            "nationality": row.get("nationality"),
            "source_type": row.get("source_type", "synthetic_demo"),
            "payload": payload,
        }
    if table == "channels":
        return {
            "channel_id": row.get("channel_id"),
            "name": row.get("name", ""),
            "ko_label": row.get("ko_label"),
            "domain": row.get("domain"),
            "purpose": row.get("purpose"),
            "members": _json(row.get("members", [])),
            "source_type": row.get("source_type", "synthetic_demo"),
            "payload": payload,
        }
    if table == "canvases":
        return {
            "canvas_id": row.get("canvas_id"),
            "title": row.get("title", ""),
            "domain": row.get("domain"),
            "channel_id": row.get("channel_id"),
            "channel_name": row.get("channel_name"),
            "related_case_ids": _json(row.get("related_case_ids", [])),
            "markdown": row.get("markdown"),
            "source_type": row.get("source_type", "synthetic_demo"),
            "payload": payload,
        }
    if table == "cases":
        return {
            "case_id": row.get("case_id"),
            "title": row.get("title", ""),
            "domain": row.get("domain", ""),
            "case_type": row.get("case_type", ""),
            "status": row.get("status", ""),
            "priority": row.get("priority"),
            "risk_level": row.get("risk_level"),
            "student_ref": row.get("student_ref"),
            "student_name": row.get("student_name"),
            "owner_user_id": row.get("owner_user_id"),
            "owner_name": row.get("owner_name"),
            "approver_user_id": row.get("approver_user_id"),
            "approver_name": row.get("approver_name"),
            "related_channel_id": row.get("related_channel_id"),
            "related_channel_name": row.get("related_channel_name"),
            "related_thread_id": row.get("related_thread_id"),
            "related_canvas_id": row.get("related_canvas_id"),
            "related_canvas_title": row.get("related_canvas_title"),
            "consent_on_file": row.get("consent_on_file"),
            "required_documents": _json(row.get("required_documents", [])),
            "submitted_documents": _json(row.get("submitted_documents", [])),
            "missing_documents": _json(row.get("missing_documents", [])),
            "related_rag_paths": _json(row.get("related_rag_paths", [])),
            "next_actions": _json(row.get("next_actions", [])),
            "next_action": row.get("next_action"),
            "summary": row.get("summary"),
            "timeline": _json(row.get("timeline", [])),
            "created_at_text": row.get("created_at"),
            "updated_at_text": row.get("updated_at"),
            "source_type": row.get("source_type", "synthetic_demo"),
            "payload": payload,
        }
    if table == "tasks":
        return {
            "task_id": row.get("task_id"),
            "case_id": row.get("case_id"),
            "title": row.get("title", ""),
            "owner_user_id": row.get("owner_user_id"),
            "owner_name": row.get("owner_name"),
            "status": row.get("status", ""),
            "priority": row.get("priority"),
            "due_at": row.get("due_at"),
            "created_at": row.get("created_at"),
            "source_type": row.get("source_type", "synthetic_demo"),
            "payload": payload,
        }
    if table == "approvals":
        return {
            "approval_id": row.get("approval_id"),
            "case_id": row.get("case_id"),
            "type": row.get("type"),
            "requester_user_id": row.get("requester_user_id"),
            "requester_name": row.get("requester_name"),
            "approver_user_id": row.get("approver_user_id"),
            "approver_name": row.get("approver_name"),
            "status": row.get("status", ""),
            "requested_at": row.get("requested_at"),
            "decided_at": row.get("decided_at"),
            "due_at": row.get("due_at"),
            "comment": row.get("comment"),
            "source_type": row.get("source_type", "synthetic_demo"),
            "payload": payload,
        }
    if table == "documents":
        return {
            "document_id": row.get("document_id"),
            "case_id": row.get("case_id"),
            "doc_type": row.get("doc_type"),
            "title": row.get("title"),
            "status": row.get("status", ""),
            "student_ref": row.get("student_ref"),
            "owner_user_id": row.get("owner_user_id"),
            "rag_path": row.get("rag_path"),
            "file_ref": row.get("file_ref"),
            "pii_masked": row.get("pii_masked"),
            "consent_required": row.get("consent_required"),
            "created_at": row.get("created_at"),
            "source_type": row.get("source_type", "synthetic_demo"),
            "payload": payload,
        }
    if table == "relationships":
        return {
            "rel_id": row.get("rel_id"),
            "from_id": row.get("from_id"),
            "from_type": row.get("from_type"),
            "to_id": row.get("to_id"),
            "to_type": row.get("to_type"),
            "relation": row.get("relation"),
            "source_type": row.get("source_type", "synthetic_demo"),
            "payload": payload,
        }
    if table == "slack_threads":
        return {
            "thread_id": row.get("thread_id"),
            "case_id": row.get("case_id"),
            "title": row.get("title"),
            "channel_id": row.get("channel_id"),
            "channel_name": row.get("channel_name"),
            "participants": _json(row.get("participants", [])),
            "message_count": row.get("message_count"),
            "messages": _json(row.get("messages", [])),
            "created_at": row.get("created_at"),
            "source_type": row.get("source_type", "synthetic_demo"),
            "payload": payload,
        }
    if table == "rag_documents":
        return {
            "path": row.get("path"),
            "doc_id": row.get("doc_id"),
            "domain": row.get("domain"),
            "title": row.get("title"),
            "applies_to_case_types": _json(row.get("applies_to_case_types", [])),
            "source_type": row.get("source_type", "synthetic_demo"),
            "body": row.get("body"),
            "payload": payload,
        }
    if table == "workspace_map":
        return {
            "workspace_key": row.get("workspace", "default"),
            "generated_at": row.get("generated_at"),
            "source_type": row.get("source_type", "synthetic_demo"),
            "payload": payload,
        }
    raise ValueError(f"Unsupported table: {table}")
