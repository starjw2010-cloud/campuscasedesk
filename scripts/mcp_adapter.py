from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date
from uuid import uuid4

import rag_store
import store


PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "campuscasedesk", "version": "0.1.0"}
MAX_MCP_TEXT_CHARS = 2200


def _success(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _text_result(text, structured):
    text = str(text or "").strip()
    if len(text) > MAX_MCP_TEXT_CHARS:
        text = text[: MAX_MCP_TEXT_CHARS - 90].rstrip() + "\n\n...응답이 길어 일부를 줄였습니다."
    return {"content": [{"type": "text", "text": text}], "structuredContent": structured}


def _compact_case(case):
    if not case:
        return {}
    keys = [
        "case_id",
        "title",
        "domain",
        "case_type",
        "status",
        "priority",
        "risk_level",
        "student_name",
        "student_ref",
        "owner_user_id",
        "owner_name",
        "approver_user_id",
        "approver_name",
        "related_channel_name",
        "related_thread_id",
        "related_canvas_title",
        "related_rag_paths",
        "missing_documents",
        "next_action",
        "summary",
    ]
    return {key: case.get(key) for key in keys if key in case}


def _compact_row(row, keys):
    return {key: row.get(key) for key in keys if key in row}


def _as_bool_filter(value):
    if value in (None, "", "all"):
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "있음", "예"}


def _has_missing_documents(case):
    return bool(case.get("missing_documents"))


def _case_matches_filters(case, filters):
    owner_user_id = filters.get("owner_user_id") or ""
    priority = filters.get("priority") or "all"
    risk_level = filters.get("risk_level") or "all"
    has_missing_documents = _as_bool_filter(filters.get("has_missing_documents"))
    consent_on_file = _as_bool_filter(filters.get("consent_on_file"))
    if owner_user_id and case.get("owner_user_id") != owner_user_id:
        return False
    if priority != "all" and case.get("priority") != priority:
        return False
    if risk_level != "all" and case.get("risk_level") != risk_level:
        return False
    if has_missing_documents is not None and _has_missing_documents(case) != has_missing_documents:
        return False
    if consent_on_file is not None and bool(case.get("consent_on_file")) != consent_on_file:
        return False
    return True


def _compact_document(row):
    return _compact_row(
        row,
        [
            "document_id",
            "case_id",
            "doc_type",
            "title",
            "status",
            "student_ref",
            "owner_user_id",
            "rag_path",
            "pii_masked",
            "consent_required",
            "source_type",
        ],
    )


def _case_lookup():
    return {case.get("case_id"): case for case in store.load_jsonl("cases.jsonl")}


def _match(text, query):
    if not query:
        return True
    tokens = [token for token in re.split(r"\s+", query.lower()) if token]
    haystack = text.lower()
    return all(token in haystack for token in tokens)


