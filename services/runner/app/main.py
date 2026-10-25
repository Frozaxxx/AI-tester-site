import asyncio
import logging

import grpc

from app.application.agent import LlmAgent
from app.application.loop import WorkLoop
from app.application.worker import RunWorker
from app.config import settings
from app.infra.broker import make_broker
from app.infra.browser import SiteBrowser
from app.infra.clients.projects import ProjectsClient
from app.infra.clients.runs import RunsClient
from app.infra.llm import make_chat_model

logger = logging.getLogger("runner")


def _browser(base_url: str) -> SiteBrowser:
    """Создаёт браузер для сайта с настройкой доступа к внутренним адресам."""
    return SiteBrowser(base_url, allow_internal=settings.allow_internal_urls)


async def work() -> None:
    """Выполняет прогоны по событиям из RabbitMQ и подстраховывается редким опросом очереди."""
    async with (
        grpc.aio.insecure_channel(settings.runs_grpc_address) as runs_channel,
        grpc.aio.insecure_channel(settings.projects_grpc_address) as projects_channel,
    ):
        model = make_chat_model(settings)
        agent = LlmAgent(model) if model is not None else None
        worker = RunWorker(
            RunsClient(runs_channel), ProjectsClient(projects_channel), _browser, agent
        )
        loop = WorkLoop(worker, settings.poll_interval_seconds)
        broker = make_broker(settings.rabbitmq_url, loop)
        await broker.start()
        logger.info("раннер ждёт прогоны, LLM: %s", settings.llm_provider)
        try:
            await loop.run_forever()
        finally:
            await broker.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(work())
