from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel

from kimmy.config import Settings, get_settings


class DemoIdentity(BaseModel):
    user_id: str


def get_demo_identity(
    settings: Annotated[Settings, Depends(get_settings)],
) -> DemoIdentity:
    """Server-owned identity; client headers and payloads cannot override it."""
    return DemoIdentity(user_id=settings.demo_user_id)
