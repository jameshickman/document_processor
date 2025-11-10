"""
Vector utilities for document embeddings and similarity search.
Handles chunking, embedding generation, and vector database operations.
"""
import logging
import os
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from openai import OpenAI

from api.models.embedding import DocumentEmbedding
from api.models.documents import Document

logger = logging.getLogger(__name__)

# Default chunk size for document splitting (in words)
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 50

# Default embedding model
DEFAULT_EMBEDDING_MODEL = "text-embedding-ada-002"


class VectorUtils:
    """Utility class for vector embeddings and similarity search."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ):
        """
        Initialize vector utilities.

        Args:
            openai_api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            openai_base_url: OpenAI API base URL (defaults to None for official API)
            embedding_model: Model to use for embeddings
            chunk_size: Maximum words per chunk
            chunk_overlap: Number of words to overlap between chunks
        """
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_base_url = openai_base_url or os.getenv("OPENAI_BASE_URL")
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize OpenAI client
        if self.openai_base_url:
            self.client = OpenAI(api_key=self.openai_api_key, base_url=self.openai_base_url)
        else:
            self.client = OpenAI(api_key=self.openai_api_key)

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []

        if len(words) <= self.chunk_size:
            return [text]

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append(chunk_text)

            # Stop if we've reached the end
            if i + self.chunk_size >= len(words):
                break

        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

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
            force_regenerate: If True, delete existing embeddings and regenerate

        Returns:
            Number of embeddings created
        """
        # Get the document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Check if embeddings already exist
        existing_count = db.query(DocumentEmbedding).filter(
            DocumentEmbedding.document_id == document_id
        ).count()

        if existing_count > 0:
            if not force_regenerate:
                logger.info(f"Document {document_id} already has {existing_count} embeddings")
                return existing_count
            else:
                # Delete existing embeddings
                db.query(DocumentEmbedding).filter(
                    DocumentEmbedding.document_id == document_id
                ).delete()
                db.commit()
                logger.info(f"Deleted {existing_count} existing embeddings for document {document_id}")

        # Chunk the document
        chunks = self.chunk_text(document.full_text)
        logger.info(f"Processing {len(chunks)} chunks for document {document_id}")

        # Generate embeddings for each chunk
        embeddings_created = 0
        for idx, chunk in enumerate(chunks):
            try:
                embedding_vector = self.generate_embedding(chunk)

                # Store in database
                doc_embedding = DocumentEmbedding(
                    document_id=document_id,
                    chunk_index=idx,
                    chunk_text=chunk,
                    embedding=embedding_vector
                )
                db.add(doc_embedding)
                embeddings_created += 1

                # Commit in batches to avoid large transactions
                if (idx + 1) % 10 == 0:
                    db.commit()
                    logger.info(f"Committed batch of embeddings (up to chunk {idx + 1})")
            except Exception as e:
                logger.error(f"Failed to embed chunk {idx} for document {document_id}: {e}")
                db.rollback()
                raise

        # Final commit
        db.commit()
        logger.info(f"Created {embeddings_created} embeddings for document {document_id}")
        return embeddings_created

    def similarity_search(
        self,
        db: Session,
        query_text: str,
        document_id: Optional[int] = None,
        limit: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Tuple[DocumentEmbedding, float]]:
        """
        Search for similar text chunks using cosine similarity.

        Args:
            db: Database session
            query_text: Text to search for
            document_id: Optional document ID to limit search to specific document
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of tuples (DocumentEmbedding, similarity_score)
        """
        # Generate embedding for query
        query_embedding = self.generate_embedding(query_text)

        # Build similarity search query
        # Using cosine similarity: 1 - (embedding <=> query_embedding)
        query_str = """
            SELECT
                id,
                document_id,
                chunk_index,
                chunk_text,
                embedding,
                1 - (embedding <=> :query_embedding) AS similarity
            FROM document_embeddings
        """

        params = {"query_embedding": str(query_embedding)}

        if document_id is not None:
            query_str += " WHERE document_id = :document_id"
            params["document_id"] = document_id

        query_str += """
            ORDER BY embedding <=> :query_embedding
            LIMIT :limit
        """
        params["limit"] = limit

        # Execute query
        result = db.execute(text(query_str), params)
        rows = result.fetchall()

        # Filter by threshold and convert to objects
        results = []
        for row in rows:
            if row.similarity >= similarity_threshold:
                embedding = DocumentEmbedding(
                    id=row.id,
                    document_id=row.document_id,
                    chunk_index=row.chunk_index,
                    chunk_text=row.chunk_text,
                    embedding=row.embedding
                )
                results.append((embedding, float(row.similarity)))

        logger.info(f"Found {len(results)} similar chunks with threshold {similarity_threshold}")
        return results

    def get_relevant_context(
        self,
        db: Session,
        query_text: str,
        document_id: int,
        max_tokens: int = 2048,
        words_per_token: float = 0.75
    ) -> str:
        """
        Get relevant context from document based on query using similarity search.

        Args:
            db: Database session
            query_text: Query to search for
            document_id: Document to search within
            max_tokens: Maximum tokens in result
            words_per_token: Approximate words per token (default 0.75 for English)

        Returns:
            Combined text from most relevant chunks
        """
        # Calculate max words based on token limit
        max_words = int(max_tokens * words_per_token)

        # Perform similarity search
        similar_chunks = self.similarity_search(
            db=db,
            query_text=query_text,
            document_id=document_id,
            limit=20,  # Get more chunks initially
            similarity_threshold=0.5  # Lower threshold to get more candidates
        )

        if not similar_chunks:
            logger.warning(f"No similar chunks found for document {document_id}")
            # Fallback to first chunk of document
            first_chunk = db.query(DocumentEmbedding).filter(
                DocumentEmbedding.document_id == document_id,
                DocumentEmbedding.chunk_index == 0
            ).first()
            if first_chunk:
                return first_chunk.chunk_text[:max_words * 5]  # Rough word limit
            return ""

        # Combine chunks until we reach token limit
        combined_text = []
        current_words = 0

        for embedding, similarity in similar_chunks:
            chunk_words = len(embedding.chunk_text.split())
            if current_words + chunk_words <= max_words:
                combined_text.append(embedding.chunk_text)
                current_words += chunk_words
            else:
                # Add partial chunk to reach limit
                remaining_words = max_words - current_words
                if remaining_words > 50:  # Only add if meaningful amount remains
                    words = embedding.chunk_text.split()[:remaining_words]
                    combined_text.append(" ".join(words))
                break

        result = "\n\n".join(combined_text)
        logger.info(f"Built context with {current_words} words from {len(combined_text)} chunks")
        return result