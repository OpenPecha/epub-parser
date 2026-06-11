from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import ebooklib
from bs4 import BeautifulSoup, NavigableString, Tag
from ebooklib import epub

from epub_font_parser.css import StyleState, Stylesheet, parse_inline_style, parse_stylesheets
from epub_font_parser.models import TextSpan

_BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}

_SKIP_TAGS = {"head", "script", "style", "meta", "link", "title"}


class EpubFontParser:
    """Parse an EPUB and stream text spans with font metadata."""

    def __init__(self, epub_path: str | Path) -> None:
        self.epub_path = Path(epub_path)

    def stream(self) -> Iterator[TextSpan]:
        book = epub.read_epub(str(self.epub_path))

        for spine_entry in book.spine:
            item_id = spine_entry[0]
            item = book.get_item_with_id(item_id)
            if item is None or item.get_type() != ebooklib.ITEM_DOCUMENT:
                continue

            document_href = item.get_name()
            soup = BeautifulSoup(item.content, "lxml-xml")
            stylesheet = self._load_stylesheet(book, soup, document_href)
            body = soup.body or soup
            yield from self._walk_element(
                body,
                inherited=StyleState(),
                stylesheet=stylesheet,
                document_href=document_href,
            )

    def _load_stylesheet(
        self,
        book: epub.EpubBook,
        soup: BeautifulSoup,
        document_href: str,
    ) -> Stylesheet:
        css_chunks: list[str] = [
            style_tag.get_text()
            for style_tag in soup.find_all("style")
        ]

        for link_tag in soup.find_all("link"):
            rel = link_tag.get("rel")
            rel_values = rel if isinstance(rel, list) else [rel]
            if not any(str(value).lower() == "stylesheet" for value in rel_values if value):
                continue

            href = link_tag.get("href")
            if not href:
                continue

            css_item = book.get_item_with_href(urljoin(document_href, href))
            if css_item is None:
                continue

            css_chunks.append(css_item.get_content().decode("utf-8", errors="replace"))

        return parse_stylesheets(css_chunks)

    def __iter__(self) -> Iterator[TextSpan]:
        return self.stream()

    def _walk_element(
        self,
        element: Tag | NavigableString,
        inherited: StyleState,
        stylesheet: Stylesheet,
        document_href: str,
    ) -> Iterator[TextSpan]:
        if isinstance(element, NavigableString):
            text = str(element)
            if not text:
                return
            yield TextSpan(
                text=text,
                font_family=inherited.font_family,
                font_size=inherited.font_size,
                document_href=document_href,
            )
            return

        if not isinstance(element, Tag):
            return

        tag_name = (element.name or "").lower()
        if tag_name in _SKIP_TAGS:
            return

        class_names = _class_names(element)
        resolved = stylesheet.resolve_for_element(tag_name, class_names, inherited)
        inline = parse_inline_style(element.get("style"))
        if inline.font_family:
            resolved.font_family = inline.font_family
        if inline.font_size:
            resolved.font_size = inline.font_size

        legacy_face = element.get("face")
        if legacy_face:
            resolved.font_family = legacy_face.strip()

        if tag_name == "font":
            legacy_size = element.get("size")
            if legacy_size and resolved.font_size is None:
                resolved.font_size = _html_font_size_to_css(legacy_size)

        if tag_name == "br":
            yield TextSpan(
                text="\n",
                font_family=resolved.font_family,
                font_size=resolved.font_size,
                document_href=document_href,
                element=tag_name,
            )
            return

        for child in element.children:
            yield from self._walk_element(
                child,
                inherited=resolved,
                stylesheet=stylesheet,
                document_href=document_href,
            )

        if tag_name in _BLOCK_TAGS and tag_name != "br":
            yield TextSpan(
                text="\n",
                font_family=resolved.font_family,
                font_size=resolved.font_size,
                document_href=document_href,
                element=tag_name,
            )


def stream_epub_text(epub_path: str | Path) -> Iterator[TextSpan]:
    """Convenience wrapper around :class:`EpubFontParser`."""
    return EpubFontParser(epub_path).stream()


def _class_names(element: Tag) -> list[str]:
    class_attr: Any = element.get("class")
    if not class_attr:
        return []
    if isinstance(class_attr, list):
        return [str(name) for name in class_attr]
    return str(class_attr).split()


def _html_font_size_to_css(size_value: str) -> str:
    mapping = {
        "1": "10pt",
        "2": "13pt",
        "3": "16pt",
        "4": "18pt",
        "5": "24pt",
        "6": "32pt",
        "7": "48pt",
    }
    return mapping.get(size_value.strip(), size_value.strip())
