"""
Document embedder for semantic search and retrieval.
Uses PGVector for storing and querying vector embeddings.

Supports multiple embedding providers:
- DeepInfra: google/embeddinggemma-300m (768 dimensions)
- OpenAI: text-embedding-ada-002 (1536 dimensions)
- Ollama: mxbai-embed-large (1024 dimensions)
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session

from api.models.embedding import DocumentEmbedding
from api.models.documents import Document
from api.util.vector_utils import VectorUtils
from api.util.embedding_config import EmbeddingConfig, create_embedding_config

logger = logging.getLogger(__name__)


class DocumentEmbedder:
    """
    High-level interface for document embedding and retrieval.
    Uses vector database for efficient semantic search.
    """

    def __init__(
        self,
        embedding_config: Optional[EmbeddingConfig] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        # Legacy parameters for backward compatibility
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        embedding_model: Optional[str] = None
    ):
        """
        Initialize document embedder.

        Args:
            embedding_config: EmbeddingConfig object (if None, creates from environment)
            chunk_size: Maximum words per chunk
            chunk_overlap: Words to overlap between chunks
            openai_api_key: (Deprecated) OpenAI API key for legacy compatibility
            openai_base_url: (Deprecated) OpenAI API base URL for legacy compatibility
            embedding_model: (Deprecated) Model name for legacy compatibility
        """
        # Initialize vector utilities with embedding config
        self.vector_utils = VectorUtils(
            embedding_config=embedding_config,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            # Pass through legacy parameters if provided
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            embedding_model=embedding_model
        )
        logger.info(f"DocumentEmbedder initialized with {self.vector_utils.config.provider} provider")

    def embed_document(
        self,
        db: Session,
        document_id: int,
        force_regenerate: bool = False
    ) -> int:
        """
        Generate and store embeddings for a document.

        Args:
            db: Database session
            document_id: ID of document to embed
            force_regenerate: If True, regenerate even if embeddings exist

        Returns:
            Number of embeddings created
        """
        return self.vector_utils.embed_document(
            db=db,
            document_id=document_id,
            force_regenerate=force_regenerate
        )

    def ensure_document_embedded(self, db: Session, document_id: int) -> bool:
        """
        Ensure document has embeddings, creating them if needed.

        Args:
            db: Database session
            document_id: ID of document to check

        Returns:
            True if embeddings exist or were created
        """
        # Check if embeddings exist
        existing_count = db.query(DocumentEmbedding).filter(
            DocumentEmbedding.document_id == document_id
        ).count()

        if existing_count > 0:
            logger.debug(f"Document {document_id} already has {existing_count} embeddings")
            return True

        # Create embeddings
        logger.info(f"Creating embeddings for document {document_id}")
        try:
            count = self.embed_document(db=db, document_id=document_id)
            return count > 0
        except Exception as e:
            logger.error(f"Failed to create embeddings for document {document_id}: {e}")
            return False

    def get_relevant_context(
        self,
        db: Session,
        query: str,
        document_id: int,
        max_tokens: int = 2048
    ) -> str:
        """
        Get relevant context from document based on query.

        This is the main method to use for fact extraction and document analysis.
        It will:
        1. Ensure the document has embeddings
        2. Perform similarity search based on the query
        3. Return the most relevant text chunks

        Args:
            db: Database session
            query: Query or question to search for
            document_id: Document to search within
            max_tokens: Maximum tokens in result

        Returns:
            Combined text from most relevant chunks
        """
        # Ensure document is embedded
        if not self.ensure_document_embedded(db, document_id):
            logger.error(f"Failed to ensure embeddings for document {document_id}")
            # Fallback to full text
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                words = document.full_text.split()[:int(max_tokens * 0.75)]
                return " ".join(words)
            return ""

        # Get relevant context using similarity search
        return self.vector_utils.get_relevant_context(
            db=db,
            query_text=query,
            document_id=document_id,
            max_tokens=max_tokens
        )

    def search_similar_chunks(
        self,
        db: Session,
        query: str,
        document_id: Optional[int] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ):
        """
        Search for similar text chunks across documents or within a specific document.

        Args:
            db: Database session
            query: Query text to search for
            document_id: Optional document ID to limit search
            limit: Maximum results to return
            similarity_threshold: Minimum similarity score

        Returns:
            List of (DocumentEmbedding, similarity_score) tuples
        """
        return self.vector_utils.similarity_search(
            db=db,
            query_text=query,
            document_id=document_id,
            limit=limit,
            similarity_threshold=similarity_threshold
        )