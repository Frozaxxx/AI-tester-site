import uuid

import pytest

from app.domain.exceptions import ProjectNotFoundError, ValidationError
from app.domain.services import create_project, create_scenario, ensure_owner, normalize_base_url


def test_base_url_is_normalized() -> None:
    """Пробелы и слэш в конце адреса убираются."""
    assert normalize_base_url("  https://shop.example.com/ ") == "https://shop.example.com"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "shop.example.com",
        "ftp://shop.example.com",
        "javascript:alert(1)",
        "http://",
        "http://[::1",
        "http://a.com:99999",
        "http://a.com:abc",
        "http://user:pass@a.com",
        "http://a.com/\x00",
        "http://a .com",
    ],
)
def test_bad_base_url_is_rejected(url: str) -> None:
    """Адрес без http/https или без хоста не принимается."""
    with pytest.raises(ValidationError):
        normalize_base_url(url)


def test_too_long_base_url_is_rejected() -> None:
    """Слишком длинный адрес не принимается."""
    with pytest.raises(ValidationError):
        normalize_base_url("https://a.com/" + "x" * 2048)


@pytest.mark.parametrize("name", ["", "   ", "x" * 201])
def test_bad_project_name_is_rejected(name: str) -> None:
    """Пустое или слишком длинное название проекта не принимается."""
    with pytest.raises(ValidationError):
        create_project(uuid.uuid4(), name, "https://shop.example.com")


def test_scenario_belongs_to_project() -> None:
    """Сценарий привязывается к своему проекту, а пробелы в полях обрезаются."""
    project = create_project(uuid.uuid4(), " Магазин ", "https://shop.example.com")
    scenario = create_scenario(project, " Корзина ", " Добавь товар в корзину ")
    assert project.name == "Магазин"
    assert scenario.project_id == project.id
    assert (scenario.title, scenario.text) == ("Корзина", "Добавь товар в корзину")


def test_empty_scenario_text_is_rejected() -> None:
    """Сценарий без текста не принимается."""
    project = create_project(uuid.uuid4(), "Магазин", "https://shop.example.com")
    with pytest.raises(ValidationError):
        create_scenario(project, "Корзина", "  ")


def test_foreign_project_looks_not_found() -> None:
    """Чужой или отсутствующий проект выглядит как ненайденный."""
    project = create_project(uuid.uuid4(), "Магазин", "https://shop.example.com")
    assert ensure_owner(project, project.owner_id) is project
    with pytest.raises(ProjectNotFoundError):
        ensure_owner(project, uuid.uuid4())
    with pytest.raises(ProjectNotFoundError):
        ensure_owner(None, project.owner_id)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000",
        "http://app.localhost",
        "http://127.0.0.1",
        "http://2130706433",
        "http://127.1",
        "http://10.0.0.5",
        "http://192.168.1.1",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]:8000",
        "http://[::ffff:127.0.0.1]",
        "http://0.0.0.0",
    ],
)
def test_internal_url_is_rejected_by_default(url: str) -> None:
    """Локальные и внутренние адреса запрещены, чтобы агента нельзя было натравить на нашу сеть."""
    with pytest.raises(ValidationError):
        normalize_base_url(url)


def test_internal_url_is_allowed_when_enabled() -> None:
    """Для локальной разработки внутренние адреса можно разрешить настройкой."""
    assert normalize_base_url("http://127.0.0.1:8001/", allow_internal=True) == (
        "http://127.0.0.1:8001"
    )


@pytest.mark.parametrize("name", ["a\x00b", "a\nb", "a\x1bb"])
def test_control_chars_in_name_are_rejected(name: str) -> None:
    """Служебные символы в названии не принимаются, иначе база упадёт на нулевом байте."""
    with pytest.raises(ValidationError):
        create_project(uuid.uuid4(), name, "https://shop.example.com")


def test_scenario_text_keeps_line_breaks_but_rejects_null() -> None:
    """В тексте сценария переносы строк разрешены, а нулевой байт нет."""
    project = create_project(uuid.uuid4(), "Магазин", "https://shop.example.com")
    assert create_scenario(project, "Шаги", "1. Открой\n2. Купи").text == "1. Открой\n2. Купи"
    with pytest.raises(ValidationError):
        create_scenario(project, "Шаги", "a\x00b")
