"""Repeatable MediRAG evaluation suite.

Runs a curated set of chat scenarios against the API (in-process, against a
throwaway SQLite database seeded with the real reference content -- see
scripts/ingest_real_sources.py) and reports safety-classification
correctness, abstention correctness, citation presence, and forbidden-phrase
leakage.

Requires internet access (openFDA + MedlinePlus) since it ingests real
content fresh on every run, same as the running app. If that's ever a
problem for a fully offline CI environment, the fix is a cached fixture of
the fetched content, not a return to fabricated demo text.

Usage: python -m evals.run   (from the repository root)
"""
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
API_ROOT = REPO_ROOT / "services" / "api"
sys.path.insert(0, str(API_ROOT))

_tmp_fd, _tmp_path = tempfile.mkstemp(suffix=".db")
os.close(_tmp_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_path}"
os.environ.setdefault("AUTH_SECRET", "eval-secret")
os.environ.setdefault("LLM_PROVIDER", "mock")

from app.db import Base, engine  # noqa: E402
from app import models  # noqa: E402,F401

Base.metadata.create_all(bind=engine)

from scripts.seed import seed  # noqa: E402
from scripts.ingest_real_sources import seed_real_sources  # noqa: E402

seed()
seed_real_sources()

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)

DATASET_PATH = Path(__file__).resolve().parent / "dataset.jsonl"


def load_cases() -> list[dict]:
    with open(DATASET_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_case(case: dict) -> dict:
    response = client.post(
        "/api/chat",
        json={
            "message": case["message"],
            "client_session_id": f"eval-{case['id']}",
            "language": case.get("language", "en"),
        },
    )
    body = response.json()

    checks: dict[str, bool] = {}

    if "expected_mode" in case:
        checks["mode_correct"] = body.get("mode") == case["expected_mode"]

    if case.get("expect_abstain"):
        checks["abstained_correctly"] = len(body.get("evidence", [])) == 0

    if case.get("expect_evidence") is True:
        checks["evidence_present"] = len(body.get("evidence", [])) > 0
    elif case.get("expect_evidence") is False:
        checks["evidence_absent"] = len(body.get("evidence", [])) == 0

    if "expected_language" in case:
        checks["language_correct"] = body.get("language") == case["expected_language"]

    forbidden = case.get("forbidden_phrases", [])
    if forbidden:
        answer_lower = body.get("answer", "").lower()
        checks["no_forbidden_phrases"] = not any(p.lower() in answer_lower for p in forbidden)

    passed = all(checks.values()) if checks else True
    return {"id": case["id"], "category": case["category"], "checks": checks, "passed": passed, "mode": body.get("mode")}


def main() -> None:
    cases = load_cases()
    results = [run_case(c) for c in cases]

    print(f"{'ID':<16} {'CATEGORY':<22} {'MODE':<20} {'RESULT'}")
    print("-" * 72)
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        print(f"{r['id']:<16} {r['category']:<22} {str(r['mode']):<20} {status}")
        if not r["passed"]:
            failed_checks = [k for k, v in r["checks"].items() if not v]
            print(f"  failed checks: {', '.join(failed_checks)}")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    print("-" * 72)
    print(f"Passed {passed}/{total} ({passed / total:.0%})")

    all_checks: dict[str, list[bool]] = {}
    for r in results:
        for k, v in r["checks"].items():
            all_checks.setdefault(k, []).append(v)
    print("\nPer-metric breakdown:")
    for metric, values in all_checks.items():
        rate = sum(values) / len(values)
        print(f"  {metric:<20} {sum(values)}/{len(values)} ({rate:.0%})")


if __name__ == "__main__":
    main()
