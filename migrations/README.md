# Database Migrations

This directory contains SQL migration scripts for database schema changes.

## Applying Migrations

### For Existing Installations

If you have an existing database with the old schema (1536-dimension vectors), run:

```bash
psql -U postgres -d classifier_and_extractor_2 -p 5433 -f migrations/002_fix_vector_dimensions.sql
```

This will:
- Remove dimension constraints from the embedding column
- Allow embeddings from any provider (DeepInfra 768, OpenAI 1536, Ollama 1024)
- Recreate the vector similarity index

### For New Installations

The application will automatically create tables on first run, but you can manually run:

```bash
psql -U postgres -d classifier_and_extractor_2 -p 5433 -f migrations/001_add_pgvector_support.sql
```

## Migration History

| Migration | Date | Description |
|-----------|------|-------------|
| 001_add_pgvector_support.sql | 2025-11-10 | Initial PGVector setup with variable dimensions |
| 002_fix_vector_dimensions.sql | 2025-11-10 | Fix existing installations to support multiple providers |
| add_llm_models.sql | 2026-01-11 | Add support for per-extractor LLM model selection |

## LLM Model Selection Feature (add_llm_models.sql)

This migration adds the ability to configure and select different LLM models per extractor.

### What It Does

- Creates `llm_models` table for storing custom model configurations
- Adds `llm_model_id` column to `extractors` table (nullable)
- Sets up foreign key with `ON DELETE SET NULL` (extractors revert to global default if model is deleted)
- Creates performance indexes

### How to Apply

**Step 1: Check your database credentials** (from `.env` file):
```bash
cat .env | grep POSTGRES
```

**Step 2: Run the migration**:
```bash
# Using environment variables
PGPASSWORD=your_password psql -h hostname -p port -U username -d database_name -f migrations/add_llm_models.sql

# Example with typical values:
PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -d classifier_and_extractor -f migrations/add_llm_models.sql
```

**Step 3: Verify the migration**:
```bash
# Check extractors table has new column
PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -d classifier_and_extractor -c "\d extractors"

# Check llm_models table was created
PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -d classifier_and_extractor -c "\d llm_models"
```

You should see:
- `llm_model_id` column in the `extractors` table
- A new `llm_models` table with columns: id, name, provider, model_identifier, base_url, temperature, max_tokens, timeout, model_kwargs_json, account_id, created_at

**Step 4: Restart your application** to load the new code.

### Using the Feature

After applying the migration and restarting:

1. Navigate to the **Model Manager** tab (new tab in the UI)
2. Create model configurations (e.g., "GPT-4 Turbo", "Claude Sonnet", etc.)
3. In the **Extractors** tab, select a model from the dropdown for each extractor
4. Leave as "Use Global Default" to use the model specified in `.env` file

### Rollback (if needed)

To remove this feature:
```sql
-- Remove foreign key column from extractors
ALTER TABLE extractors DROP COLUMN IF EXISTS llm_model_id;

-- Drop the llm_models table
DROP TABLE IF EXISTS llm_models CASCADE;
```

**Warning**: This will delete all stored model configurations.

## Automatic Provider Change Detection

The system now automatically detects when you switch embedding providers and regenerates embeddings. For example:

1. You generate embeddings with DeepInfra (768 dimensions)
2. Later, you change `.env` to use OpenAI (1536 dimensions)
3. Next time a document is accessed, the system detects the mismatch
4. Embeddings are automatically regenerated with the new provider

Log output:
```
WARNING: Document 123 has embeddings from different provider (deepinfra/google/embeddinggemma-300m/768D)
         but current config is (openai/text-embedding-ada-002/1536D).
         Automatically regenerating embeddings...
INFO: Deleted 15 existing embeddings for document 123
INFO: Processing 15 chunks for document 123
INFO: Created 15 embeddings for document 123
```

## Troubleshooting

### "column extractors.llm_model_id does not exist" Error

If you see this error after updating the code:
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn) column extractors.llm_model_id does not exist
```

**Solution**: You need to run the `add_llm_models.sql` migration:
```bash
PGPASSWORD=your_password psql -h hostname -p port -U username -d database_name -f migrations/add_llm_models.sql
```

Then restart your application.

### Check if migration was successful

```sql
-- Check vector column type
SELECT
    column_name,
    data_type,
    udt_name
FROM information_schema.columns
WHERE table_name = 'document_embeddings'
    AND column_name = 'embedding';

-- Should show: data_type = 'USER-DEFINED', udt_name = 'vector'
-- No specific dimension constraint
```

### Verify embeddings are being saved

```sql
-- Count embeddings by provider
SELECT
    provider,
    model_name,
    dimensions,
    COUNT(*) as embedding_count
FROM document_embeddings
GROUP BY provider, model_name, dimensions
ORDER BY embedding_count DESC;

-- Check embedding dimensions for each row
SELECT
    id,
    document_id,
    chunk_index,
    provider,
    model_name,
    dimensions,
    array_length(embedding::float[], 1) as actual_dimensions
FROM document_embeddings
LIMIT 10;
```

### Check for provider mismatches

```sql
-- Find documents with embeddings from old providers
SELECT DISTINCT
    de.provider,
    de.model_name,
    de.dimensions,
    COUNT(DISTINCT de.document_id) as document_count
FROM document_embeddings de
GROUP BY de.provider, de.model_name, de.dimensions;
```

### Clear embeddings for a specific provider

```sql
-- Remove all DeepInfra embeddings (they will be regenerated as OpenAI)
DELETE FROM document_embeddings
WHERE provider = 'deepinfra';
```

### Clear all embeddings (force regeneration)

```sql
TRUNCATE TABLE document_embeddings;
```

## Notes

- **Variable Dimensions**: The schema now supports any vector dimension, allowing you to switch between embedding providers without schema changes
- **Automatic Creation**: When the application starts, it will automatically create tables if they don't exist
- **Automatic Rebuilding**: When you switch providers (e.g., DeepInfra → OpenAI), embeddings are automatically regenerated on next access
- **Provider Metadata**: Each embedding stores the provider, model, and dimensions used to generate it
- **Index Performance**: The IVFFlat index is optimized for ~100 lists. Adjust for larger datasets (lists = rows / 1000)
- **No Manual Intervention**: Just change your `.env` file and the system handles the rest