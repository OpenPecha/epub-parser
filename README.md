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

## TEI XML conversion

In addition to streaming spans, the package can convert an EPUB into a single
TEI XML document. Font sizes are classified by Tibetan-character frequency
(most common size = regular, larger = `<hi rend="head">`, smaller =
`<hi rend="small">`), and Tibetan text is normalized to NFC/NFD with
Tibetan-specific rules. The output structure follows the BDRC e-text format
used in [buda-base/tibetan-etext-tools](https://github.com/buda-base/tibetan-etext-tools/tree/main/IE11249).

```python
from epub_font_parser import epub_to_tei_xml, epub_to_xml_file

# Get the TEI XML as a string
xml = epub_to_tei_xml("book.epub")

# Or write it next to the EPUB as book.xml
epub_to_xml_file("book.epub")
```

## Batch conversion scripts

The `scripts/` directory contains helpers to convert a whole tree of EPUBs.
Each output file is written in the same directory as its source EPUB, with the
extension swapped.

Plain text (`.txt`):

```bash
python scripts/convert_epubs_to_txt.py path/to/epub/root
```

TEI XML (`.xml`):

```bash
python scripts/convert_epubs_to_xml.py path/to/epub/root --ie-id IE_EPUB
```

Both scripts recurse with `rglob("*.epub")`, log per-file progress, and skip
corrupt EPUBs without aborting the whole batch.

## Notes

- Output is streamed document-by-document; nothing is buffered into one giant string.
- Font sizes are returned as written in the EPUB/CSS (for example `12pt`, `14px`, `1.2em`).
- Complex CSS selectors (`#id`, descendant selectors, `@font-face`) are not fully supported yet.
- TEI XML output normalizes Tibetan Unicode; non-Tibetan text is passed through unchanged.
