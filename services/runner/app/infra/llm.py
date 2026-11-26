from langchain_core.language_models import BaseChatModel

from app.config import Settings


def make_chat_model(settings: Settings) -> BaseChatModel:
    """Создаёт обязательную для прогона LLM выбранного провайдера."""
    match settings.llm_provider:
        case "gigachat":
            if not settings.gigachat_credentials or settings.gigachat_credentials == "change-me":
                raise ValueError("Для GigaChat задайте RUNNER_GIGACHAT_CREDENTIALS")
            from langchain_gigachat.chat_models import GigaChat

            return GigaChat(
                credentials=settings.gigachat_credentials,
                scope=settings.gigachat_scope,
                model=settings.gigachat_model,
                ca_bundle_file=settings.gigachat_ca_bundle_file,
                timeout=60,
            )
        case "openrouter":
            if not settings.openrouter_api_key:
                raise ValueError("Для OpenRouter задайте RUNNER_OPENROUTER_API_KEY")
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
                timeout=60,
            )
    raise ValueError(f"Неизвестный провайдер LLM: {settings.llm_provider}")
