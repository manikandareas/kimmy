from typing import Annotated

from pydantic import AfterValidator, Field


def validate_bigint(value: str) -> str:
    if int(value) > 9223372036854775807:
        raise ValueError("ID exceeds PostgreSQL bigint range")
    return value


FleetId = Annotated[
    str,
    Field(
        pattern=r"^[1-9][0-9]{0,18}$",
        description="Positive PostgreSQL bigint as a decimal string",
    ),
    AfterValidator(validate_bigint),
]
