import asyncio
import logging

from app.application.worker import RunWorker

logger = logging.getLogger("runner")


class WorkLoop:
    def __init__(self, worker: RunWorker, poll_interval: float) -> None:
        self._worker = worker
        self._poll_interval = poll_interval
        self._wake = asyncio.Event()

    def wake(self) -> None:
        """Будит раннер, когда из брокера пришло событие о новом прогоне."""
        self._wake.set()

    async def drain(self) -> None:
        """Выполняет прогоны из очереди один за другим, пока очередь не опустеет."""
        try:
            while await self._worker.run_once():
                pass
        except Exception:
            logger.exception("не удалось взять прогон из очереди, попробуем позже")

    async def run_forever(self) -> None:
        """Ждёт событие из брокера или истечение интервала опроса и разбирает очередь."""
        while True:
            await self.drain()
            try:
                await asyncio.wait_for(self._wake.wait(), self._poll_interval)
            except TimeoutError:
                pass
            self._wake.clear()
