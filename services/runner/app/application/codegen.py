from urllib.parse import urljoin

from app.domain.entities import Action, Job
from app.domain.exceptions import ActionError
from app.domain.services import validate_action

HEADER = '''from playwright.sync_api import Page, expect

BASE_URL = {base_url}
CHECKED_RESOURCES = {{"document", "xhr", "fetch", "script", "stylesheet", "image"}}


def test_run_{name}(page: Page) -> None:
    """Повторяет прогон {name}: страницы должны открываться без ошибок."""
    errors = []
    page.on("pageerror", lambda error: errors.append(f"JS: {{error}}"))
    page.on(
        "console",
        lambda message: message.type == "error"
        and not message.text.startswith("Failed to load resource")
        and errors.append(f"console: {{message.text}}"),
    )
    page.on(
        "response",
        lambda response: (
            response.status >= 500
            or (response.status >= 400 and response.request.resource_type in CHECKED_RESOURCES)
        )
        and not response.url.endswith("/favicon.ico")
        and errors.append(f"{{response.status}} {{response.url}}"),
    )
'''


def _is_valid(action: Action) -> bool:
    """Проверяет, что действие корректное и его можно перевести в код."""
    try:
        validate_action(action)
    except ActionError:
        return False
    return True


def _target(action: Action) -> str:
    """Возвращает код локатора действия, а без локатора саму страницу."""
    return f"page.locator({action.locator!r}).first" if action.locator else "page"


def _line(action: Action, base_url: str) -> str:
    """Переводит одно действие агента в строку Playwright-кода."""
    target = _target(action)
    match action.name:
        case "goto":
            url = urljoin(base_url + "/", action.value)
            if url.startswith(base_url):
                return f"page.goto(BASE_URL + {url[len(base_url) :]!r})"
            return f"page.goto({url!r})"
        case "click":
            return f"{target}.click()"
        case "fill":
            return f"{target}.fill({action.value!r})"
        case "press":
            keyboard = f"{target}.press" if action.locator else "page.keyboard.press"
            return f"{keyboard}({action.value!r})"
        case "select":
            return f"{target}.select_option({action.value!r})"
        case "check":
            return f"{target}.check()"
        case "expect_text":
            where = target if action.locator else 'page.locator("body")'
            return f"expect({where}).to_contain_text({action.value!r})"
        case "expect_url":
            return f"assert {action.value!r} in page.url"
        case "wait":
            return f"page.wait_for_timeout({int(action.value)})"
    raise ValueError(f"Неизвестное действие {action.name}")


def generate_test(job: Job, actions: list[Action]) -> str:
    """Собирает pytest-тест на Playwright, который повторяет шаги прогона и ловит ошибки страниц."""
    base_url = job.base_url.rstrip("/")
    code = HEADER.format(base_url=repr(base_url), name=job.run_id.replace("-", "_")[:8])
    body = [f"    {_line(action, base_url)}" for action in actions if _is_valid(action)]
    body.append("    assert errors == [], errors")
    return code + "\n".join(body) + "\n"
