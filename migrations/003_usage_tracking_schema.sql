-- Migration: Add usage tracking tables

-- Create usage_logs table
CREATE TABLE usage_logs (
    id BIGSERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,

    -- Timestamp
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Operation metadata
    operation_type VARCHAR(50) NOT NULL,  -- 'extraction', 'classification', 'embedding', 'upload'
    source_type VARCHAR(20) NOT NULL,     -- 'workbench', 'api'

    -- Resource identifiers
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    extractor_id INTEGER REFERENCES extractors(id) ON DELETE SET NULL,
    classifier_id INTEGER REFERENCES classifiers(id) ON DELETE SET NULL,

    -- LLM tracking
    llm_model_id INTEGER REFERENCES llm_models(id) ON DELETE SET NULL,
    provider VARCHAR(50),                  -- 'openai', 'deepinfra', 'ollama', 'anthropic'
    model_name VARCHAR(255),               -- Actual model used (e.g., 'gpt-4', 'llama-2-70b')

    -- Token usage (for LLM operations)
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,

    -- Storage tracking (for upload operations)
    bytes_stored BIGINT,                   -- Size of uploaded/processed file

    -- Performance metrics
    duration_ms INTEGER,                   -- Operation duration in milliseconds
    status VARCHAR(20),                    -- 'success', 'failure', 'partial'
    error_message TEXT,                    -- If status != 'success'

    -- Request metadata
    user_agent TEXT,
    ip_address INET
);

-- Create indexes for efficient querying
CREATE INDEX idx_usage_logs_account_timestamp ON usage_logs(account_id, timestamp DESC);
CREATE INDEX idx_usage_logs_operation_type ON usage_logs(operation_type);
CREATE INDEX idx_usage_logs_timestamp ON usage_logs(timestamp DESC);
CREATE INDEX idx_usage_logs_provider_model ON usage_logs(provider, model_name) WHERE provider IS NOT NULL;
CREATE INDEX idx_usage_logs_source_type ON usage_logs(source_type);

-- Create usage_summaries table
CREATE TABLE usage_summaries (
    id BIGSERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,

    -- Time bucket
    date DATE NOT NULL,

    -- Usage breakdown by source
    workbench_operations INTEGER DEFAULT 0,
    api_operations INTEGER DEFAULT 0,
    total_operations INTEGER DEFAULT 0,

    -- Operation counts by type
    extractions INTEGER DEFAULT 0,
    classifications INTEGER DEFAULT 0,
    embeddings INTEGER DEFAULT 0,
    uploads INTEGER DEFAULT 0,
    downloads INTEGER DEFAULT 0,

    -- LLM usage totals
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,

    -- Success rates
    successful_operations INTEGER DEFAULT 0,
    failed_operations INTEGER DEFAULT 0,

    -- Storage
    bytes_uploaded BIGINT DEFAULT 0,
    bytes_downloaded BIGINT DEFAULT 0,

    -- Performance
    avg_duration_ms INTEGER,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Uniqueness constraint
    UNIQUE(account_id, date)
);

CREATE INDEX idx_usage_summaries_account_date ON usage_summaries(account_id, date DESC);
CREATE INDEX idx_usage_summaries_date ON usage_summaries(date DESC);

-- Create usage_summaries_by_model table
CREATE TABLE usage_summaries_by_model (
    id BIGSERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,

    -- Time bucket
    date DATE NOT NULL,

    -- LLM identification
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    llm_model_id INTEGER REFERENCES llm_models(id) ON DELETE SET NULL,

    -- Usage counts
    operation_count INTEGER DEFAULT 0,

    -- Token tracking
    input_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,

    -- Performance
    avg_duration_ms INTEGER,

    -- Success rate
    successful_operations INTEGER DEFAULT 0,
    failed_operations INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Uniqueness constraint
    UNIQUE(account_id, date, provider, model_name)
);

CREATE INDEX idx_usage_summaries_by_model_account_date ON usage_summaries_by_model(account_id, date DESC);
CREATE INDEX idx_usage_summaries_by_model_provider_model ON usage_summaries_by_model(provider, model_name);

-- Create storage_usage table
CREATE TABLE storage_usage (
    id BIGSERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,

    -- Time
    date DATE NOT NULL,

    -- Storage metrics (in bytes)
    total_bytes BIGINT NOT NULL DEFAULT 0,
    document_count INTEGER NOT NULL DEFAULT 0,

    -- Storage backend
    storage_backend VARCHAR(20),  -- 'local', 's3'

    -- Breakdown by file type (optional)
    pdf_bytes BIGINT DEFAULT 0,
    docx_bytes BIGINT DEFAULT 0,
    html_bytes BIGINT DEFAULT 0,
    other_bytes BIGINT DEFAULT 0,

    -- Metadata
    calculated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Uniqueness constraint
    UNIQUE(account_id, date)
);

CREATE INDEX idx_storage_usage_account_date ON storage_usage(account_id, date DESC);
CREATE INDEX idx_storage_usage_date ON storage_usage(date DESC);

-- Add columns to accounts table
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS roles TEXT[] DEFAULT '{}';
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS usage_tracking_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS usage_limit_tokens BIGINT;  -- Optional token limit per month
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS usage_alert_threshold FLOAT;  -- Alert at % of limit (e.g., 0.8 = 80%)
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- Insert default role for existing admin users if roles column is empty
UPDATE accounts SET roles = ARRAY['admin', 'reporting'] WHERE roles = '{}' AND is_admin = true;