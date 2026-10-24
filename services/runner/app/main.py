import asyncio
import logging

import grpc

from app.application.agent import LlmAgent
from app.application.worker import RunWorker
from app.config import settings
from app.infra.browser import SiteBrowser
from app.infra.clients.projects import ProjectsClient
from app.infra.clients.runs import RunsClient
from app.infra.llm import make_chat_model

logger = logging.getLogger("runner")


def _browser(base_url: str) -> SiteBrowser:
    """Создаёт браузер для сайта с настройкой доступа к внутренним адресам."""
    return SiteBrowser(base_url, allow_internal=settings.allow_internal_urls)


async def work() -> None:
    """Бесконечно берёт прогоны из очереди и выполняет их по одному."""
    async with (
        grpc.aio.insecure_channel(settings.runs_grpc_address) as runs_channel,
        grpc.aio.insecure_channel(settings.projects_grpc_address) as projects_channel,
    ):
        model = make_chat_model(settings)
        agent = LlmAgent(model) if model is not None else None
        worker = RunWorker(
            RunsClient(runs_channel), ProjectsClient(projects_channel), _browser, agent
        )
        logger.info("раннер ждёт прогоны, LLM: %s", settings.llm_provider)
        while True:
            try:
                worked = await worker.run_once()
            except grpc.aio.AioRpcError as exc:
                logger.warning("runs недоступен: %s", exc.code())
                worked = False
            if not worked:
                await asyncio.sleep(settings.poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(work())
