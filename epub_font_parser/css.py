from __future__ import annotations

import re
from dataclasses import dataclass, field

_FONT_FAMILY_RE = re.compile(
    r"font-family\s*:\s*([^;]+)",
    re.IGNORECASE,
)
_FONT_SIZE_RE = re.compile(
    r"font-size\s*:\s*([^;]+)",
    re.IGNORECASE,
)
_RULE_RE = re.compile(
    r"([^{]+)\{([^}]*)\}",
    re.DOTALL,
)


@dataclass
class StyleState:
    font_family: str | None = None
    font_size: str | None = None

    def copy(self) -> StyleState:
        return StyleState(
            font_family=self.font_family,
            font_size=self.font_size,
        )

    def apply_declarations(self, declarations: str) -> None:
        family_match = _FONT_FAMILY_RE.search(declarations)
        if family_match:
            self.font_family = _normalize_font_family(family_match.group(1))

        size_match = _FONT_SIZE_RE.search(declarations)
        if size_match:
            self.font_size = _normalize_font_size(size_match.group(1))


@dataclass
class Stylesheet:
    tag_rules: dict[str, StyleState] = field(default_factory=dict)
    class_rules: dict[str, StyleState] = field(default_factory=dict)
    tag_class_rules: dict[tuple[str, str], StyleState] = field(default_factory=dict)

    def resolve_for_element(
        self,
        tag_name: str,
        class_names: list[str],
        inherited: StyleState,
    ) -> StyleState:
        resolved = inherited.copy()

        tag_rule = self.tag_rules.get(tag_name)
        if tag_rule:
            resolved.font_family = tag_rule.font_family or resolved.font_family
            resolved.font_size = tag_rule.font_size or resolved.font_size

        for class_name in class_names:
            class_rule = self.class_rules.get(class_name)
            if class_rule:
                resolved.font_family = class_rule.font_family or resolved.font_family
                resolved.font_size = class_rule.font_size or resolved.font_size

            tag_class_rule = self.tag_class_rules.get((tag_name, class_name))
            if tag_class_rule:
                resolved.font_family = tag_class_rule.font_family or resolved.font_family
                resolved.font_size = tag_class_rule.font_size or resolved.font_size

        return resolved


def parse_stylesheets(style_texts: list[str]) -> Stylesheet:
    stylesheet = Stylesheet()

    for style_text in style_texts:
        for selector, declarations in _RULE_RE.findall(style_text):
            state = StyleState()
            state.apply_declarations(declarations)

            if not state.font_family and not state.font_size:
                continue

            for raw_selector in selector.split(","):
                selector_text = raw_selector.strip()
                if not selector_text:
                    continue
                _register_selector(stylesheet, selector_text, state)

    return stylesheet


def parse_inline_style(style_attr: str | None) -> StyleState:
    state = StyleState()
    if style_attr:
        state.apply_declarations(style_attr)
    return state


def _register_selector(stylesheet: Stylesheet, selector: str, state: StyleState) -> None:
    selector = re.sub(r"\s+", " ", selector.strip())
    if not selector:
        return

    tag_class_match = re.fullmatch(r"([a-zA-Z][\w-]*)\.([\w-]+)", selector)
    if tag_class_match:
        key = (tag_class_match.group(1).lower(), tag_class_match.group(2))
        stylesheet.tag_class_rules[key] = _merge_style(
            stylesheet.tag_class_rules.get(key),
            state,
        )
        return

    if selector.startswith("."):
        class_name = selector[1:]
        if class_name:
            stylesheet.class_rules[class_name] = _merge_style(
                stylesheet.class_rules.get(class_name),
                state,
            )
        return

    tag_match = re.fullmatch(r"[a-zA-Z][\w-]*", selector)
    if tag_match:
        tag_name = tag_match.group(0).lower()
        stylesheet.tag_rules[tag_name] = _merge_style(
            stylesheet.tag_rules.get(tag_name),
            state,
        )


def _merge_style(existing: StyleState | None, new: StyleState) -> StyleState:
    if existing is None:
        return new.copy()
    merged = existing.copy()
    merged.font_family = new.font_family or merged.font_family
    merged.font_size = new.font_size or merged.font_size
    return merged


def _normalize_font_family(raw_value: str) -> str:
    parts = []
    for chunk in raw_value.split(","):
        cleaned = chunk.strip().strip("'\"")
        if cleaned:
            parts.append(cleaned)
    return parts[0] if parts else raw_value.strip()


def _normalize_font_size(raw_value: str) -> str:
    return re.sub(r"\s+", "", raw_value.strip())
