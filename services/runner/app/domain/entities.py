from dataclasses import dataclass
from enum import StrEnum


class ProblemKind(StrEnum):
    JS_ERROR = "js_error"
    HTTP_ERROR = "http_error"


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
