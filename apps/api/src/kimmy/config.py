from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KIMMY_", extra="ignore")
    database_url: SecretStr
    demo_user_id: str = Field(default="demo-user", min_length=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
