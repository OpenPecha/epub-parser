from __future__ import annotations

import argparse
import json
from pathlib import Path

from epub_font_parser.parser import EpubFontParser


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Stream text from an EPUB with font family and font size metadata.",
    )
    parser.add_argument("epub", type=Path, help="Path to the EPUB file")
    parser.add_argument(
        "--format",
        choices=("text", "jsonl"),
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)

    for span in EpubFontParser(args.epub).stream():
        if args.format == "jsonl":
            print(json.dumps(span.as_dict(), ensure_ascii=False))
            continue

        family = span.font_family or "-"
        size = span.font_size or "-"
        text = span.text.replace("\n", "\\n")
        print(f"[{family} | {size}] {text}")

    return 0
