from langchain_core.language_models import BaseChatModel

from app.config import Settings


def make_chat_model(settings: Settings) -> BaseChatModel | None:
    """Создаёт LLM выбранного провайдера, а без провайдера возвращает None для режима без LLM."""
    match settings.llm_provider:
        case "gigachat":
            from langchain_gigachat.chat_models import GigaChat

            return GigaChat(
                credentials=settings.gigachat_credentials,
                scope=settings.gigachat_scope,
                model=settings.gigachat_model,
                ca_bundle_file=settings.gigachat_ca_bundle_file,
                timeout=60,
            )
        case "openrouter":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key,
                model=settings.openrouter_model,
                timeout=60,
            )
        case "none":
            return None
    raise ValueError(f"Неизвестный провайдер LLM: {settings.llm_provider}")
