"""
SQLAlchemy model for PGVector embeddings.
Store vector embeddings for documents to enable semantic search.
"""
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .database import Base


class DocumentEmbedding(Base):
    """
    Store vector embeddings for document chunks.
    Each document can have multiple embeddings (one per chunk).
    """
    __tablename__ = "document_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Position of chunk in document
    chunk_text = Column(Text, nullable=False)  # The actual text chunk
    embedding = Column(Vector(), nullable=False)  # Vector embedding (variable dimensions based on provider)

    # Track embedding provider metadata for rebuilding when provider changes
    provider = Column(String(50), nullable=False, default="openai")  # deepinfra, openai, ollama
    model_name = Column(String(100), nullable=False, default="text-embedding-ada-002")  # Model used
    dimensions = Column(Integer, nullable=False, default=1536)  # Embedding dimensions

    # Relationship back to document
    document = relationship("Document", back_populates="embeddings")

    # Create an index for vector similarity search using cosine distance
    __table_args__ = (
        Index(
            'ix_document_embeddings_embedding',
            'embedding',
            postgresql_using='ivfflat',
            postgresql_with={'lists': 100},
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
        # Index for efficient filtering by document
        Index('ix_document_embeddings_document_id', 'document_id'),
    )