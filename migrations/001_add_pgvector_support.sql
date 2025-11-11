-- Migration: Add PGVector support for document embeddings
-- Description: Enables pgvector extension and creates document_embeddings table
-- Date: 2025-11-10

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create document_embeddings table
-- Note: vector type without dimension constraint allows different embedding providers
-- DeepInfra: 768 dimensions, OpenAI: 1536 dimensions, Ollama: 1024 dimensions
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector NOT NULL,
    provider VARCHAR(50) NOT NULL DEFAULT 'openai',
    model_name VARCHAR(100) NOT NULL DEFAULT 'text-embedding-ada-002',
    dimensions INTEGER NOT NULL DEFAULT 1536,
    CONSTRAINT fk_document_embeddings_document_id
        FOREIGN KEY (document_id)
        REFERENCES documents(id)
        ON DELETE CASCADE
);

-- Create index for efficient filtering by document
CREATE INDEX IF NOT EXISTS ix_document_embeddings_document_id
    ON document_embeddings(document_id);

-- Create index for vector similarity search using cosine distance
-- Note: This uses IVFFlat index for faster similarity search
-- The 'lists' parameter should be adjusted based on dataset size
-- Rule of thumb: lists = rows / 1000 for datasets < 1M rows
CREATE INDEX IF NOT EXISTS ix_document_embeddings_embedding
    ON document_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Create index on provider for faster queries when checking provider mismatches
CREATE INDEX IF NOT EXISTS ix_document_embeddings_provider
    ON document_embeddings(provider, model_name);

-- Comments for documentation
COMMENT ON TABLE document_embeddings IS 'Stores vector embeddings for document chunks to enable semantic search';
COMMENT ON COLUMN document_embeddings.document_id IS 'Foreign key to documents table';
COMMENT ON COLUMN document_embeddings.chunk_index IS 'Sequential index of chunk within the document';
COMMENT ON COLUMN document_embeddings.chunk_text IS 'The actual text content of this chunk';
COMMENT ON COLUMN document_embeddings.embedding IS 'Vector embedding (variable dimensions: DeepInfra=768, OpenAI=1536, Ollama=1024)';
COMMENT ON COLUMN document_embeddings.provider IS 'Embedding provider used (deepinfra, openai, ollama)';
COMMENT ON COLUMN document_embeddings.model_name IS 'Embedding model name used';
COMMENT ON COLUMN document_embeddings.dimensions IS 'Vector embedding dimensions';