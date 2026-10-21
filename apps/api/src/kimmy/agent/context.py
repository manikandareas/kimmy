from dataclasses import dataclass
from uuid import UUID


@dataclass
class AgentContext:
    user_id: str
    thread_id: UUID
    run_id: UUID
    source_message_id: UUID
    memory_generation: int = 0
    reset_history: bool = False
