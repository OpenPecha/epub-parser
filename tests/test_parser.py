from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from epub_font_parser import EpubFontParser, stream_epub_text


def _build_sample_epub(path: Path) -> None:
    chapter = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <link rel="stylesheet" type="text/css" href="styles/main.css" />
  </head>
  <body>
    <p class="title">བོད་ཡིག</p>
    <p style="font-family: Himalaya; font-size: 14pt;">second line</p>
  </body>
</html>
"""
    css = (
        'body { font-family: "Times New Roman"; font-size: 12pt; }\n'
        ".title { font-family: Dedris-a; font-size: 18pt; }\n"
    )
    container = """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""
    opf = """<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">sample-epub</dc:identifier>
    <dc:title>Sample</dc:title>
    <dc:language>bo</dc:language>
  </metadata>
  <manifest>
    <item id="chapter" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="css" href="styles/main.css" media-type="text/css"/>
  </manifest>
  <spine>
    <itemref idref="chapter"/>
  </spine>
</package>
"""

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        archive.writestr("META-INF/container.xml", container)
        archive.writestr("OEBPS/content.opf", opf)
        archive.writestr("OEBPS/chapter1.xhtml", chapter)
        archive.writestr("OEBPS/styles/main.css", css)


def test_stream_epub_text_extracts_font_metadata(tmp_path: Path) -> None:
    epub_path = tmp_path / "sample.epub"
    _build_sample_epub(epub_path)

    spans = list(stream_epub_text(epub_path))
    texts = [span.text for span in spans if span.text.strip()]

    assert any("བོད་ཡིག" in span.text for span in spans)

    title_span = next(span for span in spans if "བོད་ཡིག" in span.text)
    assert title_span.font_family == "Dedris-a"
    assert title_span.font_size == "18pt"

    second_span = next(span for span in spans if "second line" in span.text)
    assert second_span.font_family == "Himalaya"
    assert second_span.font_size == "14pt"

    assert texts


def test_parser_iterates_like_stream(tmp_path: Path) -> None:
    epub_path = tmp_path / "sample.epub"
    _build_sample_epub(epub_path)

    parser = EpubFontParser(epub_path)
    assert list(parser) == list(parser.stream())


if __name__ == "__main__":
    pytest.main([__file__])