def tool_definitions():
    return [
        {
            "name": "find_cases",
            "description": "Find university operation cases by Korean keyword, domain, status, owner, priority, risk, missing documents, consent, or student name.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword such as 현장실습 중도 포기 or 김하늘."},
                    "domain": {"type": "string", "description": "Domain id or all.", "default": "all"},
                    "status": {"type": "string", "description": "Case status or all.", "default": "all"},
                    "owner_user_id": {"type": "string", "description": "Filter by case owner user id."},
                    "priority": {"type": "string", "description": "Filter by priority or all.", "default": "all"},
                    "risk_level": {"type": "string", "description": "Filter by risk level or all.", "default": "all"},
                    "has_missing_documents": {"type": "boolean", "description": "Filter cases with or without missing documents."},
                    "consent_on_file": {"type": "boolean", "description": "Filter by 개인정보 동의 확인 여부."},
                    "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
                },
            },
        },
        {
            "name": "get_case_detail",
            "description": "Get a specific case with tasks, approvals, documents, and linked Slack context.",
            "inputSchema": {"type": "object", "properties": {"case_id": {"type": "string"}}, "required": ["case_id"]},
        },
        {
            "name": "list_pending_tasks",
            "description": "List pending case tasks, optionally by owner or priority.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "owner_user_id": {"type": "string"},
                    "priority": {"type": "string", "default": "all"},
                    "limit": {"type": "integer", "default": 8},
                },
            },
        },
        {
            "name": "trace_slack_context",
            "description": "Show Slack channel, thread, canvas, and timeline context linked to a case.",
            "inputSchema": {"type": "object", "properties": {"case_id": {"type": "string"}}, "required": ["case_id"]},
        },
        {
            "name": "create_task",
            "description": "Create a follow-up task for a case. Demo mode persists to tasks.jsonl.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "title": {"type": "string"},
                    "owner_user_id": {"type": "string"},
                    "due_at": {"type": "string"},
                },
                "required": ["case_id", "title"],
            },
        },
        {
            "name": "list_approvals_due_today",
            "description": "List pending approvals whose due_at date matches today, grouped by approver.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "YYYY-MM-DD. Defaults to today's date."},
                    "domain": {"type": "string", "description": "Domain id or all.", "default": "all"},
                    "limit": {"type": "integer", "default": 20, "minimum": 1, "maximum": 50},
                },
            },
        },
        {
            "name": "group_cases_by_owner",
            "description": "Group cases by owner with optional domain/status/priority/risk/missing-document filters.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "default": "all"},
                    "status": {"type": "string", "default": "all"},
                    "priority": {"type": "string", "default": "all"},
                    "risk_level": {"type": "string", "default": "all"},
                    "has_missing_documents": {"type": "boolean"},
                    "consent_on_file": {"type": "boolean"},
                },
            },
        },
        {
            "name": "get_student_cases",
            "description": "Find all cases linked to a student by masked student_ref or student name.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "student_ref": {"type": "string"},
                    "student_name": {"type": "string"},
                    "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 20},
                },
            },
        },
        {
            "name": "list_documents",
            "description": "List case documents by case_id, status, owner, or document type.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "status": {"type": "string", "description": "Document status such as 미제출 or 제출완료."},
                    "owner_user_id": {"type": "string"},
                    "doc_type": {"type": "string"},
                    "limit": {"type": "integer", "default": 12, "minimum": 1, "maximum": 30},
                },
            },
        },
        {
            "name": "get_rag_refs",
            "description": "Return the RAG policy/procedure documents referenced by a case, including title and applies_to_case_types.",
            "inputSchema": {"type": "object", "properties": {"case_id": {"type": "string"}}, "required": ["case_id"]},
        },
        {
            "name": "search_rag",
            "description": "Search the CampusFlow RAG knowledge base with keyword, vector, or hybrid retrieval.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Korean policy/procedure search query."},
                    "domain": {"type": "string", "default": "all"},
                    "case_type": {"type": "string", "description": "Optional case_type metadata filter such as early_withdrawal."},
                    "mode": {
                        "type": "string",
                        "description": "Retrieval mode: hybrid, vector, or keyword.",
                        "default": "hybrid",
                    },
                    "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
                },
                "required": ["query"],
            },
        },
        {
            "name": "rag_vector_stats",
            "description": "Show local vector RAG index stats such as document, chunk, and term counts.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_doc",
            "description": "Open a RAG source document by path.",
            "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
        },
        {
            "name": "list_docs",
            "description": "List available RAG documents by domain.",
            "inputSchema": {"type": "object", "properties": {"domain": {"type": "string", "default": "all"}}},
        },
    ]


