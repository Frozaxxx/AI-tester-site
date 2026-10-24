import asyncio
import logging

from app.application.agent import SmokeAgent
from app.application.codegen import generate_test
from app.application.interfaces import Agent, Browser, BrowserFactory, Projects, Runs
from app.domain.entities import Action, ActionResult, Job, PageProblem, ProblemKind
from app.domain.exceptions import RunCancelledError

RUN_TIMEOUT_SECONDS = 600
BLOCKED_MARKERS = ("ERR_BLOCKED_BY_CLIENT", "заблокирован")

logger = logging.getLogger("runner")


def navigation_problem(action: Action, result: ActionResult) -> PageProblem | None:
    """Считает багом страницу, которая не открылась, если её не заблокировали мы сами."""
    if action.name != "goto" or result.ok or not result.error:
        return None
    if any(marker in result.error for marker in BLOCKED_MARKERS):
        return None
    return PageProblem(
        kind=ProblemKind.HTTP_ERROR,
        title=f"Страница {action.value} не открылась",
        details=result.error,
    )


class RunRecorder:
    def __init__(self, runs: Runs, run_id: str, browser: Browser) -> None:
        self._runs = runs
        self._run_id = run_id
        self._browser = browser
        self._index = -1

    async def step(self, action: Action, result: ActionResult) -> None:
        """Записывает шаг и все проблемы страницы, которые появились после него."""
        self._index += 1
        await self._runs.add_step(self._run_id, self._index, action, result)
        problems = self._browser.take_problems()
        if (problem := navigation_problem(action, result)) is not None:
            problems.insert(0, problem)
        for problem in problems:
            await self._runs.add_finding(self._run_id, problem, self._index)

    async def bug(self, problem: PageProblem) -> None:
        """Записывает баг, который заметил агент, на последнем шаге."""
        await self._runs.add_finding(self._run_id, problem, max(self._index, 0))

    async def tokens(self, count: int) -> None:
        """Прибавляет к прогону потраченные токены LLM."""
        await self._runs.add_tokens(self._run_id, count)


class RunWorker:
    def __init__(
        self,
        runs: Runs,
        projects: Projects,
        browser_factory: BrowserFactory,
        agent: Agent | None = None,
    ) -> None:
        self._runs = runs
        self._projects = projects
        self._browser_factory = browser_factory
        self._agent = agent or SmokeAgent()

    async def run_once(self) -> bool:
        """Берёт один прогон из очереди и выполняет его, а при пустой очереди возвращает False."""
        claimed = await self._runs.claim()
        if claimed is None:
            return False
        run_id = claimed.run.id
        try:
            async with asyncio.timeout(RUN_TIMEOUT_SECONDS):
                job = await self._load_job(claimed)
                actions = await self._execute(job)
            await self._runs.finish(run_id)
            await self._save_test(job, actions)
        except RunCancelledError:
            logger.info("прогон %s отменён, останавливаемся", run_id)
        except Exception:
            logger.exception("прогон %s сломался", run_id)
            await self._crash(run_id)
        return True

    async def _load_job(self, claimed) -> Job:
        """Собирает задание: адрес сайта из проекта и текст сценария, если он выбран."""
        run, owner_id = claimed.run, claimed.owner_id
        project = await self._projects.get_project(owner_id, run.project_id)
        scenario_id = run.scenario_id if run.HasField("scenario_id") else None
        scenario_text = None
        if scenario_id:
            scenarios = await self._projects.list_scenarios(owner_id, run.project_id)
            scenario = next((s for s in scenarios if s.id == scenario_id), None)
            if scenario is None:
                raise LookupError(f"Сценарий {scenario_id} удалён")
            scenario_text = scenario.text
        return Job(
            run_id=run.id,
            owner_id=owner_id,
            project_id=run.project_id,
            base_url=project.base_url,
            scenario_id=scenario_id,
            scenario_text=scenario_text,
        )

    async def _execute(self, job: Job) -> list[Action]:
        """Запускает агента на сайте проекта и возвращает выполненные им действия."""
        async with self._browser_factory(job.base_url) as browser:
            recorder = RunRecorder(self._runs, job.run_id, browser)
            return await self._agent.run(job, browser, recorder)

    async def _save_test(self, job: Job, actions: list[Action]) -> None:
        """Сохраняет Playwright-тест из шагов прогона и не роняет раннер, если это не удалось."""
        if not actions:
            return
        try:
            await self._runs.save_test(job.run_id, generate_test(job, actions))
        except Exception:
            logger.exception("не удалось сохранить тест прогона %s", job.run_id)

    async def _crash(self, run_id: str) -> None:
        """Пытается отметить прогон сломанным и не падает, если runs недоступен."""
        try:
            await self._runs.crash(run_id)
        except Exception:
            logger.exception("не удалось отметить прогон %s сломанным", run_id)
