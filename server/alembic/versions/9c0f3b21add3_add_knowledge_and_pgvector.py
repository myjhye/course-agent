"""add pgvector extension and knowledge_chunks table

Revision ID: 9c0f3b21add3
Revises: 81d77924672b
Create Date: 2026-03-03
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision = "9c0f3b21add3"
down_revision = "81d77924672b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) pgvector 확장 활성화
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2) knowledge_chunks 테이블 생성
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_knowledge_chunks_id", "knowledge_chunks", ["id"])
    op.create_index(
        "ix_knowledge_chunks_source_type", "knowledge_chunks", ["source_type"]
    )

    # 3) 벡터 인덱스 (코사인 유사도용)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_cosine
        ON knowledge_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_cosine"
    )
    op.drop_index("ix_knowledge_chunks_source_type", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.execute("DROP EXTENSION IF EXISTS vector")

