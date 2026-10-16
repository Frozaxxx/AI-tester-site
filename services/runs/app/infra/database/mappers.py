from datetime import UTC, datetime

from app.domain.entities import Finding, GeneratedTest, Run, Step
from app.infra.database.models import FindingOrm, GeneratedTestOrm, RunOrm, StepOrm


def _utc(value: datetime | None) -> datetime | None:
    """Добавляет к дате часовой пояс UTC, если его нет."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class RunMapper:
    @staticmethod
    def from_model(model: RunOrm) -> Run:
        """Собирает доменный прогон из записи в базе."""
        return Run(
            id=model.id,
            owner_id=model.owner_id,
            project_id=model.project_id,
            scenario_id=model.scenario_id,
            status=model.status,
            tokens_used=model.tokens_used,
            created_at=_utc(model.created_at),
            started_at=_utc(model.started_at),
            finished_at=_utc(model.finished_at),
        )

    @staticmethod
    def to_model(entity: Run) -> RunOrm:
        """Готовит прогон к сохранению в базу."""
        return RunOrm(
            id=entity.id,
            owner_id=entity.owner_id,
            project_id=entity.project_id,
            scenario_id=entity.scenario_id,
            status=entity.status,
            tokens_used=entity.tokens_used,
            created_at=entity.created_at,
            started_at=entity.started_at,
            finished_at=entity.finished_at,
        )


class StepMapper:
    @staticmethod
    def from_model(model: StepOrm) -> Step:
        """Собирает доменный шаг из записи в базе."""
        return Step(
            id=model.id,
            run_id=model.run_id,
            index=model.index,
            action=model.action,
            ok=model.ok,
            locator=model.locator,
            value=model.value,
            error=model.error,
            screenshot_key=model.screenshot_key,
            created_at=_utc(model.created_at),
        )

    @staticmethod
    def to_model(entity: Step) -> StepOrm:
        """Готовит шаг к сохранению в базу."""
        return StepOrm(
            id=entity.id,
            run_id=entity.run_id,
            index=entity.index,
            action=entity.action,
            ok=entity.ok,
            locator=entity.locator,
            value=entity.value,
            error=entity.error,
            screenshot_key=entity.screenshot_key,
            created_at=entity.created_at,
        )


class FindingMapper:
    @staticmethod
    def from_model(model: FindingOrm) -> Finding:
        """Собирает доменный баг из записи в базе."""
        return Finding(
            id=model.id,
            run_id=model.run_id,
            kind=model.kind,
            title=model.title,
            details=model.details,
            step_index=model.step_index,
            reproduced=model.reproduced,
            created_at=_utc(model.created_at),
        )

    @staticmethod
    def to_model(entity: Finding) -> FindingOrm:
        """Готовит баг к сохранению в базу."""
        return FindingOrm(
            id=entity.id,
            run_id=entity.run_id,
            kind=entity.kind,
            title=entity.title,
            details=entity.details,
            step_index=entity.step_index,
            reproduced=entity.reproduced,
            created_at=entity.created_at,
        )


class GeneratedTestMapper:
    @staticmethod
    def from_model(model: GeneratedTestOrm) -> GeneratedTest:
        """Собирает доменный сгенерированный тест из записи в базе."""
        return GeneratedTest(
            id=model.id,
            run_id=model.run_id,
            code=model.code,
            verified=model.verified,
            created_at=_utc(model.created_at),
        )

    @staticmethod
    def to_model(entity: GeneratedTest) -> GeneratedTestOrm:
        """Готовит сгенерированный тест к сохранению в базу."""
        return GeneratedTestOrm(
            id=entity.id,
            run_id=entity.run_id,
            code=entity.code,
            verified=entity.verified,
            created_at=entity.created_at,
        )
