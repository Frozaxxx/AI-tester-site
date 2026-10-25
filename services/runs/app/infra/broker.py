from faststream.rabbit import RabbitBroker, RabbitQueue

RUN_CREATED_QUEUE = RabbitQueue("runs.created", durable=True)


class RabbitRunEvents:
    def __init__(self, broker: RabbitBroker) -> None:
        self._broker = broker

    async def run_created(self, run_id: str) -> None:
        """Публикует в RabbitMQ событие о новом прогоне, чтобы раннер взял его сразу."""
        await self._broker.publish({"run_id": run_id}, queue=RUN_CREATED_QUEUE, persist=True)