def find_cases(arguments):
    query = (arguments.get("query") or "").strip()
    domain = arguments.get("domain") or "all"
    status = arguments.get("status") or "all"
    limit = int(arguments.get("limit") or 5)
    results = []
    for case in store.load_jsonl("cases.jsonl"):
        text = " ".join(
            str(case.get(key, ""))
            for key in [
                "case_id",
                "title",
                "student_name",
                "summary",
                "status",
                "domain",
                "case_type",
                "risk_level",
                "owner_name",
                "missing_documents",
            ]
        )
        if domain != "all" and case.get("domain") != domain:
            continue
        if status != "all" and case.get("status") != status:
            continue
        if not _case_matches_filters(case, arguments):
            continue
        if not _match(text, query):
            continue
        results.append(_compact_case(case))
    structured = {
        "query": query,
        "domain": domain,
        "status": status,
        "filters": {
            key: arguments.get(key)
            for key in ["owner_user_id", "priority", "risk_level", "has_missing_documents", "consent_on_file"]
            if arguments.get(key) not in (None, "", "all")
        },
        "cases": results[:limit],
    }
    text = "\n".join(
        f"- {c['case_id']} {c['title']} · {c['status']} · risk {c.get('risk_level', 'n/a')} · 담당 {c.get('owner_name')}"
        for c in structured["cases"]
    ) or "검색된 케이스가 없습니다."
    return _text_result(text, structured)


def list_approvals_due_today(arguments):
    target_date = arguments.get("date") or date.today().isoformat()
    domain = arguments.get("domain") or "all"
    limit = int(arguments.get("limit") or 20)
    cases = _case_lookup()
    approvals = []
    grouped = defaultdict(list)
    for approval in store.load_jsonl("approvals.jsonl"):
        if approval.get("status") != "pending":
            continue
        if str(approval.get("due_at", ""))[:10] != target_date:
            continue
        case = cases.get(approval.get("case_id"), {})
        if domain != "all" and case.get("domain") != domain:
            continue
        row = _compact_row(
            approval,
            [
                "approval_id",
                "case_id",
                "type",
                "requester_name",
                "approver_user_id",
                "approver_name",
                "status",
                "requested_at",
                "due_at",
                "source_type",
            ],
        )
        row["case_title"] = case.get("title")
        row["domain"] = case.get("domain")
        row["priority"] = case.get("priority")
        row["risk_level"] = case.get("risk_level")
        approvals.append(row)
        grouped[row.get("approver_name") or row.get("approver_user_id") or "미지정"].append(row)
    approvals = approvals[:limit]
    structured = {
        "date": target_date,
        "domain": domain,
        "count": len(approvals),
        "approvals": approvals,
        "grouped_by_approver": {
            name: {
                "count": len(rows),
                "approval_ids": [row.get("approval_id") for row in rows[:limit]],
                "case_ids": [row.get("case_id") for row in rows[:limit]],
            }
            for name, rows in grouped.items()
        },
        "source_type": "synthetic_demo",
    }
    text = "\n".join(
        f"- {row['approval_id']} {row.get('case_title')} · 승인자 {row.get('approver_name')} · {row.get('due_at')}"
        for row in approvals
    ) or f"{target_date} 마감 승인 건이 없습니다."
    return _text_result(text, structured)


def group_cases_by_owner(arguments):
    domain = arguments.get("domain") or "all"
    status = arguments.get("status") or "all"
    groups = defaultdict(list)
    for case in store.load_jsonl("cases.jsonl"):
        if domain != "all" and case.get("domain") != domain:
            continue
        if status != "all" and case.get("status") != status:
            continue
        if not _case_matches_filters(case, arguments):
            continue
        owner_key = case.get("owner_name") or case.get("owner_user_id") or "미지정"
        groups[owner_key].append(_compact_case(case))
    owner_rows = []
    for owner, cases in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        owner_rows.append(
            {
                "owner": owner,
                "count": len(cases),
                "high_risk_count": len([case for case in cases if case.get("risk_level") == "high"]),
                "missing_document_count": len([case for case in cases if case.get("missing_documents")]),
                "cases": cases[:6],
            }
        )
    structured = {
        "domain": domain,
        "status": status,
        "groups": owner_rows,
        "source_type": "synthetic_demo",
    }
    text = "\n".join(
        f"- {row['owner']}: {row['count']}건 · 고위험 {row['high_risk_count']}건 · 서류누락 {row['missing_document_count']}건"
        for row in owner_rows
    ) or "조건에 맞는 케이스가 없습니다."
    return _text_result(text, structured)


