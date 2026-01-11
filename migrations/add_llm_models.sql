-- Migration: Add LLM Models support
-- Description: Creates llm_models table and adds llm_model_id to extractors table

-- Create llm_models table
CREATE TABLE IF NOT EXISTS llm_models (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    provider VARCHAR NOT NULL,
    model_identifier VARCHAR NOT NULL,
    base_url VARCHAR,
    temperature FLOAT DEFAULT 0.0,
    max_tokens INTEGER DEFAULT 2048,
    timeout INTEGER DEFAULT 360,
    model_kwargs_json TEXT,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_llm_models_account ON llm_models(account_id);
CREATE INDEX IF NOT EXISTS idx_llm_models_name ON llm_models(name);

-- Add foreign key column to extractors table
ALTER TABLE extractors
ADD COLUMN IF NOT EXISTS llm_model_id INTEGER REFERENCES llm_models(id) ON DELETE SET NULL;

-- Create index for extractor model lookup
CREATE INDEX IF NOT EXISTS idx_extractors_llm_model ON extractors(llm_model_id);

-- Add comments
COMMENT ON TABLE llm_models IS 'User-configured LLM models for extraction';
COMMENT ON COLUMN llm_models.name IS 'User-friendly display name';
COMMENT ON COLUMN llm_models.provider IS 'LLM provider: openai, deepinfra, or ollama';
COMMENT ON COLUMN llm_models.model_identifier IS 'Actual model name used by the API';
COMMENT ON COLUMN llm_models.model_kwargs_json IS 'JSON string with additional provider-specific parameters';
COMMENT ON COLUMN extractors.llm_model_id IS 'Optional: specific model to use for this extractor (NULL = use global default)';
