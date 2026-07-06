from __future__ import annotations

import sys

sys.path.insert(0, "scripts")
import mcp_adapter  # noqa: E402


def call(name, arguments):
    response = mcp_adapter.handle_json_rpc(
        {"jsonrpc": "2.0", "id": name, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
    )
    assert "error" not in response, response
    return response["result"]["structuredContent"]


def main():
    assert len(mcp_adapter.tool_definitions()) == 14
    assert call("find_cases", {"query": "현장실습 중도 포기"})["cases"]
    assert call("find_cases", {"has_missing_documents": True, "risk_level": "high"})["cases"]
    assert call("get_case_detail", {"case_id": "case_prac_001"})["found"]
    assert call("list_pending_tasks", {"priority": "high"})["tasks"]
    assert call("trace_slack_context", {"case_id": "case_prac_001"})["found"]
    assert call("list_approvals_due_today", {"date": "2026-07-01"})["approvals"]
    assert call("group_cases_by_owner", {"domain": "practicum"})["groups"]
    assert call("get_student_cases", {"student_name": "김하늘"})["cases"]
    assert call("list_documents", {"case_id": "case_prac_001", "status": "미제출"})["documents"]
    assert call("get_rag_refs", {"case_id": "case_prac_001"})["refs"]
    assert call("search_rag", {"query": "장학 중복수혜 규정"})["results"][0]["path"] == "knowledge/scholarship/duplicate-award.md"
    assert call("search_rag", {"query": "실습 그만두면 학점은 어떻게 돼", "mode": "vector"})["results"]
    assert call("rag_vector_stats", {})["chunks"]
    assert call("get_doc", {"path": "knowledge/practicum/early-withdrawal.md"})["found"]
    assert call("list_docs", {"domain": "practicum"})["documents"]
    print({"ok": True, "service": "campuscasedesk"})


if __name__ == "__main__":
    main()
