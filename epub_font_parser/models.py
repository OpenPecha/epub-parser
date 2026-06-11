from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextSpan:
    """A contiguous run of text with resolved font metadata."""

    text: str
    font_family: str | None = None
    font_size: str | None = None
    document_href: str | None = None
    element: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "text": self.text,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "document_href": self.document_href,
            "element": self.element,
        }
