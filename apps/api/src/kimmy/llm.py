from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_openrouter import ChatOpenRouter
from openrouter import OpenRouter
from pydantic import SecretStr

from kimmy.config import Settings


class ModelConfigurationError(ValueError):
    pass


def require_key(key: SecretStr | None) -> SecretStr:
    if key is None or not key.get_secret_value().strip():
        raise ModelConfigurationError("Selected provider requires an API key")
    return key


@asynccontextmanager
async def chat_model(settings: Settings) -> AsyncIterator[BaseChatModel]:
    # Own both transports explicitly. No hidden retries: the run deadline is the
    # outer bound and explicit retry/recovery belongs to KM-012.
    with httpx.Client(timeout=settings.model_timeout_seconds) as sync_client:
        async with httpx.AsyncClient(
            timeout=settings.model_timeout_seconds
        ) as async_client:
            if settings.chat_provider == "openai":
                yield ChatOpenAI(
                    model=settings.openai_chat_model,
                    api_key=require_key(settings.openai_api_key),
                    timeout=settings.model_timeout_seconds,
                    max_retries=0,
                    max_completion_tokens=settings.agent_max_output_tokens,
                    streaming=True,
                    http_client=sync_client,
                    http_async_client=async_client,
                )
            else:
                key = require_key(settings.openrouter_api_key)
                async with OpenRouter(
                    api_key=key.get_secret_value(),
                    client=sync_client,
                    async_client=async_client,
                    timeout_ms=settings.model_timeout_seconds * 1000,
                    retry_config=None,
                ) as client:
                    yield ChatOpenRouter(
                        model_name=settings.openrouter_chat_model,
                        api_key=key,
                        client=client,
                        timeout=settings.model_timeout_seconds * 1000,
                        max_retries=0,
                        max_tokens=settings.agent_max_output_tokens,
                        streaming=True,
                    )


@asynccontextmanager
async def embedding_model(settings: Settings) -> AsyncIterator[OpenAIEmbeddings]:
    # Embeddings have their own model/dimension contract and are never initialized
    # by chat. SOP ingestion will use this factory in KM-007.
    with httpx.Client(timeout=settings.model_timeout_seconds) as sync_client:
        async with httpx.AsyncClient(
            timeout=settings.model_timeout_seconds
        ) as async_client:
            yield OpenAIEmbeddings(
                model=settings.openai_embedding_model,
                dimensions=settings.embedding_dimensions,
                openai_api_key=require_key(settings.openai_api_key),
                request_timeout=settings.model_timeout_seconds,
                max_retries=0,
                http_client=sync_client,
                http_async_client=async_client,
            )
