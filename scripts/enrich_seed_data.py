#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SRC = "synthetic_demo"
NOW = datetime(2026, 7, 1, 9, 0, 0)
random.seed(20260702)

DOMAIN_CODE = {
    "practicum": "prac",
    "scholarship": "sch",
    "academic": "acad",
    "complaint": "civil",
    "international": "intl",
    "student_success": "succ",
}

DOMAIN_KO = {
    "practicum": "현장실습",
    "scholarship": "장학",
    "academic": "학사",
    "complaint": "민원",
    "international": "유학생",
    "student_success": "학생성공",
}

STATUS_WEIGHTS = [
    "received",
    "in_review",
    "evidence_requested",
    "approval_pending",
    "approval_pending",
    "in_progress",
    "in_progress",
    "on_hold",
    "completed",
    "rejected",
]

PRIORITY_WEIGHTS = ["urgent", "high", "high", "normal", "normal", "normal", "low"]
RISK_BY_PRIORITY = {"urgent": "high", "high": "medium", "normal": "medium", "low": "low"}
KOREAN_SUR = list("김이박최정강조윤장임한오서신권황안송류전문배노구")
KOREAN_GIVEN = [
    "하린",
    "민재",
    "서윤",
    "지안",
    "도현",
    "예서",
    "시현",
    "준서",
    "주하",
    "지율",
    "수연",
    "채아",
    "다현",
    "서우",
    "지후",
    "유나",
    "현서",
    "승민",
    "예원",
    "나은",
    "가온",
    "태윤",
    "소민",
    "건희",
    "하람",
    "지민",
    "수아",
    "연재",
    "민서",
    "준영",
]
INTL_NAMES = [
    ("Linh Tran", "베트남"),
    ("Mina Chen", "중국"),
    ("Sara Ahmed", "이집트"),
    ("Yuki Mori", "일본"),
    ("Wei Zhang", "중국"),
    ("Duc Nguyen", "베트남"),
    ("Elena Rossi", "이탈리아"),
    ("Grace Kim", "미국"),
    ("Min Li", "중국"),
    ("Amir Khan", "파키스탄"),
    ("Anna Ivanova", "러시아"),
    ("An Pham", "베트남"),
    ("Mei Lin", "중국"),
    ("Ren Sato", "일본"),
    ("Lucia Garcia", "스페인"),
    ("Arjun Patel", "인도"),
]


