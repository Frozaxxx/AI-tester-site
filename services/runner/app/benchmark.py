import argparse
import asyncio
from dataclasses import dataclass, field

from app.application.agent import LlmAgent
from app.application.worker import navigation_problem
from app.domain.entities import Action, ActionResult, Job, PageProblem, ProblemKind
from app.infra.browser import SiteBrowser


@dataclass(frozen=True)
class KnownBug:
    id: str
    kind: ProblemKind
    markers: tuple[str, ...]


KNOWN_BUGS = [
    KnownBug(id="broken_link", kind=ProblemKind.HTTP_ERROR, markers=("/delivery",)),
    KnownBug(id="favorites_js", kind=ProblemKind.JS_ERROR, markers=("addtofavorites",)),
    KnownBug(id="search_500", kind=ProblemKind.HTTP_ERROR, markers=("/search",)),
    KnownBug(id="cart_total", kind=ProblemKind.LLM_JUDGE, markers=("итог", "сумм")),
    KnownBug(id="pagination", kind=ProblemKind.LLM_JUDGE, markers=("повтор", "дублир")),
    KnownBug(
        id="checkout_validation",
        kind=ProblemKind.LLM_JUDGE,
        markers=("пуст", "валидац", "обязательн", "без имени"),
    ),
]

SCENARIOS = [
    None,
    "Открой любой товар, добавь его в корзину в количестве 3 штук и проверь, что итоговая "
    "сумма в корзине равна цене, умноженной на количество.",
    "Добавь товар в корзину и попробуй оформить заказ, не заполняя поля. Сайт не должен "
    "принимать заказ с пустыми именем, email и адресом.",
    "Пролистай все страницы каталога и проверь, что товары не повторяются между страницами.",
    "Проверь поиск: найди ноутбук, а потом нажми «Найти» с пустым запросом.",
    "Открой товар, нажми «В избранное», потом проверь ссылки в подвале сайта.",
]


def match(problem: PageProblem) -> str | None:
    """Определяет, какой из известных багов демо-магазина описывает найденная проблема."""
    text = f"{problem.title} {problem.details}".lower()
    for bug in KNOWN_BUGS:
        if bug.kind == problem.kind and any(marker in text for marker in bug.markers):
            return bug.id
    return None


@dataclass
class Report:
    found: set[str] = field(default_factory=set)
    false_positives: list[PageProblem] = field(default_factory=list)
    tokens: int = 0

    def add(self, problem: PageProblem) -> None:
        """Засчитывает проблему как известный баг или как ложное срабатывание."""
        if (bug_id := match(problem)) is not None:
            self.found.add(bug_id)
        else:
            self.false_positives.append(problem)

    def summary(self) -> str:
        """Описывает итог: сколько известных багов найдено и сколько лишних срабатываний."""
        lines = [f"Найдено багов: {len(self.found)} из {len(KNOWN_BUGS)}"]
        lines += [f"  [{'x' if bug.id in self.found else ' '}] {bug.id}" for bug in KNOWN_BUGS]
        lines.append(f"Ложных срабатываний: {len(self.false_positives)}")
        lines += [f"  - {p.kind}: {p.title}" for p in self.false_positives]
        lines.append(f"Потрачено токенов: {self.tokens}")
        return "\n".join(lines)


class BenchmarkRecorder:
    def __init__(self, browser: SiteBrowser, report: Report) -> None:
        self._browser = browser
        self._report = report

    async def step(self, action: Action, result: ActionResult) -> None:
        """Засчитывает проблемы страницы, найденные после шага."""
        problems = self._browser.take_problems()
        if (problem := navigation_problem(action, result)) is not None:
            problems.append(problem)
        for problem in problems:
            self._report.add(problem)

    async def bug(self, problem: PageProblem) -> None:
        """Засчитывает баг, о котором сообщил агент."""
        self._report.add(problem)

    async def tokens(self, count: int) -> None:
        """Учитывает потраченные токены."""
        self._report.tokens += count


async def run_benchmark(agent: LlmAgent, base_url: str, allow_internal: bool = True) -> Report:
    """Прогоняет агента по всем сценариям демо-магазина и собирает общий отчёт."""
    report = Report()
    for number, scenario in enumerate(SCENARIOS):
        job = Job(
            run_id=f"benchmark-{number}",
            owner_id="benchmark",
            project_id="demo-shop",
            base_url=base_url,
            scenario_text=scenario,
        )
        async with SiteBrowser(base_url, allow_internal=allow_internal) as browser:
            await agent.run(job, browser, BenchmarkRecorder(browser, report))
    return report


async def main() -> None:
    """Запускает оценку агента на демо-магазине с LLM из настроек раннера."""
    from app.config import settings
    from app.infra.llm import make_chat_model

    parser = argparse.ArgumentParser(description="Оценка агента на демо-магазине")
    parser.add_argument("--site", default="http://127.0.0.1:8001")
    args = parser.parse_args()
    model = make_chat_model(settings)
    if model is None:
        raise SystemExit("Укажите RUNNER_LLM_PROVIDER в .env, без LLM оценивать нечего")
    report = await run_benchmark(LlmAgent(model), args.site)
    print(report.summary())


if __name__ == "__main__":
    asyncio.run(main())
