import uuid
from datetime import UTC, datetime

import pytest

from app.domain.entities import FindingKind, Run, RunStatus
from app.domain.exceptions import InvalidRunStateError, RunNotFoundError, ValidationError
from app.domain.services import (
    add_tokens,
    cancel_run,
    crash_run,
    create_finding,
    create_generated_test,
    create_run,
    create_step,
    ensure_owner,
    finish_run,
    parse_finding_kind,
    start_run,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def new_run() -> Run:
    """Создаёт прогон в очереди для тестов."""
    return create_run(uuid.uuid4(), uuid.uuid4(), None)


def running_run() -> Run:
    """Создаёт уже запущенный прогон для тестов."""
    run = new_run()
    start_run(run, NOW)
    return run


def test_run_lifecycle() -> None:
    """Прогон идёт из очереди в работу и завершается с багами или без."""
    run = new_run()
    assert run.status == RunStatus.QUEUED
    start_run(run, NOW)
    assert (run.status, run.started_at) == (RunStatus.RUNNING, NOW)
    finish_run(run, found_bugs=True, now=NOW)
    assert (run.status, run.finished_at) == (RunStatus.FAILED, NOW)

    clean = running_run()
    finish_run(clean, found_bugs=False, now=NOW)
    assert clean.status == RunStatus.PASSED


def test_wrong_transitions_are_rejected() -> None:
    """Нельзя запустить прогон дважды, завершить незапущенный или отменить завершённый."""
    run = running_run()
    with pytest.raises(InvalidRunStateError):
        start_run(run, NOW)
    with pytest.raises(InvalidRunStateError):
        finish_run(new_run(), found_bugs=False, now=NOW)
    crash_run(run, NOW)
    assert run.status == RunStatus.ERROR
    with pytest.raises(InvalidRunStateError):
        cancel_run(run, NOW)


def test_cancel_queued_and_running() -> None:
    """Отменить можно прогон и в очереди, и уже идущий."""
    for run in (new_run(), running_run()):
        cancel_run(run, NOW)
        assert run.status == RunStatus.CANCELLED


def test_steps_and_findings_only_in_running_run() -> None:
    """Шаги и баги записываются только в идущий прогон и проверяются."""
    run = running_run()
    step = create_step(run, 0, "click", ok=True, locator='get_by_role("button")')
    assert step.run_id == run.id
    finding = create_finding(run, FindingKind.JS_ERROR, "  Ошибка в консоли  ")
    assert finding.title == "Ошибка в консоли"

    with pytest.raises(ValidationError):
        create_step(run, 1, "rm -rf", ok=True)
    with pytest.raises(ValidationError):
        create_step(run, -1, "click", ok=True)
    with pytest.raises(ValidationError):
        create_finding(run, FindingKind.ASSERTION, "  ")
    with pytest.raises(InvalidRunStateError):
        create_step(new_run(), 0, "click", ok=True)


def test_generated_test_needs_finished_run() -> None:
    """Тест собирается только из завершённого прогона и не бывает пустым."""
    run = running_run()
    with pytest.raises(InvalidRunStateError):
        create_generated_test(run, "test code")
    finish_run(run, found_bugs=True, now=NOW)
    assert create_generated_test(run, "def test_cart(page): ...").run_id == run.id
    with pytest.raises(ValidationError):
        create_generated_test(run, "   ")


def test_tokens_and_owner() -> None:
    """Токены только прибавляются, а чужой прогон выглядит ненайденным."""
    run = new_run()
    add_tokens(run, 120)
    assert run.tokens_used == 120
    with pytest.raises(ValidationError):
        add_tokens(run, -1)
    assert ensure_owner(run, run.owner_id) is run
    with pytest.raises(RunNotFoundError):
        ensure_owner(run, uuid.uuid4())
    with pytest.raises(RunNotFoundError):
        ensure_owner(None, run.owner_id)


def test_runner_text_is_cleaned() -> None:
    """Нулевые байты убираются, а слишком длинные тексты от браузера и LLM обрезаются."""
    run = running_run()
    step = create_step(run, 0, "click", ok=False, error="bad\x00byte" + "x" * 10_000)
    assert "\x00" not in step.error and len(step.error) == 5_000
    finding = create_finding(run, FindingKind.LLM_JUDGE, "Цена\nне совпадает" + "!" * 500)
    assert finding.title.startswith("Цена не совпадает") and len(finding.title) == 300


@pytest.mark.parametrize("index", [-1, 10_001, 2**31])
def test_step_index_limits(index: int) -> None:
    """Номер шага вне допустимого диапазона не принимается ни у шага, ни у бага."""
    run = running_run()
    with pytest.raises(ValidationError):
        create_step(run, index, "click", ok=True)
    with pytest.raises(ValidationError):
        create_finding(run, FindingKind.JS_ERROR, "Баг", step_index=index)


def test_token_limits() -> None:
    """Слишком большое число токенов не ломает счётчик в базе."""
    run = new_run()
    with pytest.raises(ValidationError):
        add_tokens(run, 3_000_000_000)
    run.tokens_used = 1_999_999_999
    with pytest.raises(ValidationError):
        add_tokens(run, 10)


def test_unknown_finding_kind() -> None:
    """Строка с неизвестным типом бага превращается в ошибку валидации."""
    assert parse_finding_kind("js_error") == FindingKind.JS_ERROR
    with pytest.raises(ValidationError):
        parse_finding_kind("nonsense")


def test_generated_test_rejects_null_byte() -> None:
    """Код теста с нулевым байтом не сохраняется."""
    run = running_run()
    finish_run(run, found_bugs=False, now=NOW)
    with pytest.raises(ValidationError):
        create_generated_test(run, "def test(page):\x00 ...")
