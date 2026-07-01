#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

os.environ.setdefault("DATA_BACKEND", "mariadb")

sys.path.insert(0, "scripts")

import mariadb_store  # noqa: E402
import mcp_adapter  # noqa: E402


EXPECTED_MIN_COUNTS = {
    "students": 500,
    "cases": 300,
    "tasks": 1000,
    "approvals": 250,
    "documents": 800,
    "slack_threads": 500,
    "canvases": 50,
    "relationships": 5000,
    "rag_documents": 30,
}


def _count(table: str) -> int:
    with mariadb_store.connect() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        row = cursor.fetchone()
        return int(row[0])


def _call_tool(name: str, arguments: dict):
    response = mcp_adapter.handle_json_rpc(
        {
            "jsonrpc": "2.0",
            "id": name,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )
    if "error" in response:
        raise AssertionError(response)
    return response["result"]["structuredContent"]


def main() -> None:
    if not (os.environ.get("MARIADB_URL") or os.environ.get("MARIADB_HOST")):
        raise SystemExit("Set MARIADB_URL or MARIADB_HOST before running this check.")

    counts = {table: _count(table) for table in EXPECTED_MIN_COUNTS}
    too_small = {
        table: {"actual": counts[table], "minimum": minimum}
        for table, minimum in EXPECTED_MIN_COUNTS.items()
        if counts[table] < minimum
    }
    if too_small:
        raise AssertionError({"error": "imported row counts are too small", "tables": too_small})

    case_detail = _call_tool("get_case_detail", {"case_id": "case_prac_001"})
    assert case_detail["found"], case_detail
    assert case_detail["case"]["student_name"] == "김하늘", case_detail

    approvals = _call_tool("list_approvals_due_today", {"date": "2026-07-01", "limit": 50})
    assert approvals["approvals"], approvals

    rag = _call_tool("search_rag", {"query": "장학 중복수혜 규정", "limit": 3})
    assert rag["results"][0]["path"] == "knowledge/scholarship/duplicate-award.md", rag

    print(
        json.dumps(
            {
                "ok": True,
                "backend": os.environ.get("DATA_BACKEND"),
                "counts": counts,
                "anchor_case": case_detail["case"]["case_id"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

