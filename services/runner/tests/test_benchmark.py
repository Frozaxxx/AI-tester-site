import pytest

from app.benchmark import KNOWN_BUGS, Report, match
from app.domain.entities import PageProblem, ProblemKind


@pytest.mark.parametrize(
    ("kind", "title", "bug_id"),
    [
        (ProblemKind.HTTP_ERROR, "404 на http://127.0.0.1:8001/delivery", "broken_link"),
        (ProblemKind.JS_ERROR, "Ошибка JavaScript: addToFavorites is not defined", "favorites_js"),
        (ProblemKind.HTTP_ERROR, "500 на http://127.0.0.1:8001/search?q=", "search_500"),
        (ProblemKind.LLM_JUDGE, "Итоговая сумма не учитывает количество", "cart_total"),
        (ProblemKind.LLM_JUDGE, "Товар повторяется на второй странице", "pagination"),
        (ProblemKind.LLM_JUDGE, "Заказ оформляется с пустыми полями", "checkout_validation"),
        (ProblemKind.LLM_JUDGE, "Кнопка слишком маленькая", None),
        (ProblemKind.JS_ERROR, "Ошибка в консоли: что-то другое", None),
    ],
)
def test_match(kind: ProblemKind, title: str, bug_id: str | None) -> None:
    """Найденная проблема сопоставляется с известным багом по типу и ключевым словам."""
    assert match(PageProblem(kind=kind, title=title)) == bug_id


def test_report_summary() -> None:
    """Отчёт считает найденные баги один раз и отдельно ложные срабатывания."""
    report = Report()
    for title in ("404 на /delivery", "404 на /delivery?x=1"):
        report.add(PageProblem(kind=ProblemKind.HTTP_ERROR, title=title))
    report.add(PageProblem(kind=ProblemKind.LLM_JUDGE, title="Странный шрифт"))
    report.tokens = 1200
    text = report.summary()
    assert f"Найдено багов: 1 из {len(KNOWN_BUGS)}" in text
    assert "[x] broken_link" in text and "[ ] cart_total" in text
    assert "Ложных срабатываний: 1" in text and "Странный шрифт" in text
