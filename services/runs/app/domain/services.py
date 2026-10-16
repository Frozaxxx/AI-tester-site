import uuid
from datetime import datetime

from app.domain.entities import (
    Finding,
    FindingKind,
    GeneratedTest,
    Run,
    RunStatus,
    Step,
)
from app.domain.exceptions import InvalidRunStateError, RunNotFoundError, ValidationError

FINAL_STATUSES = frozenset(
    {RunStatus.PASSED, RunStatus.FAILED, RunStatus.ERROR, RunStatus.CANCELLED}
)
STEP_ACTIONS = frozenset(
    {"goto", "click", "fill", "press", "select", "check", "expect_text", "expect_url", "wait"}
)
FINDING_TITLE_MAX_LENGTH = 300


def create_run(owner_id: uuid.UUID, project_id: uuid.UUID, scenario_id: uuid.UUID | None) -> Run:
    """Создаёт прогон в очереди."""
    return Run(owner_id=owner_id, project_id=project_id, scenario_id=scenario_id)


def is_finished(run: Run) -> bool:
    """Проверяет, что прогон уже завершён и больше не изменится."""
    return run.status in FINAL_STATUSES


def ensure_owner(run: Run | None, owner_id: uuid.UUID) -> Run:
    """Возвращает прогон, только если он принадлежит пользователю, иначе считает его ненайденным."""
    if run is None or run.owner_id != owner_id:
        raise RunNotFoundError
    return run


def ensure_running(run: Run) -> None:
    """Запрещает записывать шаги и баги в прогон, который сейчас не идёт."""
    if run.status != RunStatus.RUNNING:
        raise InvalidRunStateError(f"Прогон не идёт, его статус {run.status}")


def start_run(run: Run, now: datetime) -> None:
    """Переводит прогон из очереди в работу."""
    if run.status != RunStatus.QUEUED:
        raise InvalidRunStateError(f"Запустить можно только прогон в очереди, а этот {run.status}")
    run.status = RunStatus.RUNNING
    run.started_at = now


def finish_run(run: Run, found_bugs: bool, now: datetime) -> None:
    """Завершает идущий прогон: с багами он упал, без багов прошёл."""
    ensure_running(run)
    run.status = RunStatus.FAILED if found_bugs else RunStatus.PASSED
    run.finished_at = now


def crash_run(run: Run, now: datetime) -> None:
    """Отмечает, что прогон сломался сам, например упал браузер или недоступна LLM."""
    ensure_running(run)
    run.status = RunStatus.ERROR
    run.finished_at = now


def cancel_run(run: Run, now: datetime) -> None:
    """Отменяет прогон, который ещё не завершён."""
    if is_finished(run):
        raise InvalidRunStateError(f"Прогон уже завершён со статусом {run.status}")
    run.status = RunStatus.CANCELLED
    run.finished_at = now


def add_tokens(run: Run, count: int) -> None:
    """Прибавляет потраченные на прогон токены LLM."""
    if count < 0:
        raise ValidationError("Число токенов не может быть отрицательным")
    run.tokens_used += count


def create_step(
    run: Run,
    index: int,
    action: str,
    ok: bool,
    locator: str | None = None,
    value: str | None = None,
    error: str | None = None,
) -> Step:
    """Записывает очередное действие агента в идущий прогон."""
    ensure_running(run)
    if index < 0:
        raise ValidationError("Номер шага не может быть отрицательным")
    if action not in STEP_ACTIONS:
        raise ValidationError(f"Неизвестное действие «{action}»")
    return Step(
        run_id=run.id,
        index=index,
        action=action,
        ok=ok,
        locator=locator,
        value=value,
        error=error,
    )


def create_finding(
    run: Run, kind: FindingKind, title: str, details: str = "", step_index: int | None = None
) -> Finding:
    """Записывает найденный баг в идущий прогон."""
    ensure_running(run)
    title = title.strip()
    if not title:
        raise ValidationError("У бага должен быть заголовок")
    if len(title) > FINDING_TITLE_MAX_LENGTH:
        raise ValidationError(
            f"Заголовок бага должен быть не длиннее {FINDING_TITLE_MAX_LENGTH} символов"
        )
    return Finding(run_id=run.id, kind=kind, title=title, details=details, step_index=step_index)


def create_generated_test(run: Run, code: str) -> GeneratedTest:
    """Сохраняет Playwright-тест, собранный из шагов завершённого прогона."""
    if run.status not in (RunStatus.PASSED, RunStatus.FAILED):
        raise InvalidRunStateError("Тест собирается только из успешно завершённого прогона")
    if not code.strip():
        raise ValidationError("Код теста не может быть пустым")
    return GeneratedTest(run_id=run.id, code=code)
