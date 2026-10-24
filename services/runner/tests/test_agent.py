from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from app.application.agent import LlmAgent, to_action
from app.domain.entities import Action, ActionResult, Element, Job, PageProblem, PageSnapshot
from app.infra.browser import SiteBrowser


class ScriptedModel(BaseChatModel):
    """Фейковая LLM: на каждый ход отдаёт следующий заранее заданный вызов инструмента."""

    script: list
    prompts: list = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self.prompts.append(messages[-1].content)
        step = self.script.pop(0)
        calls = []
        if step is not None:
            name, args = step(messages[-1].content) if callable(step) else step
            calls = [{"name": name, "args": args, "id": f"call-{len(self.prompts)}"}]
        message = AIMessage(
            content="",
            tool_calls=calls,
            usage_metadata={
                "input_tokens": 100,
                "output_tokens": 10,
                "total_tokens": 110,
            },
        )
        return ChatResult(generations=[ChatGeneration(message=message)])


class Recorder:
    def __init__(self, browser: SiteBrowser) -> None:
        self.browser = browser
        self.steps: list[tuple[Action, ActionResult]] = []
        self.bugs: list[PageProblem] = []
        self.problems: list[PageProblem] = []
        self.used_tokens = 0

    async def step(self, action: Action, result: ActionResult) -> None:
        self.steps.append((action, result))
        self.problems += self.browser.take_problems()

    async def bug(self, problem: PageProblem) -> None:
        self.bugs.append(problem)

    async def tokens(self, count: int) -> None:
        self.used_tokens += count


def element_named(name: str):
    """Ход фейковой LLM: найти в описании страницы номер элемента с нужным именем."""

    def pick(page: str) -> int:
        for line in page.splitlines():
            if line.startswith("[") and f"«{name}»" in line:
                return int(line[1 : line.index("]")])
        raise AssertionError(f"нет элемента {name} в\n{page}")

    return pick


def click(name: str):
    """Ход фейковой LLM: кликнуть по элементу с именем."""
    return lambda page: ("act", {"action": "click", "element": element_named(name)(page)})


def fill(name: str, value: str):
    """Ход фейковой LLM: ввести текст в поле с именем."""
    return lambda page: (
        "act",
        {"action": "fill", "element": element_named(name)(page), "value": value},
    )


async def test_agent_walks_site_and_reports_bug(site_url: str) -> None:
    """Агент по ходам модели заполняет поле, жмёт кнопку, сообщает баг и заканчивает."""
    model = ScriptedModel(
        script=[
            fill("Поиск", "ноутбук"),
            click("В корзину"),
            ("act", {"action": "expect_text", "value": "Добавлено"}),
            ("report_bug", {"title": "Нет счётчика корзины", "details": "После добавления"}),
            ("finish", {"summary": "Проверил корзину"}),
        ]
    )
    async with SiteBrowser(site_url, allow_internal=True) as browser:
        recorder = Recorder(browser)
        actions = await LlmAgent(model).run(job_for(site_url), browser, recorder)

    assert [a.name for a in actions] == ["goto", "fill", "click", "expect_text"]
    assert actions[1].locator == 'input[name="q"]' and actions[1].value == "ноутбук"
    assert actions[2].locator == 'role=button[name="В корзину"]'
    assert all(result.ok for _, result in recorder.steps), recorder.steps
    assert [b.title for b in recorder.bugs] == ["Нет счётчика корзины"]
    assert recorder.used_tokens == 5 * 110
    assert "[" in model.prompts[0] and "«В корзину»" in model.prompts[0]


async def test_agent_stops_at_step_limit(site_url: str) -> None:
    """Агент, который никогда не заканчивает, останавливается по лимиту шагов."""
    model = ScriptedModel(script=[("act", {"action": "wait", "value": "1"})] * 10)
    async with SiteBrowser(site_url, allow_internal=True) as browser:
        recorder = Recorder(browser)
        actions = await LlmAgent(model, max_steps=3).run(job_for(site_url), browser, recorder)
    assert len(actions) == 1 + 3


async def test_agent_ends_when_model_answers_without_tool(site_url: str) -> None:
    """Если модель ответила текстом без инструмента, агент заканчивает работу."""
    model = ScriptedModel(script=[None])
    async with SiteBrowser(site_url, allow_internal=True) as browser:
        actions = await LlmAgent(model).run(job_for(site_url), browser, Recorder(browser))
    assert [a.name for a in actions] == ["goto"]


def test_wrong_element_number_becomes_failed_action() -> None:
    """Номер элемента вне списка не превращается в чужой локатор."""
    snapshot = PageSnapshot(
        url="u",
        title="t",
        text="",
        elements=[Element(index=0, role="button", name="Купить", locator="role=button")],
    )
    assert to_action({"action": "click", "element": 0}, snapshot).locator == "role=button"
    assert to_action({"action": "click", "element": 5}, snapshot).name == "unknown_element"
    assert to_action({"action": "click", "element": "0"}, snapshot).name == "unknown_element"


def job_for(site_url: str) -> Job:
    """Создаёт задание свободного исследования сайта."""
    return Job(run_id="r", owner_id="o", project_id="p", base_url=site_url)
