import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run DOCX PII redaction pipeline.")
    parser.add_argument(
        "--input",
        default="input/Red Herring Prospectus.docx",
        help="Path to input DOCX file.",
    )
    parser.add_argument(
        "--output",
        default="output/redacted.docx",
        help="Path to write redacted DOCX file.",
    )
    parser.add_argument(
        "--ground_truth",
        default="",
        help="Optional ground-truth JSON for evaluation.",
    )
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "src/main.py",
        "--input",
        args.input,
        "--output",
        args.output,
    ]
    if args.ground_truth:
        cmd.extend(["--ground_truth", args.ground_truth])

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
