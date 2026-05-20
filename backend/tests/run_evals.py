"""
run_evals.py — Eval runner for the clinic chatbot guardrails.

Usage:
    # Fast unit tests only (no API calls, run always):
    python run_evals.py

    # All tests including LLM integration (run before deploy):
    python run_evals.py --full

    # Specific file only:
    python run_evals.py --file test_input_guard
"""

import subprocess
import sys
import argparse
import time


def print_header(text: str):
    width = 60
    print("\n" + "═" * width)
    print(f"  {text}")
    print("═" * width)


def run(args: list[str]) -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest"] + args,
        cwd="."
    )
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run guardrail evals")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include slow LLM integration tests (uses Groq API)"
    )
    parser.add_argument(
        "--file",
        type=str,
        help="Run a specific test file (e.g. test_input_guard)"
    )
    opts = parser.parse_args()

    start = time.time()

    if opts.file:
        print_header(f"Running: tests/{opts.file}.py")
        code = run([f"tests/{opts.file}.py", "-v"])

    elif opts.full:
        print_header("FULL EVAL SUITE (Unit + Integration)")
        print("  ⚠️  This makes real Groq API calls. Takes ~2-3 minutes.")
        print("  Run this before every production deploy.\n")
        code = run(["tests/", "-v", "-m", ""])  # empty -m = run all markers

    else:
        print_header("FAST UNIT TESTS (No API calls)")
        print("  Runs: InputGuard + OutputGuard + Utility functions")
        print("  Skips: LLM integration tests (use --full to include)\n")
        code = run(["tests/", "-v"])

    elapsed = round(time.time() - start, 1)
    print_header(f"Done in {elapsed}s — {'✅ All passed' if code == 0 else '❌ Failures found'}")

    if code != 0:
        print("\n  Fix failing tests before deploying to production.\n")

    sys.exit(code)


if __name__ == "__main__":
    main()