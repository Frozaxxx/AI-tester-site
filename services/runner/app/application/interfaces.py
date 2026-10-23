from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol

from app.domain.entities import Action, ActionResult, Job, PageProblem


class Runs(Protocol):
    async def claim(self):
        """Берёт следующий прогон из очереди или возвращает None."""

    async def add_step(self, run_id: str, index: int, action: Action, result: ActionResult) -> None:
        """Записывает выполненное действие агента в прогон."""

    async def add_finding(self, run_id: str, problem: PageProblem, step_index: int) -> None:
        """Записывает найденную проблему как баг прогона."""

    async def finish(self, run_id: str) -> None:
        """Завершает прогон."""

    async def crash(self, run_id: str) -> None:
        """Отмечает, что прогон сломался из-за раннера."""

    async def save_test(self, run_id: str, code: str) -> None:
        """Сохраняет сгенерированный Playwright-тест прогона."""


class Projects(Protocol):
    async def get_project(self, owner_id: str, project_id: str):
        """Получает проект владельца прогона."""

    async def list_scenarios(self, owner_id: str, project_id: str) -> list:
        """Получает сценарии проекта владельца прогона."""


class Browser(Protocol):
    async def perform(self, action: Action) -> ActionResult:
        """Выполняет одно действие на странице."""

    def take_problems(self) -> list[PageProblem]:
        """Отдаёт найденные на страницах проблемы."""


BrowserFactory = Callable[[str], AbstractAsyncContextManager[Browser]]
Planner = Callable[[Job], list[Action]]
