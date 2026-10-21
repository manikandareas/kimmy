"""Resolve citation markers exclusively against this run's tool artifacts."""

import re
from uuid import UUID

from kimmy.knowledge.schemas import Citation


def resolve_citations(content: str, received: dict[UUID, Citation]) -> list[Citation]:
    result: dict[UUID, Citation] = {}
    for marker in re.findall(r"\[SOP:([^\]]*)\]", content):
        try:
            chunk_id = UUID(marker)
        except ValueError as error:
            raise ValueError("Invalid SOP citation marker") from error
        if chunk_id not in received:
            raise ValueError("SOP citation was not retrieved during this run")
        result[chunk_id] = received[chunk_id]
    if content.count("[SOP:") != len(re.findall(r"\[SOP:([^\]]*)\]", content)):
        raise ValueError("Incomplete SOP citation marker")
    return list(result.values())
