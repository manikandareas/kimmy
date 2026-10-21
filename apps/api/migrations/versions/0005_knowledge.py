"""Versioned SOP corpus with explicit embedding identity."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE EXTENSION IF NOT EXISTS vector;
    CREATE TABLE knowledge_config (
        id integer PRIMARY KEY CHECK (id = 1),
        model text NOT NULL,
        dimensions integer NOT NULL CHECK (dimensions BETWEEN 1 AND 3072),
        generation bigint NOT NULL
    );
    CREATE TABLE knowledge_documents (
        id uuid PRIMARY KEY,
        slug text NOT NULL,
        title text NOT NULL,
        version text NOT NULL,
        effective_date date NOT NULL,
        content_hash varchar(64) NOT NULL,
        model text NOT NULL,
        dimensions integer NOT NULL,
        active boolean NOT NULL DEFAULT false,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE (slug, version, model, dimensions)
    );
    CREATE UNIQUE INDEX knowledge_active_slug_idx
        ON knowledge_documents(slug) WHERE active;
    CREATE TABLE knowledge_chunks (
        id uuid PRIMARY KEY,
        document_id uuid NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
        section text NOT NULL,
        ordinal integer NOT NULL,
        content text NOT NULL,
        embedding vector NOT NULL,
        UNIQUE (document_id, ordinal)
    );
    """)


def downgrade() -> None:
    raise RuntimeError("Restore a backup to roll back the SOP corpus")
