import asyncio

from faststream.rabbit import TestRabbitBroker

from app.application.loop import WorkLoop
from app.infra.broker import RUN_CREATED_QUEUE, make_broker


class CountingWorker:
    def __init__(self, queue: int = 0, fail: bool = False) -> None:
        self.queue = queue
        self.fail = fail
        self.done = 0

    async def run_once(self) -> bool:
        """Выполняет один прогон из очереди, если он есть."""
        if self.fail:
            raise ConnectionError("runs недоступен")
        if self.queue == 0:
            return False
        self.queue -= 1
        self.done += 1
        return True


async def test_drain_runs_whole_queue() -> None:
    """Раннер разбирает очередь целиком за один заход."""
    worker = CountingWorker(queue=3)
    await WorkLoop(worker, poll_interval=60).drain()
    assert worker.done == 3 and worker.queue == 0


async def test_drain_survives_errors() -> None:
    """Если runs недоступен, цикл не падает, а ждёт следующей попытки."""
    await WorkLoop(CountingWorker(fail=True), poll_interval=60).drain()


async def test_event_wakes_loop_before_poll_interval() -> None:
    """Событие из брокера будит раннер сразу, не дожидаясь интервала опроса."""
    worker = CountingWorker()
    loop = WorkLoop(worker, poll_interval=60)
    task = asyncio.create_task(loop.run_forever())
    await asyncio.sleep(0.05)
    worker.queue = 1
    loop.wake()
    await asyncio.sleep(0.05)
    task.cancel()
    assert worker.done == 1


async def test_broker_message_wakes_loop() -> None:
    """Сообщение о новом прогоне в очереди RabbitMQ будит цикл раннера."""
    loop = WorkLoop(CountingWorker(), poll_interval=60)
    broker = make_broker("amqp://guest:guest@localhost:5672/", loop)
    async with TestRabbitBroker(broker) as test_broker:
        await test_broker.publish({"run_id": "r1"}, queue=RUN_CREATED_QUEUE)
    assert loop._wake.is_set()
