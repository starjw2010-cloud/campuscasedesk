from __future__ import annotations

import sys

sys.path.insert(0, "scripts")
import store  # noqa: E402


def main():
    cases = {row["case_id"]: row for row in store.load_jsonl("cases.jsonl")}
    assert cases, "cases.jsonl is empty"
    errors = []
    for name in ["tasks.jsonl", "approvals.jsonl", "documents.jsonl"]:
        for row in store.load_jsonl(name):
            if row.get("case_id") not in cases:
                errors.append(f"{name}: unknown case_id {row.get('case_id')}")
    for row in store.load_jsonl("relationships.jsonl"):
        if row.get("relation", "").startswith("case_to") and row.get("from_id") not in cases:
            errors.append(f"relationships.jsonl: unknown from_id {row.get('from_id')}")
    if errors:
        raise SystemExit("\n".join(errors))
    print({"ok": True, "cases": len(cases)})


if __name__ == "__main__":
    main()
