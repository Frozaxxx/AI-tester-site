from faststream.rabbit import RabbitBroker, RabbitQueue

from app.application.loop import WorkLoop

RUN_CREATED_QUEUE = RabbitQueue("runs.created", durable=True)


def make_broker(url: str, loop: WorkLoop) -> RabbitBroker:
    """Создаёт брокер, который будит раннер при каждом событии о новом прогоне."""
    broker = RabbitBroker(url)

    @broker.subscriber(RUN_CREATED_QUEUE)
    async def on_run_created(message: dict) -> None:
        """Получает событие о новом прогоне и будит цикл раннера."""
        loop.wake()

    return broker
