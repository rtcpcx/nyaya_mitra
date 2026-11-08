"""Run repeatable NYAYA MITRA conversations without the Streamlit typing UI.

Usage (PowerShell, from the repository root):
    python scripts/run_conversation_tests.py --list
    python scripts/run_conversation_tests.py --case rental_deposit
    python scripts/run_conversation_tests.py --case rental_deposit cyber_fraud
    python scripts/run_conversation_tests.py

Each turn calls the same src.service.respond_to_turn() function as app.py.
The JSON files preserve the returned application output, including model_output,
retrieved sources, triage and timing metadata. These are observational runs,
not automatic legal-correctness scores.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import LLM_API_KEY, LLM_MODEL  # noqa: E402
from src.service import respond_to_turn, respond_without_llm  # noqa: E402


def load_suite(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("Suite must be a JSON object containing a 'cases' array.")
    return data


def run_case(case: dict[str, Any], use_llm: bool) -> dict[str, Any]:
    history: list[dict[str, Any]] = []
    turn_results: list[dict[str, Any]] = []
    location = str(case.get("location", ""))
    language = str(case.get("language", "English"))

    for index, prompt in enumerate(case.get("turns", []), start=1):
        prompt = str(prompt).strip()
        if not prompt:
            continue

        # Match app.py: append the current user message before calling the service.
        history.append({"role": "user", "content": prompt})
        try:
            if use_llm:
                result = respond_to_turn(prompt, history, location, language)
            else:
                result = respond_without_llm(prompt, history, location)

            assistant_content = result.get("reply", "")
            if result.get("next_question"):
                assistant_content += "\n\n" + result["next_question"]

            turn_results.append({
                "turn": index,
                "input": prompt,
                "output": result,
                "displayed_assistant_message": assistant_content,
                "error": None,
            })
            history.append({
                "role": "assistant",
                "content": assistant_content,
                "metadata": result,
            })
        except Exception as exc:  # Preserve failures as part of the test evidence.
            turn_results.append({
                "turn": index,
                "input": prompt,
                "output": None,
                "displayed_assistant_message": None,
                "error": f"{type(exc).__name__}: {exc}",
            })
            break

    return {
        "case_id": case.get("id", "unnamed"),
        "title": case.get("title", "Untitled test"),
        "purpose": case.get("purpose", ""),
        "location": location,
        "language": language,
        "model": LLM_MODEL if use_llm else None,
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "turn_count": len(turn_results),
        "turns": turn_results,
        "final_conversation_history": history,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite", type=Path,
        default=ROOT / "test_cases" / "submission_cases.json",
        help="Path to the JSON scenario suite.",
    )
    parser.add_argument("--case", nargs="+", help="Run only these case IDs.")
    parser.add_argument("--list", action="store_true", help="List available case IDs.")
    parser.add_argument("--limit", type=int, help="Run at most N cases.")
    parser.add_argument(
        "--output-dir", type=Path,
        default=ROOT / "raw_outputs" / "submission_runs",
        help="Directory for unedited JSON outputs (gitignored by default).",
    )
    parser.add_argument(
        "--no-llm", action="store_true",
        help="Run only deterministic intake/retrieval fallback; no model output.",
    )
    args = parser.parse_args()

    suite = load_suite(args.suite)
    cases = suite["cases"]

    if args.list:
        for case in cases:
            print(f'{case.get("id", "unnamed"):24} {case.get("title", "")}')
        return 0

    selected_ids = set(args.case or [])
    if selected_ids:
        cases = [case for case in cases if case.get("id") in selected_ids]
        missing = selected_ids - {case.get("id") for case in cases}
        if missing:
            parser.error("Unknown case ID(s): " + ", ".join(sorted(missing)))
    if args.limit is not None:
        cases = cases[: max(0, args.limit)]
    if not cases:
        parser.error("No test cases selected.")

    use_llm = not args.no_llm
    if use_llm and not LLM_API_KEY:
        parser.error(
            "LLM_API_KEY is not configured. Add it to your local .env file; "
            "never commit or share the key. Use --no-llm only for retrieval/triage checks."
        )

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_utc")
    run_dir = args.output_dir / run_stamp
    run_dir.mkdir(parents=True, exist_ok=True)

    summary: list[dict[str, Any]] = []
    print(f"Running {len(cases)} case(s) | mode={'LLM' if use_llm else 'no-LLM'}")
    print(f"Model: {LLM_MODEL if use_llm else 'not used'}")
    print(f"Output: {run_dir}")

    for case in cases:
        print(f"\n[{case.get('id')}] {case.get('title')}")
        result = run_case(case, use_llm)
        path = run_dir / f"{case.get('id', 'case')}.json"
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

        errors = [turn for turn in result["turns"] if turn["error"]]
        sources = [
            source
            for turn in result["turns"] if turn["output"]
            for source in turn["output"].get("retrieved_sources", [])
        ]
        summary_item = {
            "case_id": result["case_id"],
            "title": result["title"],
            "turns": result["turn_count"],
            "errors": len(errors),
            "output_file": path.name,
            "source_records_returned_across_turns": len(sources),
            "risk_levels": [
                turn["output"].get("risk_level")
                for turn in result["turns"] if turn["output"]
            ],
        }
        summary.append(summary_item)
        print(
            f"  turns={result['turn_count']} errors={len(errors)} "
            f"retrieved_source_records={len(sources)} file={path.name}"
        )
        if errors:
            print(f"  ERROR: {errors[0]['error']}")

    summary_path = run_dir / "run_summary.json"
    summary_path.write_text(
        json.dumps({
            "suite": str(args.suite),
            "run_at_utc": datetime.now(timezone.utc).isoformat(),
            "mode": "llm" if use_llm else "no_llm",
            "model": LLM_MODEL if use_llm else None,
            "cases": summary,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nFinished. Summary: {summary_path}")
    print("Review outputs manually; this runner does not certify legal correctness.")
    return 1 if any(item["errors"] for item in summary) else 0


if __name__ == "__main__":
    raise SystemExit(main())
