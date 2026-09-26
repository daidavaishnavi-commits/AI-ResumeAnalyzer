"""Run the extraction pipeline on a PDF without starting the web app.

python scripts/analyze_cli.py resume.pdf --lines 40
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core import extraction  # noqa: E402
from app.core.errors import ResumeIQError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text from a resume PDF.")
    parser.add_argument("pdf", help="path to the PDF file")
    parser.add_argument("--lines", type=int, default=30, help="how many lines to print")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    parser.add_argument(
        "--strict", action="store_true", help="fail instead of flagging scanned/empty PDFs"
    )
    args = parser.parse_args()

    try:
        result = extraction.extract_text(args.pdf, strict=args.strict)
    except ResumeIQError as error:
        print(f"error: {error.user_message}", file=sys.stderr)
        if error.technical_detail:
            print(f"detail: {error.technical_detail}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0

    print(f"file      : {args.pdf}")
    print(f"extractor : {result.method}")
    print(f"pages     : {result.page_count}")
    print(f"lines     : {result.line_count}")
    print(f"words     : {result.word_count}")
    print(f"characters: {result.char_count}")
    print(f"scanned?  : {result.is_probably_scanned}")
    for warning in result.warnings:
        print(f"warning   : {warning}")

    print("\npage  line  text")
    print("-" * 60)
    for line in result.lines[: args.lines]:
        print(f"{line.page:>4}  {line.index:>4}  {line.text}")
    if result.line_count > args.lines:
        print(f"... {result.line_count - args.lines} more lines")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
