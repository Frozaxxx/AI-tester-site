import uuid
from urllib.parse import urlsplit

from app.domain.entities import Project, Scenario
from app.domain.exceptions import ProjectNotFoundError, ValidationError

NAME_MAX_LENGTH = 200
URL_MAX_LENGTH = 2048
TITLE_MAX_LENGTH = 200
TEXT_MAX_LENGTH = 10_000


def _require_text(raw: str, field: str, max_length: int) -> str:
    """Обрезает пробелы и проверяет, что строка не пустая и не слишком длинная."""
    value = raw.strip()
    if not value:
        raise ValidationError(f"Поле «{field}» не может быть пустым")
    if len(value) > max_length:
        raise ValidationError(f"Поле «{field}» должно быть не длиннее {max_length} символов")
    return value


def normalize_base_url(raw: str) -> str:
    """Проверяет, что адрес сайта начинается с http или https и содержит хост."""
    url = raw.strip().rstrip("/")
    if len(url) > URL_MAX_LENGTH:
        raise ValidationError(f"Адрес сайта должен быть не длиннее {URL_MAX_LENGTH} символов")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValidationError("Адрес сайта должен начинаться с http:// или https://")
    return url


def create_project(owner_id: uuid.UUID, name: str, base_url: str) -> Project:
    """Создаёт проект с проверенным названием и адресом сайта."""
    return Project(
        owner_id=owner_id,
        name=_require_text(name, "название", NAME_MAX_LENGTH),
        base_url=normalize_base_url(base_url),
    )


def create_scenario(project: Project, title: str, text: str) -> Scenario:
    """Создаёт сценарий тестирования внутри проекта."""
    return Scenario(
        project_id=project.id,
        title=_require_text(title, "заголовок", TITLE_MAX_LENGTH),
        text=_require_text(text, "текст", TEXT_MAX_LENGTH),
    )


def ensure_owner(project: Project | None, owner_id: uuid.UUID) -> Project:
    """Возвращает проект, только если он принадлежит пользователю, иначе считает его ненайденным."""
    if project is None or project.owner_id != owner_id:
        raise ProjectNotFoundError
    return project
