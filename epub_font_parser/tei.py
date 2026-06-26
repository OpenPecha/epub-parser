from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path

from epub_font_parser.models import TextSpan
from epub_font_parser.normalization import normalize_unicode
from epub_font_parser.parser import stream_epub_text

_DEFAULT_IE_ID = "IE_EPUB"


def parse_font_size_points(font_size: str | None) -> float:
  """Convert CSS font-size values to comparable point sizes."""
  if not font_size:
    return 12.0

  value = font_size.strip().lower()
  try:
    if value.endswith("pt"):
      return float(value[:-2])
    if value.endswith("px"):
      return float(value[:-2]) * 0.75
    if value.endswith("em"):
      return float(value[:-2]) * 12.0
    if value.endswith("%"):
      return float(value[:-1]) * 0.12
    return float(value)
  except ValueError:
    return 12.0


def escape_xml(text: str) -> str:
  text = text.replace("&", "&amp;")
  text = text.replace("<", "&lt;")
  text = text.replace(">", "&gt;")
  return text


def calculate_sha256(file_path: Path) -> str:
  sha256_hash = hashlib.sha256()
  with open(file_path, "rb") as f:
    for byte_block in iter(lambda: f.read(4096), b""):
      sha256_hash.update(byte_block)
  return sha256_hash.hexdigest()


def classify_font_sizes(spans: list[TextSpan]) -> dict[float, str]:
  """Classify font sizes into head, regular, and small categories."""
  size_counts: Counter[float] = Counter()

  for span in spans:
    font_size = parse_font_size_points(span.font_size)
    tibetan_chars = sum(1 for c in span.text if 0x0F00 <= ord(c) <= 0x0FFF)
    if tibetan_chars > 0:
      size_counts[font_size] += tibetan_chars

  if not size_counts:
    return {}

  most_common = max(size_counts.items(), key=lambda item: item[1])[0]
  classifications: dict[float, str] = {}

  for font_size in size_counts:
    if font_size == most_common:
      classifications[font_size] = "regular"
    elif font_size > most_common:
      classifications[font_size] = "head"
    else:
      classifications[font_size] = "small"

  return classifications


def build_tei_body(spans: list[TextSpan]) -> str:
  """Build TEI body content from parsed EPUB text spans."""
  classifications = classify_font_sizes(spans)
  tei_lines: list[str] = []
  current_markup: str | None = None

  for span in spans:
    normalized_text = normalize_unicode(span.text)
    if not normalized_text:
      continue

    escaped_text = escape_xml(normalized_text)
    font_size = parse_font_size_points(span.font_size)
    classification = classifications.get(font_size, "regular")

    if classification != current_markup:
      if current_markup == "small":
        tei_lines.append("</hi>")
      elif current_markup == "head":
        tei_lines.append("</hi>")

      if classification == "small":
        tei_lines.append('<hi rend="small">')
      elif classification == "head":
        tei_lines.append('<hi rend="head">')

      current_markup = classification if classification != "regular" else None

    tei_lines.append(escaped_text)

  if current_markup == "small":
    tei_lines.append("</hi>")
  elif current_markup == "head":
    tei_lines.append("</hi>")

  body_content = "".join(tei_lines)
  body_content = re.sub(r'<hi rend="[^"]+"></hi>', "", body_content)
  body_content = re.sub(r"\n\n+", "\n", body_content)
  body_content = body_content.replace("\n", "\n<lb/>")
  body_content = re.sub(r" *<lb/> *", "\n<lb/>", body_content)
  body_content = body_content.strip()
  body_content = re.sub(r"(<lb/>[\s\n]*)+</hi>", r"</hi>", body_content)
  body_content = re.sub(r"\n\s*(</hi>)", r"\1", body_content)
  body_content = re.sub(r'(<hi rend="[^"]+">)\n<lb/>', r"\n<lb/>\1", body_content)
  body_content = re.sub(r"\n<lb/>\s*\n", "\n", body_content)
  body_content = re.sub(r"(<lb/>)\s*(<lb/>)", r"\1", body_content)
  body_content = re.sub(r"\n<lb/>\s*$", "", body_content)

  if body_content.startswith("<lb/>"):
    body_content = "\n" + body_content

  return body_content


def generate_tei_xml(
  *,
  body_content: str,
  title: str,
  src_path: str,
  sha256: str,
  ie_id: str,
  ve_id: str,
  ut_id: str,
) -> str:
  """Generate a complete TEI XML document (IE11249-style)."""
  return f'''<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
<teiHeader>
<fileDesc>
<titleStmt>
<title>{escape_xml(title)}</title>
</titleStmt>
<publicationStmt>
<p>File from the archive of the Buddhist Digital Resource Center (BDRC), converted into TEI from a file not created by BDRC.</p>
</publicationStmt>
<sourceDesc>
<bibl>
<idno type="src_path">{escape_xml(src_path)}</idno>
<idno type="src_sha256">{sha256}</idno>
<idno type="bdrc_ie">http://purl.bdrc.io/resource/{ie_id}</idno>
<idno type="bdrc_ve">http://purl.bdrc.io/resource/{ve_id}</idno>
<idno type="bdrc_ut">http://purl.bdrc.io/resource/{ut_id}</idno>
</bibl>
</sourceDesc>
</fileDesc>
<encodingDesc>
<p>The TEI header does not contain any bibliographical data. It is instead accessible through the <ref target="http://purl.bdrc.io/resource/{ie_id}">record in the BDRC database</ref>.</p>
</encodingDesc>
</teiHeader>
<text>
<body xml:lang="bo">
<p>{body_content}</p>
</body>
</text>
</TEI>
'''


def epub_ids(epub_path: Path, ie_id: str = _DEFAULT_IE_ID) -> tuple[str, str, str]:
  """Derive placeholder BDRC-style IDs from an EPUB path."""
  ve_id = f"VE_{epub_path.parent.name}"
  ut_id = f"UT_{epub_path.stem}"
  return ie_id, ve_id, ut_id


def epub_to_tei_xml(
  epub_path: str | Path,
  *,
  ie_id: str = _DEFAULT_IE_ID,
  src_path: str | None = None,
) -> str:
  """Convert an EPUB file to TEI XML string."""
  epub_path = Path(epub_path)
  spans = list(stream_epub_text(epub_path))
  body_content = build_tei_body(spans)
  ie_id, ve_id, ut_id = epub_ids(epub_path, ie_id=ie_id)
  resolved_src_path = src_path or epub_path.name

  return generate_tei_xml(
    body_content=body_content,
    title=epub_path.stem,
    src_path=resolved_src_path,
    sha256=calculate_sha256(epub_path),
    ie_id=ie_id,
    ve_id=ve_id,
    ut_id=ut_id,
  )


def epub_to_xml_file(
  epub_path: str | Path,
  *,
  ie_id: str = _DEFAULT_IE_ID,
  src_path: str | None = None,
) -> Path:
  """Write TEI XML alongside an EPUB file (same directory, .xml extension)."""
  epub_path = Path(epub_path)
  xml_path = epub_path.with_suffix(".xml")
  xml_path.write_text(
    epub_to_tei_xml(epub_path, ie_id=ie_id, src_path=src_path),
    encoding="utf-8",
  )
  return xml_path
