import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

from app.domain.entities import Action
from app.domain.exceptions import ActionError

NEEDS_LOCATOR = frozenset({"click", "fill", "select", "check"})
NEEDS_VALUE = frozenset({"goto", "fill", "press", "select", "expect_text", "expect_url", "wait"})
ACTIONS = NEEDS_LOCATOR | NEEDS_VALUE
WAIT_MAX_MS = 5_000


def validate_action(action: Action) -> None:
    """Проверяет, что действие известно и у него есть нужные локатор и значение."""
    if action.name not in ACTIONS:
        raise ActionError(f"Неизвестное действие «{action.name}»")
    if action.name in NEEDS_LOCATOR and not action.locator:
        raise ActionError(f"Для действия «{action.name}» нужен локатор")
    if action.name in NEEDS_VALUE and action.value is None:
        raise ActionError(f"Для действия «{action.name}» нужно значение")
    if action.name == "wait" and not (action.value.isdigit() and int(action.value) <= WAIT_MAX_MS):
        raise ActionError(f"Ждать можно от 0 до {WAIT_MAX_MS} мс")


def is_internal_ip(raw: str) -> bool:
    """Проверяет, что IP-адрес из локальной или внутренней сети, а не из интернета."""
    try:
        return not ipaddress.ip_address(raw).is_global
    except ValueError:
        return True


def resolve_internal(host: str) -> bool:
    """Резолвит хост и проверяет, ведёт ли хоть один его адрес во внутреннюю сеть."""
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    return any(is_internal_ip(info[4][0]) for info in infos)


def same_site_url(base_url: str, target: str) -> str:
    """Собирает адрес перехода и не даёт агенту уйти с тестируемого сайта."""
    url = urljoin(base_url + "/", target)
    if urlsplit(url).netloc != urlsplit(base_url).netloc or urlsplit(url).scheme not in (
        "http",
        "https",
    ):
        raise ActionError("Переходить можно только по страницам тестируемого сайта")
    return url


def _site_host(host: str) -> str:
    """Убирает www из хоста, чтобы www.shop.ru и shop.ru считались одним сайтом."""
    return host.lower().removeprefix("www.")


def is_same_site(base_url: str, url: str) -> bool:
    """Проверяет, что адрес относится к тестируемому сайту или его поддомену."""
    base = _site_host(urlsplit(base_url).hostname or "")
    host = _site_host(urlsplit(url).hostname or "")
    return bool(host) and (host == base or host.endswith("." + base))