def get_student_cases(arguments):
    student_ref = (arguments.get("student_ref") or "").strip()
    student_name = (arguments.get("student_name") or "").strip()
    limit = int(arguments.get("limit") or 10)
    rows = []
    for case in store.load_jsonl("cases.jsonl"):
        if student_ref and case.get("student_ref") != student_ref:
            continue
        if student_name and student_name not in str(case.get("student_name", "")):
            continue
        if not student_ref and not student_name:
            continue
        rows.append(_compact_case(case))
    structured = {
        "student_ref": student_ref,
        "student_name": student_name,
        "cases": rows[:limit],
        "source_type": "synthetic_demo",
    }
    text = "\n".join(
        f"- {case['case_id']} {case['title']} · {case['status']} · 담당 {case.get('owner_name')}"
        for case in structured["cases"]
    ) or "학생 연결 케이스가 없습니다."
    return _text_result(text, structured)


def list_documents(arguments):
    case_id = (arguments.get("case_id") or "").strip()
    status = (arguments.get("status") or "").strip()
    owner_user_id = (arguments.get("owner_user_id") or "").strip()
    doc_type = (arguments.get("doc_type") or "").strip()
    limit = int(arguments.get("limit") or 12)
    rows = []
    for doc in store.load_jsonl("documents.jsonl"):
        if case_id and doc.get("case_id") != case_id:
            continue
        if status and doc.get("status") != status:
            continue
        if owner_user_id and doc.get("owner_user_id") != owner_user_id:
            continue
        if doc_type and doc_type not in str(doc.get("doc_type", "")):
            continue
        rows.append(_compact_document(doc))
    structured = {
        "case_id": case_id,
        "status": status,
        "owner_user_id": owner_user_id,
        "doc_type": doc_type,
        "documents": rows[:limit],
        "source_type": "synthetic_demo",
    }
    text = "\n".join(
        f"- {doc['document_id']} {doc.get('title')} · {doc.get('status')} · {doc.get('case_id')}"
        for doc in structured["documents"]
    ) or "조건에 맞는 문서가 없습니다."
    return _text_result(text, structured)


def get_rag_refs(arguments):
    case_id = arguments.get("case_id") or ""
    case = store.get_case(case_id)
    if not case:
        return _text_result("케이스를 찾지 못했습니다.", {"found": False, "case_id": case_id})
    refs = []
    for path in case.get("related_rag_paths") or []:
        doc = rag_store.get_doc(path)
        if doc:
            refs.append(
                {
                    "path": doc.get("path"),
                    "doc_id": doc.get("doc_id"),
                    "domain": doc.get("domain"),
                    "title": doc.get("title"),
                    "applies_to_case_types": doc.get("applies_to_case_types", []),
                    "source_type": doc.get("source_type", "synthetic_demo"),
                }
            )
        else:
            refs.append({"path": path, "missing": True})
    structured = {"found": True, "case_id": case_id, "case_type": case.get("case_type"), "refs": refs}
    text = "\n".join(f"- {ref.get('path')} {ref.get('title', '문서 없음')}" for ref in refs) or "연결된 RAG 근거가 없습니다."
    return _text_result(text, structured)


def search_rag(arguments):
    query = arguments.get("query") or ""
    domain = arguments.get("domain") or "all"
    mode = arguments.get("mode") or "hybrid"
    case_type = arguments.get("case_type") or ""
    limit = int(arguments.get("limit") or 5)
    results = rag_store.search_rag(query, domain=domain, limit=limit, mode=mode, case_type=case_type)
    structured = {
        "query": query,
        "domain": domain,
        "mode": mode,
        "case_type": case_type,
        "results": results,
        "source_type": "synthetic_demo",
    }
    text = "\n".join(
        f"- {row['path']} {row['title']} · {row['domain']} · {row.get('heading')} · {row.get('retrieval', 'n/a')}"
        for row in results
    ) or "검색된 RAG 문서가 없습니다."
    return _text_result(text, structured)


