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
