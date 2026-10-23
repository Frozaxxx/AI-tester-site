import uuid
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import Run, RunStatus
from app.infra.database.mappers import RunMapper
from app.infra.database.models import RunOrm


class SqlRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, run: Run) -> None:
        """Сохраняет новый прогон."""
        self._session.add(RunMapper.to_model(run))
        await self._session.flush()

    async def get(self, run_id: uuid.UUID, for_update: bool = False) -> Run | None:
        """Находит прогон по id и при необходимости блокирует его до конца транзакции."""
        query = select(RunOrm).where(RunOrm.id == run_id)
        if for_update:
            query = query.with_for_update()
        model = (await self._session.execute(query)).scalar_one_or_none()
        return RunMapper.from_model(model) if model else None

    async def save(self, run: Run) -> None:
        """Сохраняет изменения прогона."""
        await self._session.merge(RunMapper.to_model(run))
        await self._session.flush()

    async def list_by_project(self, owner_id: uuid.UUID, project_id: uuid.UUID) -> list[Run]:
        """Возвращает прогоны проекта пользователя, сначала новые."""
        result = await self._session.scalars(
            select(RunOrm)
            .where(RunOrm.owner_id == owner_id, RunOrm.project_id == project_id)
            .order_by(RunOrm.created_at.desc())
        )
        return [RunMapper.from_model(model) for model in result]

    async def count_active(self, owner_id: uuid.UUID) -> int:
        """Считает незавершённые прогоны пользователя, заранее блокируя его прогоны от гонки."""
        if self._session.bind.dialect.name == "postgresql":
            key = owner_id.int & 0x7FFF_FFFF_FFFF_FFFF
            await self._session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
        result = await self._session.scalar(
            select(func.count())
            .select_from(RunOrm)
            .where(
                RunOrm.owner_id == owner_id,
                RunOrm.status.in_([RunStatus.QUEUED, RunStatus.RUNNING]),
            )
        )
        return result or 0

    async def claim_next(self) -> Run | None:
        """Берёт самый старый прогон из очереди и блокирует его, пропуская занятые другими."""
        result = await self._session.execute(
            select(RunOrm)
            .where(RunOrm.status == RunStatus.QUEUED)
            .order_by(RunOrm.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        model = result.scalar_one_or_none()
        return RunMapper.from_model(model) if model else None

    async def list_stale(self, started_before: datetime) -> list[Run]:
        """Находит прогоны, которые идут дольше допустимого, и блокирует их для обновления."""
        result = await self._session.scalars(
            select(RunOrm)
            .where(RunOrm.status == RunStatus.RUNNING, RunOrm.started_at < started_before)
            .with_for_update(skip_locked=True)
        )
        return [RunMapper.from_model(model) for model in result]
