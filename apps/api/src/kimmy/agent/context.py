from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AgentContext:
    user_id: str
    thread_id: UUID
    run_id: UUID
    source_message_id: UUID
