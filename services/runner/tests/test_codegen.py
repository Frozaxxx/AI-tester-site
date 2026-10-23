import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from app.application.codegen import generate_test
from app.domain.entities import Action, Job

RUN_ID = "1a2b3c4d-0000-0000-0000-000000000000"


def make_job(base_url: str) -> Job:
    """Создаёт задание прогона для тестов."""
    return Job(run_id=RUN_ID, owner_id="o", project_id="p", base_url=base_url)


def run_generated(code: str, tmp_path: Path) -> subprocess.CompletedProcess:
    """Запускает сгенерированный тест в отдельном процессе с настоящим браузером."""
    (tmp_path / "test_generated.py").write_text(code, encoding="utf-8")
    runner = textwrap.dedent(
        """
        import sys
        from playwright.sync_api import sync_playwright
        sys.path.insert(0, sys.argv[1])
        import test_generated
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            test_generated.test_run_1a2b3c4d(page)
            browser.close()
        """
    )
    return subprocess.run(
        [sys.executable, "-c", runner, str(tmp_path)], capture_output=True, text=True, timeout=60
    )


def test_code_is_valid_python_with_safe_literals() -> None:
    """Код компилируется, а значения от LLM попадают в него только как строковые литералы."""
    evil = "'); import os; os.system('rm -rf /'); ('"
    actions = [
        Action(name="goto", value="/"),
        Action(name="fill", locator="input[name=q]", value=evil),
        Action(name="press", value="Enter"),
        Action(name="expect_url", value="/search"),
        Action(name="rm", value="-rf"),
        Action(name="wait", value="100"),
    ]
    code = generate_test(make_job("https://shop.example.com/"), actions)
    compile(code, "test_generated.py", "exec")
    assert "BASE_URL = 'https://shop.example.com'" in code
    assert repr(evil) in code and "rm" not in code.replace(repr(evil), "")
    assert "page.keyboard.press('Enter')" in code


def test_generated_test_passes_on_clean_page(site_url: str, tmp_path: Path) -> None:
    """Тест по шагам на странице без ошибок проходит."""
    actions = [
        Action(name="goto", value="/"),
        Action(name="click", locator="role=button[name='В корзину']"),
        Action(name="expect_text", locator="#cart", value="Добавлено"),
    ]
    result = run_generated(generate_test(make_job(site_url), actions), tmp_path)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("path", ["/js-error", "/api-error", "/missing"])
def test_generated_test_reproduces_bug(site_url: str, tmp_path: Path, path: str) -> None:
    """Тест падает на странице с ошибкой, то есть воспроизводит найденный баг."""
    actions = [Action(name="goto", value=path), Action(name="wait", value="300")]
    result = run_generated(generate_test(make_job(site_url), actions), tmp_path)
    assert result.returncode != 0 and "AssertionError" in result.stderr
