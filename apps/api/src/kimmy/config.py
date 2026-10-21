from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KIMMY_", extra="ignore")
    database_url: SecretStr
    demo_user_id: str = Field(default="demo-user", min_length=1, max_length=200)
    chat_provider: Literal["openai", "openrouter"] = "openai"
    openai_chat_model: str = Field(default="gpt-6-luna", min_length=1)
    openrouter_chat_model: str = Field(
        default="deepseek/deepseek-v4.1-flash-1017", min_length=1
    )
    openai_embedding_model: str = Field(default="text-embedding-3-small", min_length=1)
    embedding_dimensions: int = Field(default=1536, ge=1, le=3072)
    model_timeout_seconds: int = Field(default=60, ge=1, le=300)
    agent_timeout_seconds: int = Field(default=180, ge=1, le=900)
    agent_max_tool_calls: int = Field(default=8, ge=1, le=32)
    agent_max_model_calls: int = Field(default=10, ge=1, le=40)
    agent_max_output_tokens: int = Field(default=4096, ge=128, le=16384)
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "KIMMY_OPENAI_API_KEY"),
    )
    openrouter_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENROUTER_API_KEY", "KIMMY_OPENROUTER_API_KEY"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
