from app.domain.entities import Action, ProblemKind
from app.infra.browser import SiteBrowser


async def test_actions_on_page(site_url: str) -> None:
    """Браузер открывает страницу, заполняет форму, нажимает кнопку и проверяет текст."""
    async with SiteBrowser(site_url, allow_internal=True) as browser:
        steps = [
            Action(name="goto", value="/"),
            Action(name="expect_text", value="Каталог"),
            Action(name="fill", locator="input[name=q]", value="ноутбук"),
            Action(name="press", locator="input[name=q]", value="Enter"),
            Action(name="select", locator="select[name=sort]", value="new"),
            Action(name="check", locator="input[name=stock]"),
            Action(name="click", locator="role=button[name='В корзину']"),
            Action(name="expect_text", locator="#cart", value="Добавлено"),
            Action(name="expect_url", value="127.0.0.1"),
            Action(name="wait", value="10"),
        ]
        for step in steps:
            result = await browser.perform(step)
            assert result.ok, (step, result.error)
        assert browser.take_problems() == []


async def test_failed_actions_return_short_error(site_url: str) -> None:
    """Неудачное действие не роняет раннер, а возвращает короткую ошибку."""
    async with SiteBrowser(site_url, allow_internal=True) as browser:
        await browser.perform(Action(name="goto", value="/"))
        missing = await browser.perform(Action(name="click", locator="text=Нет такой кнопки"))
        assert not missing.ok and "\n" not in missing.error
        wrong_text = await browser.perform(Action(name="expect_text", value="Оплачено"))
        assert not wrong_text.ok
        unknown = await browser.perform(Action(name="rm", value="-rf"))
        assert not unknown.ok and "Неизвестное действие" in unknown.error


async def test_problems_are_collected(site_url: str) -> None:
    """Ошибки JavaScript, консоли и ответы 4xx/5xx становятся проблемами страницы."""
    async with SiteBrowser(site_url, allow_internal=True) as browser:
        for path in ("/js-error", "/console-error", "/api-error", "/js-error"):
            await browser.perform(Action(name="goto", value=path))
        await browser.perform(Action(name="goto", value="/"))
        await browser.perform(Action(name="click", locator="text=Сломанная ссылка"))
        await browser.perform(Action(name="wait", value="300"))
        problems = browser.take_problems()

    titles = [p.title for p in problems]
    assert any("undefinedFunction" in t for t in titles)
    assert any("Не удалось загрузить корзину" in t for t in titles)
    assert any(t.startswith("500 на") and t.endswith("/api/cart") for t in titles)
    assert any(t.startswith("404 на") and t.endswith("/missing") for t in titles)
    assert len([t for t in titles if "undefinedFunction" in t]) == 1
    kinds = {p.kind for p in problems}
    assert kinds == {ProblemKind.JS_ERROR, ProblemKind.HTTP_ERROR}


async def test_internal_addresses_are_blocked(site_url: str) -> None:
    """Без разрешения браузер не открывает локальные адреса, а с чужого сайта не уходит."""
    async with SiteBrowser(site_url) as browser:
        blocked = await browser.perform(Action(name="goto", value="/"))
        assert not blocked.ok and "ERR_BLOCKED_BY_CLIENT" in blocked.error
        assert browser.take_problems() == []

    async with SiteBrowser(site_url, allow_internal=True) as browser:
        away = await browser.perform(Action(name="goto", value="https://example.com"))
        assert not away.ok and "тестируемого сайта" in away.error
