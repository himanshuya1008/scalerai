import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run redaction and generate evaluation report.")
    parser.add_argument(
        "--input",
        default="input/sample.docx",
        help="Path to input DOCX file.",
    )
    parser.add_argument(
        "--output",
        default="output/redacted.docx",
        help="Path to write redacted DOCX file.",
    )
    parser.add_argument(
        "--ground_truth",
        default="tests/ground_truth.json",
        help="Path to ground-truth JSON used for report generation.",
    )
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "src/main.py",
        "--input",
        args.input,
        "--output",
        args.output,
        "--ground_truth",
        args.ground_truth,
    ]

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
