from dataclasses import dataclass
from enum import StrEnum


class ProblemKind(StrEnum):
    JS_ERROR = "js_error"
    HTTP_ERROR = "http_error"
    LLM_JUDGE = "llm_judge"


@dataclass(frozen=True, kw_only=True)
class Action:
    name: str
    locator: str | None = None
    value: str | None = None


@dataclass(frozen=True, kw_only=True)
class ActionResult:
    ok: bool
    error: str | None = None


@dataclass(frozen=True, kw_only=True)
class PageProblem:
    kind: ProblemKind
    title: str
    details: str = ""


@dataclass(frozen=True, kw_only=True)
class Job:
    run_id: str
    owner_id: str
    project_id: str
    base_url: str
    scenario_id: str | None = None
    scenario_text: str | None = None


@dataclass(frozen=True, kw_only=True)
class Element:
    index: int
    role: str
    name: str
    locator: str


@dataclass(frozen=True, kw_only=True)
class PageSnapshot:
    url: str
    title: str
    text: str
    elements: list[Element]

    def describe(self) -> str:
        """Описывает страницу для LLM: адрес, текст и пронумерованные элементы."""
        lines = [f"Адрес: {self.url}", f"Заголовок: {self.title}", "Текст страницы:", self.text]
        lines.append("Элементы, с которыми можно работать:")
        lines += [f"[{e.index}] {e.role} «{e.name}»" for e in self.elements]
        return "\n".join(lines)