def rag_vector_stats(arguments):
    structured = rag_store.vector_stats()
    text = (
        f"RAG vector index\n"
        f"- backend: {structured.get('backend')}\n"
        f"- documents: {structured.get('documents')}\n"
        f"- chunks: {structured.get('chunks')}\n"
        f"- terms: {structured.get('terms')}"
    )
    return _text_result(text, structured)


def get_doc(arguments):
    path = arguments.get("path") or ""
    doc = rag_store.get_doc(path)
    if not doc:
        return _text_result("문서를 찾지 못했습니다.", {"found": False, "path": path})
    body = doc.get("body", "")
    preview = body if len(body) <= 3000 else body[:3000].rstrip() + "\n\n...문서가 길어 일부만 표시했습니다."
    structured = {
        "found": True,
        "path": doc.get("path"),
        "doc_id": doc.get("doc_id"),
        "domain": doc.get("domain"),
        "title": doc.get("title"),
        "applies_to_case_types": doc.get("applies_to_case_types", []),
        "body_preview": preview,
        "source_type": doc.get("source_type", "synthetic_demo"),
    }
    return _text_result(f"{doc.get('title')}\n{preview}", structured)


def list_docs(arguments):
    domain = arguments.get("domain") or "all"
    docs = rag_store.list_docs(domain)
    structured = {"domain": domain, "count": len(docs), "documents": docs, "source_type": "synthetic_demo"}
    text = "\n".join(f"- {doc['path']} {doc['title']} · {doc['domain']}" for doc in docs[:30]) or "문서가 없습니다."
    return _text_result(text, structured)


def get_case_detail(arguments):
    case_id = arguments.get("case_id") or ""
    case = store.get_case(case_id)
    if not case:
        return _text_result("케이스를 찾지 못했습니다.", {"found": False, "case_id": case_id})
    tasks = [row for row in store.load_jsonl("tasks.jsonl") if row.get("case_id") == case_id]
    approvals = [row for row in store.load_jsonl("approvals.jsonl") if row.get("case_id") == case_id]
    documents = [row for row in store.load_jsonl("documents.jsonl") if row.get("case_id") == case_id]
    structured = {
        "found": True,
        "case": _compact_case(case),
        "tasks": [
            _compact_row(row, ["task_id", "case_id", "title", "owner_user_id", "owner_name", "status", "priority", "due_at"])
            for row in tasks[:8]
        ],
        "approvals": [
            _compact_row(row, ["approval_id", "case_id", "type", "status", "approver_user_id", "approver_name", "due_at"])
            for row in approvals[:8]
        ],
        "documents": [
            _compact_row(row, ["document_id", "case_id", "doc_type", "title", "status", "rag_path", "pii_masked", "consent_required"])
            for row in documents[:8]
        ],
        "relationship_count": len(store.related_items(case_id)),
    }
    text = (
        f"{case['title']}\n"
        f"- 상태: {case['status']} / 우선순위: {case['priority']} / 리스크: {case.get('risk_level', 'n/a')}\n"
        f"- 담당: {case.get('owner_name')} / 승인: {case.get('approver_name')}\n"
        f"- 다음 액션: {case.get('next_action')}\n"
        f"- 누락 서류: {', '.join(case.get('missing_documents') or []) or '없음'}\n"
        f"- 대기 태스크: {len([t for t in tasks if t.get('status') != 'done'])}건"
    )
    return _text_result(text, structured)


