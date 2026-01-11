from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import Any


def _normalize(text: str) -> str:
    return dedent(text).strip()


def compose_instructions(*parts: str) -> str:
    """Compose instruction blocks into a single instruction string.

    Empty/whitespace-only parts are ignored. Each part is dedented and stripped,
    then joined with a blank line to keep boundaries readable.
    """
    normalized = [_normalize(part) for part in parts if part and part.strip()]
    return "\n\n".join(normalized).strip()


@dataclass(frozen=True)
class PromptSpec:
    """A versioned prompt definition with render helpers.

    This is intentionally content-agnostic: pass shared/base instructions from
    higher-level modules (e.g., chains) via `render_instructions(...)`.
    """

    id: str
    version: int
    input_template: str
    instructions_template: str = ""
    name: str | None = None
    output_type: type[Any] | None = None

    def render_input(self, **vars: Any) -> str:
        return _normalize(self.input_template).format(**vars)

    def render_instructions(self, *bases: str, **vars: Any) -> str:
        rendered = _normalize(self.instructions_template).format(**vars) if self.instructions_template else ""
        return compose_instructions(*bases, rendered)
