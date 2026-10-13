import uuid

import pytest

from app.domain.exceptions import ProjectNotFoundError, ValidationError
from app.domain.services import create_project, create_scenario, ensure_owner, normalize_base_url


def test_base_url_is_normalized() -> None:
    """Пробелы и слэш в конце адреса убираются."""
    assert normalize_base_url("  https://shop.example.com/ ") == "https://shop.example.com"


@pytest.mark.parametrize(
    "url", ["", "shop.example.com", "ftp://shop.example.com", "javascript:alert(1)", "http://"]
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