def iso(dt: datetime):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def read_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def write_json(name, value):
    (DATA / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def read_jsonl(name):
    return [json.loads(line) for line in (DATA / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(name, rows):
    with (DATA / name).open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def max_numeric(rows, key, pattern):
    rx = re.compile(pattern)
    nums = []
    for row in rows:
        match = rx.match(row[key])
        if match:
            nums.append(int(match.group(1)))
    return max(nums or [0])


def next_rel_id(state):
    state["rel"] += 1
    return f"rel_{state['rel']:04d}"


def add_rel(rels, state, relation, from_type, from_id, to_type, to_id):
    rels.append(
        {
            "rel_id": next_rel_id(state),
            "relation": relation,
            "from_type": from_type,
            "from_id": from_id,
            "to_type": to_type,
            "to_id": to_id,
            "source_type": SRC,
        }
    )


def ensure_students(students, target=520):
    existing_refs = {row["student_ref"] for row in students}
    existing_names = {row["name"] for row in students}
    max_idx = 0
    for row in students:
        match = re.match(r"stu_2026_(\d+)", row["student_ref"])
        if match:
            max_idx = max(max_idx, int(match.group(1)))
    departments = ["경영학과", "회계세무학과", "재무금융학과", "경영정보학과", "국제통상학과", "AI비즈니스학과"]
    while len(students) < target:
        max_idx += 1
        ref = f"stu_2026_{max_idx:04d}"
        if ref in existing_refs:
            continue
        if len(students) % 9 == 0:
            base_name, nationality = random.choice(INTL_NAMES)
            name = f"{base_name} {max_idx}"
            masked = base_name.split()[0] + " *"
        else:
            name = random.choice(KOREAN_SUR) + random.choice(KOREAN_GIVEN)
            while name in existing_names:
                name = random.choice(KOREAN_SUR) + random.choice(KOREAN_GIVEN) + str(max_idx % 10)
            nationality = "대한민국"
            masked = name[0] + "*" + name[-1]
        existing_refs.add(ref)
        existing_names.add(name)
        students.append(
            {
                "student_ref": ref,
                "name": name,
                "masked_name": masked,
                "student_no_masked": "2026-****",
                "department": random.choice(departments),
                "year": random.choice([1, 2, 3, 4]),
                "nationality": nationality,
                "source_type": SRC,
            }
        )


def build_canvas(canvases, rels, state, domain, channel_id, channel_name, case_ids, ordinal):
    canvas_id = f"can_{DOMAIN_CODE[domain]}_ops_{ordinal:03d}"
    title = f"{DOMAIN_KO[domain]} 월간 운영 리스크 보드 {ordinal:03d}"
    linked = case_ids[:10]
    canvases.append(
        {
            "canvas_id": canvas_id,
            "channel_id": channel_id,
            "channel_name": channel_name,
            "domain": domain,
            "title": title,
            "markdown": (
                f"# {title}\n\n"
                f"> {DOMAIN_KO[domain]} 케이스 운영 현황과 병목을 모니터링하는 synthetic_demo 캔버스입니다.\n\n"
                "## 점검 항목\n"
                "- [ ] 지연 케이스 확인\n"
                "- [ ] 누락 서류 회수\n"
                "- [ ] 승인 마감 점검\n"
                "- [ ] 고위험 케이스 관리자 보고\n\n"
                "## 연결 케이스\n"
                + "\n".join(f"- {case_id}" for case_id in linked)
            ),
            "related_case_ids": linked,
            "source_type": SRC,
        }
    )
    for case_id in linked:
        add_rel(rels, state, "canvas_to_case", "canvas", canvas_id, "case", case_id)
    return canvas_id, title


def create_thread(threads, rels, state, case, thread_idx, user_names):
    thread_id = f"thr_{DOMAIN_CODE[case['domain']]}_{thread_idx:04d}"
    created = datetime.fromisoformat(case["created_at"]) + timedelta(hours=random.randint(1, 12))
    participants = list({case["owner_user_id"], case["approver_user_id"], "u_dean"})
    snippets = [
        f"{case['title']} 건 접수 후 현재 {case['status']} 상태입니다.",
        f"누락 서류 {len(case.get('missing_documents') or [])}건 확인했습니다.",
        f"근거 문서는 {case['related_rag_paths'][0]} 기준으로 검토하겠습니다.",
        "담당자 확인 후 다음 액션 업데이트하겠습니다.",
        "마감 임박 여부와 승인 라인 같이 확인 필요합니다.",
    ]
    messages = []
    for i in range(random.randint(4, 7)):
        user_id = participants[i % len(participants)]
        messages.append(
            {
                "user_id": user_id,
                "name": user_names.get(user_id, user_id),
                "ts": iso(created + timedelta(hours=i * 2)),
                "text": snippets[i % len(snippets)],
            }
        )
    threads.append(
        {
            "thread_id": thread_id,
            "channel_id": case["related_channel_id"],
            "channel_name": case["related_channel_name"],
            "case_id": case["case_id"],
            "title": case["title"],
            "participants": participants,
            "message_count": len(messages),
            "messages": messages,
            "created_at": iso(created),
            "source_type": SRC,
        }
    )
    add_rel(rels, state, "thread_to_case", "thread", thread_id, "case", case["case_id"])
    add_rel(rels, state, "case_to_thread", "case", case["case_id"], "thread", thread_id)
    return thread_id


def enrich():
    users = read_json("users.json")
    students = read_json("students.json")
    channels = read_json("channels.json")
    canvases = read_json("canvases.json")
    cases = read_jsonl("cases.jsonl")
    tasks = read_jsonl("tasks.jsonl")
    approvals = read_jsonl("approvals.jsonl")
    documents = read_jsonl("documents.jsonl")
    rels = read_jsonl("relationships.jsonl")
    threads = read_jsonl("slack_threads.jsonl")

    ensure_students(students, target=520)

    user_names = {row["user_id"]: row["name"] for row in users}
    users_by_domain = defaultdict(list)
    managers_by_domain = {}
    for user in users:
        for domain in user.get("domains", []):
            if domain == "all":
                continue
            users_by_domain[domain].append(user)
            if "팀장" in user.get("role", ""):
                managers_by_domain[domain] = user
    channels_by_domain = {row["domain"]: row for row in channels if row.get("domain") != "all"}
    students_by_kind = {
        "international": [row for row in students if row.get("nationality") != "대한민국"],
        "default": [row for row in students if row.get("nationality") == "대한민국"],
    }
    templates_by_domain = defaultdict(list)
    for case in cases:
        templates_by_domain[case["domain"]].append(case)

    state = {
        "rel": max_numeric(rels, "rel_id", r"rel_(\d+)"),
        "task": max_numeric(tasks, "task_id", r"task_[a-z]+_(\d+)"),
        "approval": max_numeric(approvals, "approval_id", r"apr_(\d+)"),
        "document": max_numeric(documents, "document_id", r"doc_(\d+)"),
        "thread": max_numeric(threads, "thread_id", r"thr_[a-z]+_(\d+)"),
    }
    case_idx_by_domain = {}
    for domain, code in DOMAIN_CODE.items():
        case_idx_by_domain[domain] = max_numeric(
            [row for row in cases if row["domain"] == domain], "case_id", rf"case_{code}_(\d+)"
        )

    new_case_ids_by_domain = defaultdict(list)
    target_per_domain = 60
    for domain in DOMAIN_CODE:
        templates = templates_by_domain[domain]
        channel = channels_by_domain[domain]
        domain_users = users_by_domain[domain]
        manager = managers_by_domain[domain]
        while sum(1 for row in cases if row["domain"] == domain) < target_per_domain:
            template = random.choice(templates)
            case_idx_by_domain[domain] += 1
            case_id = f"case_{DOMAIN_CODE[domain]}_{case_idx_by_domain[domain]:03d}"
            student_pool = students_by_kind["international"] if domain == "international" else students_by_kind["default"]
            student = random.choice(student_pool)
            owner = random.choice([user for user in domain_users if "담당자" in user.get("role", "")] or domain_users)
            status = random.choice(STATUS_WEIGHTS)
            priority = random.choice(PRIORITY_WEIGHTS)
            risk = "high" if priority == "urgent" or random.random() < 0.12 else RISK_BY_PRIORITY[priority]
            required = list(template.get("required_documents") or [])
            submitted_count = random.randint(0, len(required))
            submitted = required[:submitted_count]
            missing = required[submitted_count:]
            if status == "completed":
                submitted, missing = required, []
            if status in {"received", "evidence_requested"} and not missing and required:
                missing = [required[-1]]
                submitted = required[:-1]
            created = NOW - timedelta(days=random.randint(1, 180), hours=random.randint(0, 18))
            updated = min(NOW - timedelta(hours=random.randint(1, 48)), created + timedelta(days=random.randint(1, 30)))
            consent = False if domain == "complaint" and random.random() < 0.32 else True
            next_actions = [
                {
                    "action": f"{missing[0] if missing else required[0] if required else '필수 자료'} 확인 및 회신 요청",
                    "owner_user_id": owner["user_id"],
                    "due_at": iso(NOW + timedelta(days=random.choice([0, 1, 2, 3, 5, 7]))),
                    "status": "done" if status == "completed" else "open",
                },
                {
                    "action": "담당자 검토 후 승인 라인 상신",
                    "owner_user_id": owner["user_id"],
                    "due_at": iso(NOW + timedelta(days=random.choice([1, 2, 3, 5, 7, 10]))),
                    "status": "done" if status == "completed" else "open",
                },
            ]
            case = {
                "case_id": case_id,
                "title": f"{student['name']} {template['title'].split(' ', 1)[-1]}",
                "domain": domain,
                "case_type": template["case_type"],
                "status": status,
                "priority": priority,
                "student_ref": student["student_ref"],
                "student_name": student["name"],
                "owner_user_id": owner["user_id"],
                "owner_name": owner["name"],
                "approver_user_id": manager["user_id"],
                "approver_name": manager["name"],
                "related_channel_id": channel["channel_id"],
                "related_channel_name": channel["name"],
                "related_thread_id": None,
                "related_canvas_id": None,
                "related_canvas_title": None,
                "related_rag_paths": list(template["related_rag_paths"]),
                "required_documents": required,
                "submitted_documents": submitted,
                "missing_documents": missing,
                "next_actions": next_actions,
                "next_action": next_actions[0]["action"],
                "summary": (
                    f"{student['masked_name']} 학생 {DOMAIN_KO[domain]} {template['case_type']} 운영 케이스. "
                    f"현재 {status}, 미제출 서류 {len(missing)}건."
                ),
                "timeline": [
                    f"{student['masked_name']} 관련 케이스 접수",
                    f"{channel['name']}에서 담당자 검토",
                    f"필요 서류 {len(required)}건 중 {len(submitted)}건 확인",
                    "승인 또는 보완 요청 흐름 점검",
                ],
                "consent_on_file": consent,
                "risk_level": risk,
                "created_at": iso(created),
                "updated_at": iso(updated),
                "source_type": SRC,
            }
            state["thread"] += 1
            case["related_thread_id"] = create_thread(threads, rels, state, case, state["thread"], user_names)
            if random.random() < 0.75:
                state["thread"] += 1
                create_thread(threads, rels, state, case, state["thread"], user_names)

            add_rel(rels, state, "case_to_student", "case", case_id, "student", student["student_ref"])
            add_rel(rels, state, "case_to_owner", "case", case_id, "user", owner["user_id"])
            add_rel(rels, state, "case_to_approver", "case", case_id, "user", manager["user_id"])
            add_rel(rels, state, "case_to_channel", "case", case_id, "channel", channel["channel_id"])
            for rag_path in case["related_rag_paths"]:
                add_rel(rels, state, "case_to_rag_path", "case", case_id, "rag_path", rag_path)

            for doc_type in required:
                state["document"] += 1
                document_id = f"doc_{state['document']:04d}"
                doc_status = "제출완료" if doc_type in submitted else random.choice(["미제출", "미제출", "검토중"])
                documents.append(
                    {
                        "document_id": document_id,
                        "case_id": case_id,
                        "doc_type": doc_type,
                        "title": f"{student['masked_name']} {doc_type}",
                        "status": doc_status,
                        "student_ref": student["student_ref"],
                        "owner_user_id": owner["user_id"],
                        "rag_path": case["related_rag_paths"][0],
                        "file_ref": f"vault://{DOMAIN_CODE[domain]}/{case_id}/{document_id}.pdf",
                        "pii_masked": True,
                        "consent_required": doc_type == "개인정보동의서",
                        "created_at": iso(created + timedelta(days=1)),
                        "source_type": SRC,
                    }
                )
                add_rel(rels, state, "document_to_case", "document", document_id, "case", case_id)
                add_rel(rels, state, "case_to_document", "case", case_id, "document", document_id)

            for i, action in enumerate(next_actions + random.sample(next_actions, k=1)):
                state["task"] += 1
                task_id = f"task_{DOMAIN_CODE[domain]}_{state['task']:04d}"
                tasks.append(
                    {
                        "task_id": task_id,
                        "case_id": case_id,
                        "title": action["action"],
                        "owner_user_id": owner["user_id"],
                        "owner_name": owner["name"],
                        "status": "done" if status == "completed" and i == 0 else random.choice(["open", "open", "in_progress"]),
                        "priority": priority,
                        "due_at": action["due_at"],
                        "created_at": iso(created + timedelta(days=1, hours=i)),
                        "source_type": SRC,
                    }
                )
                add_rel(rels, state, "task_to_case", "task", task_id, "case", case_id)

            if status in {"approval_pending", "in_progress", "completed", "rejected"} or random.random() < 0.45:
                state["approval"] += 1
                approval_id = f"apr_{state['approval']:04d}"
                approval_status = {
                    "approval_pending": "pending",
                    "in_progress": "approved",
                    "completed": "approved",
                    "rejected": "rejected",
                }.get(status, "pending")
                due = NOW + timedelta(days=random.choice([0, 0, 1, 2, 3, 5]))
                approvals.append(
                    {
                        "approval_id": approval_id,
                        "case_id": case_id,
                        "type": f"{case['case_type']}_approval",
                        "requester_user_id": owner["user_id"],
                        "requester_name": owner["name"],
                        "approver_user_id": manager["user_id"],
                        "approver_name": manager["name"],
                        "status": approval_status,
                        "requested_at": iso(created + timedelta(days=2)),
                        "decided_at": None if approval_status == "pending" else iso(created + timedelta(days=4)),
                        "due_at": iso(due.replace(hour=18, minute=0, second=0)),
                        "comment": "" if approval_status == "pending" else "synthetic_demo 승인/반려 이력",
                        "source_type": SRC,
                    }
                )
                add_rel(rels, state, "approval_to_case", "approval", approval_id, "case", case_id)
                add_rel(rels, state, "case_to_approver", "case", case_id, "approval", approval_id)

            cases.append(case)
            new_case_ids_by_domain[domain].append(case_id)

    # Add richer operational canvases and attach new cases to them.
    for domain, case_ids in new_case_ids_by_domain.items():
        channel = channels_by_domain[domain]
        for ordinal, start in enumerate(range(0, len(case_ids), 10), start=1):
            canvas_id, title = build_canvas(
                canvases,
                rels,
                state,
                domain,
                channel["channel_id"],
                channel["name"],
                case_ids[start : start + 10],
                ordinal,
            )
            for case in cases:
                if case["case_id"] in case_ids[start : start + 10]:
                    case["related_canvas_id"] = canvas_id
                    case["related_canvas_title"] = title
                    add_rel(rels, state, "case_to_canvas", "case", case["case_id"], "canvas", canvas_id)

    # Backfill any new case without canvas, though the chunking above should cover all.
    canvases_by_domain = defaultdict(list)
    for canvas in canvases:
        canvases_by_domain[canvas["domain"]].append(canvas)
    for case in cases:
        if case.get("related_canvas_id"):
            continue
        canvas = random.choice(canvases_by_domain[case["domain"]])
        case["related_canvas_id"] = canvas["canvas_id"]
        case["related_canvas_title"] = canvas["title"]
        add_rel(rels, state, "case_to_canvas", "case", case["case_id"], "canvas", canvas["canvas_id"])

    workspace_map = read_json("workspace_map.json")
    counts = {
        "users": len(users),
        "channels": len(channels),
        "students": len(students),
        "cases": len(cases),
        "threads": len(threads),
        "canvases": len(canvases),
        "tasks": len(tasks),
        "approvals": len(approvals),
        "documents": len(documents),
        "relationships": len(rels),
    }
    workspace_map["counts"] = counts
    workspace_map["enriched_at"] = iso(NOW)
    workspace_map["enrichment"] = {
        "target_cases_per_domain": target_per_domain,
        "method": "deterministic append-only enrichment",
        "source_type": SRC,
    }
    workspace_map["domains"] = [
        {
            "id": domain,
            "ko_label": DOMAIN_KO[domain],
            "channel_id": channels_by_domain[domain]["channel_id"],
            "case_count": Counter(row["domain"] for row in cases)[domain],
        }
        for domain in DOMAIN_CODE
    ]

    write_json("students.json", students)
    write_json("canvases.json", canvases)
    write_json("workspace_map.json", workspace_map)
    write_jsonl("cases.jsonl", cases)
    write_jsonl("tasks.jsonl", tasks)
    write_jsonl("approvals.jsonl", approvals)
    write_jsonl("documents.jsonl", documents)
    write_jsonl("relationships.jsonl", rels)
    write_jsonl("slack_threads.jsonl", threads)
    return counts


def main():
    counts = enrich()
    print(json.dumps({"ok": True, "counts": counts}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
