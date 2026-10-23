import asyncio
import logging

from app.application.interfaces import BrowserFactory, Planner, Projects, Runs
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


def smoke_plan(job: Job) -> list[Action]:
    """Простой план без LLM: открыть главную страницу сайта и собрать ошибки."""
    return [Action(name="goto", value="/")]


class RunWorker:
    def __init__(
        self,
        runs: Runs,
        projects: Projects,
        browser_factory: BrowserFactory,
        planner: Planner = smoke_plan,
    ) -> None:
        self._runs = runs
        self._projects = projects
        self._browser_factory = browser_factory
        self._planner = planner

    async def run_once(self) -> bool:
        """Берёт один прогон из очереди и выполняет его, а при пустой очереди возвращает False."""
        claimed = await self._runs.claim()
        if claimed is None:
            return False
        run_id = claimed.run.id
        try:
            async with asyncio.timeout(RUN_TIMEOUT_SECONDS):
                job = await self._load_job(claimed)
                await self._execute(job)
            await self._runs.finish(run_id)
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

    async def _execute(self, job: Job) -> None:
        """Выполняет план по шагам и записывает каждый шаг и найденные проблемы в runs."""
        async with self._browser_factory(job.base_url) as browser:
            for index, action in enumerate(self._planner(job)):
                result = await browser.perform(action)
                await self._runs.add_step(job.run_id, index, action, result)
                problems = browser.take_problems()
                if (problem := navigation_problem(action, result)) is not None:
                    problems.insert(0, problem)
                for problem in problems:
                    await self._runs.add_finding(job.run_id, problem, index)

    async def _crash(self, run_id: str) -> None:
        """Пытается отметить прогон сломанным и не падает, если runs недоступен."""
        try:
            await self._runs.crash(run_id)
        except Exception:
            logger.exception("не удалось отметить прогон %s сломанным", run_id)
