"""Run the QC eval cases.  Usage: backend\\.venv\\Scripts\\python.exe evals\\run_qc_evals.py

Calls the real LLM reviewer (uses MODEL and ANTHROPIC_API_KEY from .env.local).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.qc import run_qc  # noqa: E402
from qc_cases import CASES, NOW  # noqa: E402


def main() -> int:
    failures = 0
    for case in CASES:
        result = run_qc(case["question"], case["draft"], case["draft"] + case["final_suffix"],
                        case["quotes"], case["chunks"], NOW)
        ok = result["verdict"] == case["expect"] and (
            case["expect_issue"] is None or any(i.startswith(case["expect_issue"]) for i in result["issues"])
        )
        failures += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {case['name']}: verdict={result['verdict']} (expected {case['expect']})")
        for issue in result["issues"]:
            print(f"         - {issue}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} eval cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
