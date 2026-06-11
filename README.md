# epub-parser

Stream text from EPUB files together with resolved font family and font size metadata.

This package walks EPUB spine documents in reading order and yields text spans as it encounters them. Font metadata is resolved from:

- CSS rules in `<style>` blocks (tag, class, and tag.class selectors)
- Inline `style` attributes
- Legacy `<font face="...">` and `<font size="...">` attributes

## Install

```bash
pip install git+https://github.com/OpenPecha/epub-parser.git
```

Local development:

```bash
cd epub-parser
pip install -e ".[dev]"
```

## Python API

```python
from pathlib import Path

from epub_font_parser import EpubFontParser, stream_epub_text

for span in stream_epub_text(Path("book.epub")):
    print(span.text, span.font_family, span.font_size)

parser = EpubFontParser("book.epub")
for span in parser.stream():
    print(span.as_dict())
```

Each yielded `TextSpan` contains:

- `text`
- `font_family`
- `font_size`
- `document_href`
- `element`

## CLI

```bash
epub-parser book.epub
epub-parser book.epub --format jsonl
python -m epub_font_parser book.epub
```

## Notes

- Output is streamed document-by-document; nothing is buffered into one giant string.
- Font sizes are returned as written in the EPUB/CSS (for example `12pt`, `14px`, `1.2em`).
- Complex CSS selectors (`#id`, descendant selectors, `@font-face`) are not fully supported yet.
