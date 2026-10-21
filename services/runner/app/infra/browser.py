import asyncio
from types import TracebackType
from typing import Self
from urllib.parse import urlsplit

from playwright.async_api import (
    Browser,
    ConsoleMessage,
    Error,
    Page,
    Playwright,
    Request,
    Response,
    Route,
    async_playwright,
    expect,
)

from app.domain.entities import Action, ActionResult, PageProblem, ProblemKind
from app.domain.exceptions import ActionError
from app.domain.services import resolve_internal, same_site_url, validate_action

ACTION_TIMEOUT_MS = 5_000
NAVIGATION_TIMEOUT_MS = 15_000
ALLOWED_SCHEMES = frozenset({"http", "https", "data", "blob", "about"})
CHECKED_RESOURCES = frozenset({"document", "xhr", "fetch", "script", "stylesheet", "image"})
ERROR_MAX_LENGTH = 500


def _short(message: str) -> str:
    """Оставляет от ошибки Playwright первую строку без длинного лога вызова."""
    return message.strip().splitlines()[0][:ERROR_MAX_LENGTH] if message.strip() else "Ошибка"


class SiteBrowser:
    def __init__(self, base_url: str, allow_internal: bool = False) -> None:
        self._base_url = base_url.rstrip("/")
        self._allow_internal = allow_internal
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None
        self._problems: dict[str, PageProblem] = {}
        self._hosts: dict[str, bool] = {}

    async def __aenter__(self) -> Self:
        """Запускает браузер и открывает пустую вкладку с защитой от внутренних адресов."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch()
        context = await self._browser.new_context(accept_downloads=False)
        context.set_default_timeout(ACTION_TIMEOUT_MS)
        context.set_default_navigation_timeout(NAVIGATION_TIMEOUT_MS)
        await context.route("**/*", self._guard)
        self._page = await context.new_page()
        self._page.on("pageerror", self._on_page_error)
        self._page.on("console", self._on_console)
        self._page.on("response", self._on_response)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Закрывает браузер и Playwright."""
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()

    @property
    def url(self) -> str:
        """Возвращает адрес открытой страницы."""
        return self._page.url

    async def perform(self, action: Action) -> ActionResult:
        """Выполняет одно действие на странице и сообщает, получилось ли оно."""
        try:
            validate_action(action)
            await self._run(action)
        except ActionError as exc:
            return ActionResult(ok=False, error=exc.message)
        except (Error, AssertionError) as exc:
            return ActionResult(ok=False, error=_short(str(exc)))
        return ActionResult(ok=True)

    def take_problems(self) -> list[PageProblem]:
        """Отдаёт найденные на страницах проблемы и очищает список."""
        problems = list(self._problems.values())
        self._problems.clear()
        return problems

    async def _run(self, action: Action) -> None:
        """Вызывает нужный метод Playwright для действия."""
        page = self._page
        target = page.locator(action.locator).first if action.locator else None
        match action.name:
            case "goto":
                await page.goto(same_site_url(self._base_url, action.value))
            case "click":
                await target.click()
            case "fill":
                await target.fill(action.value)
            case "press":
                await (target.press(action.value) if target else page.keyboard.press(action.value))
            case "select":
                await target.select_option(action.value)
            case "check":
                await target.check()
            case "expect_text":
                where = target if target else page.locator("body")
                await expect(where).to_contain_text(action.value, timeout=ACTION_TIMEOUT_MS)
            case "expect_url":
                if action.value not in page.url:
                    raise ActionError(f"Адрес страницы {page.url} не содержит «{action.value}»")
            case "wait":
                await page.wait_for_timeout(int(action.value))

    async def _guard(self, route: Route, request: Request) -> None:
        """Пропускает только запросы к публичным сайтам, а внутренние адреса блокирует."""
        parts = urlsplit(request.url)
        if parts.scheme not in ALLOWED_SCHEMES:
            await route.abort("blockedbyclient")
            return
        host = parts.hostname
        if host and not self._allow_internal and await self._is_internal(host):
            await route.abort("blockedbyclient")
            return
        await route.continue_()

    async def _is_internal(self, host: str) -> bool:
        """Проверяет хост на внутренний адрес и запоминает ответ, чтобы не резолвить повторно."""
        if host not in self._hosts:
            self._hosts[host] = await asyncio.to_thread(resolve_internal, host)
        return self._hosts[host]

    def _add(self, kind: ProblemKind, title: str, details: str = "") -> None:
        """Запоминает проблему один раз, даже если она повторилась."""
        self._problems.setdefault(title, PageProblem(kind=kind, title=title, details=details))

    def _on_page_error(self, error: Error) -> None:
        """Записывает необработанную ошибку JavaScript на странице."""
        self._add(
            ProblemKind.JS_ERROR,
            f"Ошибка JavaScript: {_short(error.message)}",
            f"Страница: {self._page.url}\n{error.stack or ''}",
        )

    def _on_console(self, message: ConsoleMessage) -> None:
        """Записывает ошибки из консоли браузера, кроме заблокированных нами запросов."""
        if message.type != "error" or "ERR_BLOCKED_BY_CLIENT" in message.text:
            return
        if message.text.startswith("Failed to load resource"):
            return
        self._add(
            ProblemKind.JS_ERROR,
            f"Ошибка в консоли: {_short(message.text)}",
            f"Страница: {self._page.url}",
        )

    def _on_response(self, response: Response) -> None:
        """Записывает ответы сервера с ошибкой: любые 5xx и 4xx для страниц и ресурсов."""
        status = response.status
        resource = response.request.resource_type
        path = urlsplit(response.url).path
        if status >= 500 or (
            status >= 400 and resource in CHECKED_RESOURCES and path != "/favicon.ico"
        ):
            self._add(
                ProblemKind.HTTP_ERROR,
                f"{status} на {response.url}",
                f"Тип запроса: {resource}\nСтраница: {self._page.url}",
            )