def list_pending_tasks(arguments):
    owner_user_id = arguments.get("owner_user_id") or ""
    priority = arguments.get("priority") or "all"
    limit = int(arguments.get("limit") or 8)
    rows = []
    for task in store.load_jsonl("tasks.jsonl"):
        if task.get("status") == "done":
            continue
        if owner_user_id and task.get("owner_user_id") != owner_user_id:
            continue
        if priority != "all" and task.get("priority") != priority:
            continue
        rows.append(task)
    structured = {"tasks": rows[:limit]}
    text = "\n".join(f"- {t['task_id']} {t['title']} · {t['case_id']} · {t.get('due_at', 'no due')}" for t in structured["tasks"]) or "대기 태스크가 없습니다."
    return _text_result(text, structured)


def trace_slack_context(arguments):
    case_id = arguments.get("case_id") or ""
    case = store.get_case(case_id)
    if not case:
        return _text_result("케이스를 찾지 못했습니다.", {"found": False, "case_id": case_id})
    threads = [row for row in store.load_jsonl("slack_threads.jsonl") if row.get("thread_id") == case.get("related_thread_id")]
    thread = threads[0] if threads else {}
    structured = {
        "found": True,
        "case_id": case_id,
        "channel": case.get("related_channel_name"),
        "thread_id": case.get("related_thread_id"),
        "canvas_title": case.get("related_canvas_title"),
        "timeline": case.get("timeline", []),
        "messages": thread.get("messages", [])[:6],
    }
    text = (
        f"{case_id} Slack 맥락\n"
        f"- 채널: {structured['channel']}\n"
        f"- 스레드: {structured['thread_id']}\n"
        f"- 캔버스: {structured['canvas_title']}\n"
        + "\n"
        + "\n".join(f"- {item}" for item in structured["timeline"][:5])
        + "\n"
        + "\n".join(f"- {msg.get('name')}: {msg.get('text')}" for msg in structured["messages"][:4])
    )
    return _text_result(text, structured)


def create_task(arguments):
    case_id = arguments.get("case_id") or ""
    if not store.get_case(case_id):
        return _text_result("케이스를 찾지 못해 태스크를 생성하지 않았습니다.", {"created": False, "case_id": case_id})
    task = {
        "task_id": "task_" + uuid4().hex[:10],
        "case_id": case_id,
        "title": arguments.get("title") or "후속 조치",
        "owner_user_id": arguments.get("owner_user_id") or "unassigned",
        "status": "open",
        "priority": "normal",
        "due_at": arguments.get("due_at") or "",
        "created_at": store.now_text(),
        "source_type": "synthetic_demo",
    }
    store.append_jsonl("tasks.jsonl", task)
    return _text_result(f"태스크를 생성했습니다: {task['task_id']} {task['title']}", {"created": True, "task": task})


TOOLS = {
    "find_cases": find_cases,
    "get_case_detail": get_case_detail,
    "list_pending_tasks": list_pending_tasks,
    "trace_slack_context": trace_slack_context,
    "create_task": create_task,
    "list_approvals_due_today": list_approvals_due_today,
    "group_cases_by_owner": group_cases_by_owner,
    "get_student_cases": get_student_cases,
    "list_documents": list_documents,
    "get_rag_refs": get_rag_refs,
    "search_rag": search_rag,
    "rag_vector_stats": rag_vector_stats,
    "get_doc": get_doc,
    "list_docs": list_docs,
}


def handle_json_rpc(payload):
    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}
    if method == "initialize":
        return _success(request_id, {"protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO})
    if method == "tools/list":
        return _success(request_id, {"tools": tool_definitions()})
    if method == "tools/call":
        name = params.get("name")
        if name not in TOOLS:
            return _error(request_id, -32602, f"Unknown tool: {name}")
        try:
            return _success(request_id, TOOLS[name](params.get("arguments") or {}))
        except Exception as exc:
            return _error(request_id, -32000, f"{type(exc).__name__}: {exc}")
    if method in {"ping", "notifications/initialized"}:
        return _success(request_id, {})
    return _error(request_id, -32601, "Method not found")


def handle_json_rpc_text(text):
    return json.dumps(handle_json_rpc(json.loads(text)), ensure_ascii=False)
