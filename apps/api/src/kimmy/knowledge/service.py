import math
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from kimmy.config import Settings
from kimmy.errors import DomainError
from kimmy.knowledge.ingestion import read_documents
from kimmy.knowledge.repository import KnowledgeRepository
from kimmy.knowledge.schemas import (
    EmbeddingIdentity,
    IndexReceipt,
    SearchInput,
    SearchResult,
    SourceChunk,
)
from kimmy.llm import embedding_model


class KnowledgeService:
    def __init__(self, engine: AsyncEngine, settings: Settings):
        self.engine = engine
        self.settings = settings
        self.identity = EmbeddingIdentity(
            model="openai:" + settings.openai_embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    def validate_vectors(self, vectors: list[list[float]], count: int) -> None:
        if len(vectors) != count or any(
            len(v) != self.identity.dimensions
            or not all(math.isfinite(x) for x in v)
            or not any(v)
            for v in vectors
        ):
            raise ValueError("Embedding provider returned invalid vectors")

    async def index(self, directory: Path, *, rebuild: bool = False) -> IndexReceipt:
        documents = read_documents(directory)
        # One corpus lock and one transaction. A failure leaves the old active
        # corpus intact, including when an explicit model rebuild fails.
        async with AsyncSession(self.engine) as session, session.begin():
            repo = KnowledgeRepository(session)
            await repo.lock()
            previous = await repo.config()
            if previous and previous[0] != self.identity and not rebuild:
                raise ValueError(
                    "Embedding model/dimensions changed; use --rebuild explicitly"
                )
            changed = previous is None or previous[0] != self.identity or rebuild
            pending = []
            for doc in documents:
                existing = await repo.document(doc, self.identity)
                if existing and existing[1] != doc.content_hash:
                    raise ValueError(
                        f"{doc.slug}: content changed without a new version"
                    )
                if not existing or not existing[2] or rebuild:
                    pending.append((doc, existing is None))
            changed = changed or bool(pending)
            if changed:
                vectors_by_slug: dict[str, list[list[float]]] = {}
                missing = [doc for doc, needs_embedding in pending if needs_embedding]
                if missing:
                    async with embedding_model(self.settings) as model:
                        for doc in missing:
                            vectors = await model.aembed_documents(
                                [
                                    f"{doc.title}\n{s.title}\n{s.content}"
                                    for s in doc.sections
                                ]
                            )
                            self.validate_vectors(vectors, len(doc.sections))
                            vectors_by_slug[doc.slug] = vectors
                if rebuild or (previous and previous[0] != self.identity):
                    await repo.deactivate_all()
                for doc, _ in pending:
                    await repo.activate(
                        doc, self.identity, vectors_by_slug.get(doc.slug)
                    )
                generation = previous[1] + 1 if previous else 1
                await repo.set_config(self.identity, generation)
            else:
                assert previous is not None
                generation = previous[1]
            count, chunks = await repo.counts()
            return IndexReceipt(
                documents=count,
                chunks=chunks,
                changed=changed,
                generation=generation,
                identity=self.identity,
            )

    async def search(self, request: SearchInput) -> SearchResult:
        async with embedding_model(self.settings) as model:
            vector = await model.aembed_query(request.query)
        self.validate_vectors([vector], 1)
        async with AsyncSession(self.engine) as session, session.begin():
            await session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            )
            repo = KnowledgeRepository(session)
            config = await repo.config()
            if config is None:
                raise DomainError(
                    409, "KNOWLEDGE_NOT_INDEXED", "Index SOP documents first"
                )
            if config[0] != self.identity:
                raise DomainError(
                    409,
                    "EMBEDDING_MISMATCH",
                    "Rebuild with the configured embedding model/dimensions",
                )
            return SearchResult(
                citations=await repo.search(vector, self.identity, request.limit)
            )

    async def source(self, chunk_id: UUID) -> SourceChunk:
        async with AsyncSession(self.engine) as session:
            source = await KnowledgeRepository(session).source(chunk_id)
            if source is None:
                raise DomainError(404, "SOURCE_NOT_FOUND", "SOP source not found")
            return source
