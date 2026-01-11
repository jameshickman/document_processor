# Database Update: Per-Extractor LLM Model Selection

This guide walks you through applying the database changes needed for the new per-extractor LLM model selection feature.

## Quick Start

If you just want to apply the migration quickly:

```bash
# 1. Check your database settings
cat .env | grep POSTGRES

# 2. Run the migration (replace values with your actual database credentials)
PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -d classifier_and_extractor -f migrations/add_llm_models.sql

# 3. Restart your application
```

## What This Update Does

This database update adds support for configuring and using different LLM models for different extractors:

- **New Table**: Creates `llm_models` table to store custom model configurations
- **New Column**: Adds `llm_model_id` to `extractors` table (optional, nullable)
- **Foreign Keys**: Sets up proper relationships with cascading delete behavior
- **Indexes**: Creates performance indexes for queries

## Detailed Instructions

### Step 1: Verify Database Connection

Check your `.env` file for database credentials:

```bash
cat .env | grep POSTGRES
```

You should see something like:
```
POSTGRES_DB=classifier_and_extractor
POSTGRES_HOST=localhost
POSTGRES_PASSWORD=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
```

### Step 2: Run the Migration

Using the values from your `.env` file, run:

```bash
PGPASSWORD=your_password psql -h hostname -p port -U username -d database_name -f migrations/add_llm_models.sql
```

**Example with default values**:
```bash
PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -d classifier_and_extractor -f migrations/add_llm_models.sql
```

**Expected output**:
```
CREATE TABLE
CREATE INDEX
CREATE INDEX
ALTER TABLE
CREATE INDEX
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
COMMENT
```

### Step 3: Verify the Migration

Check that the tables and columns were created:

```bash
# Check extractors table
PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -d classifier_and_extractor -c "\d extractors"

# Check llm_models table
PGPASSWORD=postgres psql -h localhost -p 5432 -U postgres -d classifier_and_extractor -c "\d llm_models"
```

You should see:
- `llm_model_id` column in the `extractors` table (type: integer, nullable)
- A new `llm_models` table with columns for id, name, provider, model_identifier, etc.

### Step 4: Restart Your Application

Stop and restart your FastAPI application to load the new code.

### Step 5: Verify It Works

1. Open your application in a browser
2. You should see a new **"Model Manager"** tab between "Extractors" and "Service API settings"
3. The Extractors list should load without errors
4. No "column does not exist" errors in the logs

## Using the New Feature

### Creating Model Configurations

1. Go to the **Model Manager** tab
2. Click **"Create New"**
3. Enter:
   - **Name**: A friendly name (e.g., "GPT-4 Turbo", "Claude Sonnet 4")
   - **Provider**: Select openai, deepinfra, or ollama
   - **Model Identifier**: The actual model name for the API (e.g., "gpt-4-turbo-preview")
   - **Temperature**: 0.0 for deterministic, higher for more creative
   - **Max Tokens**: Maximum response length
   - **Timeout**: Request timeout in seconds
4. Click **"Save Model"**

### Using Models with Extractors

1. Go to the **Extractors** tab
2. Select an extractor or create a new one
3. Use the **"LLM Model"** dropdown to select a model
4. Choose **"Use Global Default"** to use the model from your `.env` file
5. Click **"Save Extractor"**

### Model Behavior

- **If model is selected**: That specific model will be used for extraction
- **If "Use Global Default"**: Uses the model configured in `.env` environment variables
- **If model is deleted**: Extractors using it automatically fall back to global default

## Troubleshooting

### Error: "column extractors.llm_model_id does not exist"

**Cause**: The migration hasn't been run yet.

**Solution**: Follow Step 2 above to run the migration, then restart your app.

### Error: "relation 'llm_models' does not exist"

**Cause**: The migration failed or wasn't completed.

**Solution**:
1. Check the migration output for errors
2. Ensure your database user has CREATE permissions
3. Re-run the migration

### Warning: "relation 'llm_models' already exists"

**Cause**: You've run the migration before.

**Solution**: This is normal and safe to ignore. The migration uses `IF NOT EXISTS` to be safely re-runnable.

### Extractors not loading after migration

**Cause**: Application hasn't been restarted.

**Solution**: Restart your FastAPI application (Step 4).

## Rollback Instructions

If you need to remove this feature:

```sql
-- Connect to your database
psql -U postgres -d classifier_and_extractor

-- Remove the foreign key column
ALTER TABLE extractors DROP COLUMN IF EXISTS llm_model_id;

-- Drop the models table
DROP TABLE IF EXISTS llm_models CASCADE;
```

**Warning**: This will permanently delete all model configurations and associations.

## Summary

After completing this update:
- ✅ New "Model Manager" tab available in UI
- ✅ Create and manage multiple LLM model configurations
- ✅ Assign specific models to specific extractors
- ✅ Fall back to global default when needed
- ✅ Import/export preserves model associations
- ✅ Multi-tenant support (each user has their own models)

For more details, see `migrations/README.md`.
