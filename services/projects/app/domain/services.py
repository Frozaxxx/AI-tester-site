import ipaddress
import re
import socket
import uuid
from urllib.parse import urlsplit

from app.domain.entities import Project, Scenario
from app.domain.exceptions import ProjectNotFoundError, ValidationError

NAME_MAX_LENGTH = 200
URL_MAX_LENGTH = 2048
TITLE_MAX_LENGTH = 200
TEXT_MAX_LENGTH = 10_000

LINE_FORBIDDEN_RE = re.compile(r"[\x00-\x1f\x7f]")
TEXT_FORBIDDEN_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
URL_FORBIDDEN_RE = re.compile(r"[\x00-\x20\x7f]")


def _require_text(raw: str, field: str, max_length: int, multiline: bool = False) -> str:
    """Обрезает пробелы и проверяет длину строки и отсутствие служебных символов."""
    value = raw.strip()
    if not value:
        raise ValidationError(f"Поле «{field}» не может быть пустым")
    if len(value) > max_length:
        raise ValidationError(f"Поле «{field}» должно быть не длиннее {max_length} символов")
    forbidden = TEXT_FORBIDDEN_RE if multiline else LINE_FORBIDDEN_RE
    if forbidden.search(value):
        raise ValidationError(f"Поле «{field}» содержит недопустимые символы")
    return value


def _is_internal_host(host: str) -> bool:
    """Проверяет, что хост указывает на локальную или внутреннюю сеть, а не на сайт в интернете."""
    if host == "localhost" or host.endswith(".localhost"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        try:
            ip = ipaddress.ip_address(socket.inet_aton(host))
        except OSError:
            return False
    return not ip.is_global


def normalize_base_url(raw: str, allow_internal: bool = False) -> str:
    """Проверяет, что адрес сайта корректный, публичный и без логина с паролем."""
    url = raw.strip().rstrip("/")
    if len(url) > URL_MAX_LENGTH:
        raise ValidationError(f"Адрес сайта должен быть не длиннее {URL_MAX_LENGTH} символов")
    if URL_FORBIDDEN_RE.search(url):
        raise ValidationError("Адрес сайта не должен содержать пробелы и служебные символы")
    try:
        parts = urlsplit(url)
        host = parts.hostname
        _ = parts.port
    except ValueError:
        raise ValidationError("Некорректный адрес сайта") from None
    if parts.scheme not in ("http", "https") or not host:
        raise ValidationError("Адрес сайта должен начинаться с http:// или https://")
    if parts.username is not None or parts.password is not None:
        raise ValidationError("Адрес сайта не должен содержать логин и пароль")
    if not allow_internal and _is_internal_host(host):
        raise ValidationError("Нельзя тестировать локальные и внутренние адреса")
    return url


def create_project(
    owner_id: uuid.UUID, name: str, base_url: str, allow_internal: bool = False
) -> Project:
    """Создаёт проект с проверенным названием и адресом сайта."""
    return Project(
        owner_id=owner_id,
        name=_require_text(name, "название", NAME_MAX_LENGTH),
        base_url=normalize_base_url(base_url, allow_internal),
    )


def create_scenario(project: Project, title: str, text: str) -> Scenario:
    """Создаёт сценарий тестирования внутри проекта."""
    return Scenario(
        project_id=project.id,
        title=_require_text(title, "заголовок", TITLE_MAX_LENGTH),
        text=_require_text(text, "текст", TEXT_MAX_LENGTH, multiline=True),
    )


def ensure_owner(project: Project | None, owner_id: uuid.UUID) -> Project:
    """Возвращает проект, только если он принадлежит пользователю, иначе считает его ненайденным."""
    if project is None or project.owner_id != owner_id:
        raise ProjectNotFoundError
    return project
