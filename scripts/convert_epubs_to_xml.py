from __future__ import annotations

import argparse
import sys
from pathlib import Path

from epub_font_parser.tei import epub_to_xml_file


def main(argv: list[str] | None = None) -> int:
  parser = argparse.ArgumentParser(
    description="Convert EPUB files to TEI XML (.xml) in the same directory.",
  )
  parser.add_argument(
    "directory",
    type=Path,
    help="Root directory to search recursively for .epub files",
  )
  parser.add_argument(
    "--ie-id",
    default="IE_EPUB",
    help="BDRC IE ID for TEI headers (default: IE_EPUB)",
  )
  args = parser.parse_args(argv)

  root = args.directory.resolve()
  if not root.is_dir():
    print(f"Error: not a directory: {root}", file=sys.stderr)
    return 1

  epub_files = sorted(root.rglob("*.epub"))
  if not epub_files:
    print(f"No EPUB files found under {root}", file=sys.stderr)
    return 1

  converted = 0
  failed = 0

  for i, epub_path in enumerate(epub_files, start=1):
    try:
      rel = epub_path.relative_to(root)
      xml_path = epub_to_xml_file(
        epub_path,
        ie_id=args.ie_id,
        src_path=str(rel).replace("\\", "/"),
      )
      converted += 1
      print(f"[{i}/{len(epub_files)}] {rel} -> {xml_path.name}")
    except Exception as exc:
      failed += 1
      print(
        f"[{i}/{len(epub_files)}] FAILED {epub_path.relative_to(root)}: {exc}",
        file=sys.stderr,
      )

  print(f"\nDone: {converted} converted, {failed} failed, {len(epub_files)} total")
  return 0 if failed == 0 else 1


if __name__ == "__main__":
  raise SystemExit(main())
