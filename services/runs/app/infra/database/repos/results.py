import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Finding, GeneratedTest, Step
from app.domain.exceptions import ValidationError
from app.infra.database.mappers import FindingMapper, GeneratedTestMapper, StepMapper
from app.infra.database.models import FindingOrm, GeneratedTestOrm, StepOrm


class SqlStepRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, step: Step) -> None:
        """Сохраняет шаг прогона, а повтор номера шага считает ошибкой."""
        self._session.add(StepMapper.to_model(step))
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise ValidationError(f"Шаг №{step.index} уже записан") from None

    async def list_by_run(self, run_id: uuid.UUID) -> list[Step]:
        """Возвращает шаги прогона по порядку."""
        result = await self._session.scalars(
            select(StepOrm).where(StepOrm.run_id == run_id).order_by(StepOrm.index)
        )
        return [StepMapper.from_model(model) for model in result]


class SqlFindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, finding: Finding) -> None:
        """Сохраняет найденный баг."""
        self._session.add(FindingMapper.to_model(finding))
        await self._session.flush()

    async def list_by_run(self, run_id: uuid.UUID) -> list[Finding]:
        """Возвращает баги прогона в порядке нахождения."""
        result = await self._session.scalars(
            select(FindingOrm).where(FindingOrm.run_id == run_id).order_by(FindingOrm.created_at)
        )
        return [FindingMapper.from_model(model) for model in result]


class SqlGeneratedTestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, test: GeneratedTest) -> None:
        """Сохраняет сгенерированный тест прогона или обновляет его."""
        await self._session.merge(GeneratedTestMapper.to_model(test))
        await self._session.flush()

    async def get_by_run(self, run_id: uuid.UUID) -> GeneratedTest | None:
        """Находит сгенерированный тест прогона."""
        result = await self._session.execute(
            select(GeneratedTestOrm).where(GeneratedTestOrm.run_id == run_id)
        )
        model = result.scalar_one_or_none()
        return GeneratedTestMapper.from_model(model) if model else None
