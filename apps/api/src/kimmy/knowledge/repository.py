import json
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from kimmy.knowledge.schemas import Citation, Document, EmbeddingIdentity


class KnowledgeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def lock(self) -> None:
        await self.session.execute(text("SELECT pg_advisory_xact_lock(736196007)"))

    async def config(self) -> tuple[EmbeddingIdentity, int] | None:
        row = (
            (
                await self.session.execute(
                    text(
                        "SELECT model, dimensions, generation "
                        "FROM knowledge_config WHERE id=1"
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return EmbeddingIdentity(model=row["model"], dimensions=row["dimensions"]), row[
            "generation"
        ]

    async def document(
        self, doc: Document, identity: EmbeddingIdentity
    ) -> tuple[UUID, str, bool] | None:
        row = (
            await self.session.execute(
                text("""SELECT id, content_hash, active FROM knowledge_documents
            WHERE slug=:slug AND version=:version
            AND model=:model AND dimensions=:dimensions"""),
                {"slug": doc.slug, "version": doc.version, **identity.model_dump()},
            )
        ).one_or_none()
        return (row[0], row[1], row[2]) if row else None

    async def activate(
        self,
        doc: Document,
        identity: EmbeddingIdentity,
        vectors: list[list[float]] | None,
    ) -> None:
        existing = await self.document(doc, identity)
        await self.session.execute(
            text(
                "UPDATE knowledge_documents SET active=false "
                "WHERE slug=:slug AND active"
            ),
            {"slug": doc.slug},
        )
        if existing:
            await self.session.execute(
                text("UPDATE knowledge_documents SET active=true WHERE id=:id"),
                {"id": existing[0]},
            )
            return
        document_id = uuid4()
        await self.session.execute(
            text("""INSERT INTO knowledge_documents
            (id,slug,title,version,effective_date,content_hash,model,dimensions,active)
            VALUES (:id,:slug,:title,:version,
            :effective_date,:content_hash,:model,:dimensions,true)"""),
            {
                "id": document_id,
                **doc.model_dump(exclude={"sections"}),
                **identity.model_dump(),
            },
        )
        if vectors is None or len(vectors) != len(doc.sections):
            raise ValueError("Missing embeddings")
        await self.session.execute(
            text("""INSERT INTO knowledge_chunks
            (id, document_id, section, ordinal, content, embedding)
            VALUES (:id,:document_id,:section,:ordinal,
            :content,CAST(:embedding AS vector))"""),
            [
                {
                    "id": uuid4(),
                    "document_id": document_id,
                    "section": section.title,
                    "ordinal": i,
                    "content": section.content,
                    "embedding": json.dumps(vectors[i]),
                }
                for i, section in enumerate(doc.sections)
            ],
        )

    async def set_config(self, identity: EmbeddingIdentity, generation: int) -> None:
        await self.session.execute(
            text("""INSERT INTO knowledge_config (id,model,dimensions,generation)
            VALUES (1,:model,:dimensions,:generation) ON CONFLICT (id) DO UPDATE
            SET model=excluded.model, dimensions=excluded.dimensions,
            generation=excluded.generation"""),
            {**identity.model_dump(), "generation": generation},
        )

    async def deactivate_all(self) -> None:
        await self.session.execute(
            text("UPDATE knowledge_documents SET active=false WHERE active")
        )

    async def counts(self) -> tuple[int, int]:
        row = (
            await self.session.execute(
                text("""SELECT count(DISTINCT d.id), count(c.id)
            FROM knowledge_documents d JOIN knowledge_chunks c ON c.document_id=d.id
            WHERE d.active""")
            )
        ).one()
        return row[0], row[1]

    async def search(
        self, vector: list[float], identity: EmbeddingIdentity, limit: int
    ) -> list[Citation]:
        rows = (
            await self.session.execute(
                text("""SELECT c.id AS chunk_id, d.id AS document_id,
            d.slug AS source, d.title, c.section, d.version, d.effective_date,
            c.content AS quote,
            1 - (c.embedding <=> CAST(:vector AS vector)) AS score
            FROM knowledge_chunks c JOIN knowledge_documents d ON d.id=c.document_id
            WHERE d.active AND d.model=:model AND d.dimensions=:dimensions
            ORDER BY c.embedding <=> CAST(:vector AS vector), c.id LIMIT :limit"""),
                {"vector": json.dumps(vector), "limit": limit, **identity.model_dump()},
            )
        ).mappings()
        return [Citation.model_validate(dict(row)) for row in rows]
