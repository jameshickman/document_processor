-- Migration: Fix vector dimensions to support multiple embedding providers
-- Description: Changes embedding column from vector(1536) to vector (no dimension constraint)
--              Adds metadata columns to track provider/model for automatic rebuilding
-- Date: 2025-11-10
-- Reason: Support DeepInfra (768), OpenAI (1536), and Ollama (1024) embeddings

-- Drop the existing index (it will be recreated)
DROP INDEX IF EXISTS ix_document_embeddings_embedding;

-- Alter the column to remove dimension constraint
-- Note: This requires recreating the column
ALTER TABLE document_embeddings
    ALTER COLUMN embedding TYPE vector USING embedding::vector;

-- Add metadata columns to track embedding provider
ALTER TABLE document_embeddings
    ADD COLUMN IF NOT EXISTS provider VARCHAR(50) NOT NULL DEFAULT 'openai';

ALTER TABLE document_embeddings
    ADD COLUMN IF NOT EXISTS model_name VARCHAR(100) NOT NULL DEFAULT 'text-embedding-ada-002';

ALTER TABLE document_embeddings
    ADD COLUMN IF NOT EXISTS dimensions INTEGER NOT NULL DEFAULT 1536;

-- Update dimensions for existing embeddings based on actual vector length
UPDATE document_embeddings
SET dimensions = array_length(embedding::float[], 1)
WHERE dimensions = 1536;  -- Only update default values

-- Recreate the index for vector similarity search
CREATE INDEX IF NOT EXISTS ix_document_embeddings_embedding
    ON document_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Add index on provider for faster queries when filtering by provider
CREATE INDEX IF NOT EXISTS ix_document_embeddings_provider
    ON document_embeddings(provider, model_name);

-- Comments for documentation
COMMENT ON COLUMN document_embeddings.embedding IS 'Vector embedding (variable dimensions: DeepInfra=768, OpenAI=1536, Ollama=1024)';
COMMENT ON COLUMN document_embeddings.provider IS 'Embedding provider used (deepinfra, openai, ollama)';
COMMENT ON COLUMN document_embeddings.model_name IS 'Embedding model name used';
COMMENT ON COLUMN document_embeddings.dimensions IS 'Vector embedding dimensions';

-- Verify the changes
SELECT
    column_name,
    data_type,
    character_maximum_length,
    column_default
FROM information_schema.columns
WHERE table_name = 'document_embeddings'
ORDER BY ordinal_position;