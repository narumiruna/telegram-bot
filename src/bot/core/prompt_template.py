from dataclasses import dataclass
from textwrap import dedent


def _normalize(text: str) -> str:
    return dedent(text).strip()


@dataclass(frozen=True)
class PromptTemplate:
    template: str

    def render(self, **kwargs: str) -> str:
        return _normalize(self.template.format(**kwargs))
