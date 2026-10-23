from contextlib import asynccontextmanager

import pytest

from app.application.worker import RunWorker, navigation_problem
from app.domain.entities import Action, ActionResult, Job, PageProblem, ProblemKind
from app.domain.exceptions import RunCancelledError
from app.grpc_gen import projects_pb2, runs_pb2

PROBLEM = PageProblem(kind=ProblemKind.JS_ERROR, title="Ошибка JavaScript: boom")


class FakeRuns:
    def __init__(self, scenario_id: str | None = None, cancel_on_step: int | None = None) -> None:
        run = runs_pb2.Run(id="run-1", project_id="project-1", scenario_id=scenario_id)
        self.queue = [runs_pb2.ClaimedRun(run=run, owner_id="owner-1")]
        self.cancel_on_step = cancel_on_step
        self.steps: list[tuple[int, str, bool]] = []
        self.findings: list[tuple[str, int]] = []
        self.finished: list[str] = []
        self.crashed: list[str] = []
        self.tests: list[str] = []

    async def claim(self):
        return self.queue.pop(0) if self.queue else None

    async def add_step(self, run_id: str, index: int, action: Action, result: ActionResult) -> None:
        if index == self.cancel_on_step:
            raise RunCancelledError
        self.steps.append((index, action.name, result.ok))

    async def add_finding(self, run_id: str, problem: PageProblem, step_index: int) -> None:
        self.findings.append((problem.title, step_index))

    async def finish(self, run_id: str) -> None:
        self.finished.append(run_id)

    async def crash(self, run_id: str) -> None:
        self.crashed.append(run_id)

    async def save_test(self, run_id: str, code: str) -> None:
        self.tests.append(code)


class FakeProjects:
    async def get_project(self, owner_id: str, project_id: str) -> projects_pb2.Project:
        assert (owner_id, project_id) == ("owner-1", "project-1")
        return projects_pb2.Project(id=project_id, base_url="https://shop.example.com")

    async def list_scenarios(self, owner_id: str, project_id: str) -> list:
        return [projects_pb2.Scenario(id="scenario-1", text="Добавь товар в корзину")]


class FakeBrowser:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.done: list[Action] = []
        self.base_url: str | None = None

    async def perform(self, action: Action) -> ActionResult:
        if self.fail:
            raise RuntimeError("браузер упал")
        self.done.append(action)
        return ActionResult(ok=action.name != "click", error=None)

    def take_problems(self) -> list[PageProblem]:
        return [PROBLEM] if len(self.done) == 1 else []


def factory(browser: FakeBrowser):
    """Делает фабрику, которая отдаёт заранее созданный фейковый браузер."""

    @asynccontextmanager
    async def make(base_url: str):
        browser.base_url = base_url
        yield browser

    return make


def plan(job: Job) -> list[Action]:
    """Тестовый план из трёх действий."""
    return [
        Action(name="goto", value="/"),
        Action(name="click", locator="text=Купить"),
        Action(name="expect_text", value="Корзина"),
    ]


async def test_empty_queue() -> None:
    """При пустой очереди воркер ничего не делает и сообщает об этом."""
    runs = FakeRuns()
    runs.queue.clear()
    assert await RunWorker(runs, FakeProjects(), factory(FakeBrowser()), plan).run_once() is False


async def test_run_is_executed_and_finished() -> None:
    """Воркер выполняет план на сайте проекта, пишет шаги и баги и завершает прогон."""
    runs, browser = FakeRuns(), FakeBrowser()
    assert await RunWorker(runs, FakeProjects(), factory(browser), plan).run_once() is True
    assert browser.base_url == "https://shop.example.com"
    assert runs.steps == [(0, "goto", True), (1, "click", False), (2, "expect_text", True)]
    assert runs.findings == [(PROBLEM.title, 0)]
    assert runs.finished == ["run-1"] and runs.crashed == []
    assert len(runs.tests) == 1 and "page.goto(BASE_URL + '/')" in runs.tests[0]


async def test_scenario_text_reaches_planner() -> None:
    """Если прогон по сценарию, планировщик получает его текст."""
    seen: list[Job] = []

    def remember(job: Job) -> list[Action]:
        seen.append(job)
        return []

    runs = FakeRuns(scenario_id="scenario-1")
    await RunWorker(runs, FakeProjects(), factory(FakeBrowser()), remember).run_once()
    assert seen[0].scenario_text == "Добавь товар в корзину"
    assert runs.finished == ["run-1"]


async def test_cancelled_run_stops_without_crash() -> None:
    """Если пользователь отменил прогон, воркер молча останавливается."""
    runs = FakeRuns(cancel_on_step=1)
    await RunWorker(runs, FakeProjects(), factory(FakeBrowser()), plan).run_once()
    assert runs.steps == [(0, "goto", True)]
    assert runs.finished == [] and runs.crashed == [] and runs.tests == []


@pytest.mark.parametrize("scenario_id", [None, "deleted-scenario"])
async def test_failures_crash_the_run(scenario_id: str | None) -> None:
    """Падение браузера или удалённый сценарий помечают прогон сломанным."""
    runs = FakeRuns(scenario_id=scenario_id)
    browser = FakeBrowser(fail=scenario_id is None)
    await RunWorker(runs, FakeProjects(), factory(browser), plan).run_once()
    assert runs.crashed == ["run-1"] and runs.finished == []


def test_navigation_problem() -> None:
    """Неоткрывшаяся страница считается багом, а заблокированный нами адрес нет."""
    goto = Action(name="goto", value="/")
    down = ActionResult(ok=False, error="net::ERR_CONNECTION_REFUSED at http://shop/")
    assert navigation_problem(goto, down).title == "Страница / не открылась"
    blocked = ActionResult(ok=False, error="net::ERR_BLOCKED_BY_CLIENT at http://10.0.0.1/")
    assert navigation_problem(goto, blocked) is None
    assert navigation_problem(goto, ActionResult(ok=True)) is None
    click = Action(name="click", locator="text=Купить")
    assert navigation_problem(click, ActionResult(ok=False, error="timeout")) is None
