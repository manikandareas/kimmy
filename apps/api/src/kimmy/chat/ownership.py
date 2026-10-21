from datetime import UTC, datetime
from uuid import UUID

from kimmy.chat.models import Run
from kimmy.errors import DomainError


def require_owner(run: Run | None, token: UUID | None) -> None:
    if (
        run is None
        or token is None
        or run.owner_token != token
        or run.status != "running"
        or run.lease_until is None
        or run.lease_until <= datetime.now(UTC)
    ):
        raise DomainError(409, "RUN_OWNERSHIP_LOST", "Run ownership is no longer valid")
