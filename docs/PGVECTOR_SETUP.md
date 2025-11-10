# PGVector Document Embeddings Setup

This document explains how to use the PGVector integration for semantic search and document embeddings.

## Overview

The system now supports vector embeddings for documents, enabling semantic search and more efficient document retrieval. Instead of processing entire documents or using simple chunking, the system:

1. Splits documents into semantic chunks
2. Generates vector embeddings for each chunk
3. Stores embeddings in PostgreSQL with PGVector
4. Performs similarity search to find relevant content

## Prerequisites

### 1. PostgreSQL with PGVector Extension

Your PostgreSQL database must have the pgvector extension installed:

```sql
CREATE EXTENSION vector;
```

The application will automatically attempt to enable this extension on startup.

### 2. Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

The key new dependency is `pgvector~=0.3.6`.

### 3. Embedding Provider Configuration

The system supports multiple embedding providers with automatic fallback:

#### Option 1: DeepInfra (Recommended for Cost)
- Model: `google/embeddinggemma-300m` (768 dimensions)
- Fast and cost-effective

```bash
export DEEPINFRA_EMBEDDING_TOKEN="your-deepinfra-token"
# or reuse your existing DeepInfra token
export DEEPINFRA_API_TOKEN="your-deepinfra-token"

# Optional: Specify different model
export DEEPINFRA_EMBEDDING_MODEL="google/embeddinggemma-300m"
export DEEPINFRA_EMBEDDING_DIMENSIONS="768"
```

#### Option 2: OpenAI
- Model: `text-embedding-ada-002` (1536 dimensions)
- Highest quality embeddings

```bash
export OPENAI_API_KEY="your-openai-key"

# Optional: Specify different model
export OPENAI_EMBEDDING_MODEL="text-embedding-ada-002"
export OPENAI_EMBEDDING_DIMENSIONS="1536"
```

#### Option 3: Ollama (Local)
- Model: `mxbai-embed-large` (1024 dimensions)
- Free, runs locally

```bash
export OLLAMA_BASE_URL="http://localhost:11434/v1"

# Optional: Specify different model
export OLLAMA_EMBEDDING_MODEL="mxbai-embed-large"
export OLLAMA_EMBEDDING_DIMENSIONS="1024"
```

**Provider Priority**: The system will use DeepInfra → OpenAI → Ollama (first available)

## Database Setup

### Automatic Setup (Recommended)

When the application starts, it will automatically:
1. Enable the pgvector extension
2. Create the `document_embeddings` table
3. Create necessary indexes for vector similarity search

No manual intervention is required.

### Manual Migration

If you need to manually set up the database, run the migration script:

```bash
psql -U your_user -d your_database -f migrations/001_add_pgvector_support.sql
```

## Usage

### Using the DocumentEmbedder

```python
from api.util.embedder import DocumentEmbedder
from api.util.embedding_config import create_embedding_config
from api.models import get_db

# Option 1: Use automatic configuration from environment variables
embedder = DocumentEmbedder(
    chunk_size=500,  # Words per chunk
    chunk_overlap=50  # Overlap between chunks
)
# Will automatically use DeepInfra, OpenAI, or Ollama based on available env vars

# Option 2: Explicitly specify configuration
from api.util.embedding_config import EmbeddingConfig

config = EmbeddingConfig(
    provider="deepinfra",
    base_url="https://api.deepinfra.com/v1/openai",
    api_key="your-token",
    model_name="google/embeddinggemma-300m",
    dimensions=768,
    timeout=360
)
embedder = DocumentEmbedder(embedding_config=config)

# Get relevant context from a document
db = next(get_db())
relevant_text = embedder.get_relevant_context(
    db=db,
    query="What is the total cost?",
    document_id=123,
    max_tokens=2048
)

# The embedder will automatically:
# 1. Check if document has embeddings
# 2. Generate them if needed (using configured provider)
# 3. Perform similarity search
# 4. Return most relevant chunks
```

### Manually Embedding Documents

```python
# Embed a specific document
num_embeddings = embedder.embed_document(
    db=db,
    document_id=123,
    force_regenerate=False  # Set True to regenerate existing embeddings
)

print(f"Created {num_embeddings} embeddings")
```

### Searching Across Documents

```python
# Search across all documents
results = embedder.search_similar_chunks(
    db=db,
    query="contract terms",
    limit=10,
    similarity_threshold=0.7
)

for embedding, score in results:
    print(f"Document {embedding.document_id}, Chunk {embedding.chunk_index}")
    print(f"Similarity: {score:.2f}")
    print(f"Text: {embedding.chunk_text[:100]}...")
```

## Configuration

### Environment Variables

#### Database Configuration
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_HOST`: Database host
- `POSTGRES_PORT`: Database port
- `POSTGRES_DB`: Database name

#### Embedding Provider Configuration

**DeepInfra (Priority 1)**
- `DEEPINFRA_EMBEDDING_TOKEN` or `DEEPINFRA_API_TOKEN`: DeepInfra API token
- `DEEPINFRA_EMBEDDING_MODEL`: Model name (default: `google/embeddinggemma-300m`)
- `DEEPINFRA_EMBEDDING_DIMENSIONS`: Vector dimensions (default: `768`)
- `DEEPINFRA_EMBEDDING_BASE_URL`: Base URL (default: `https://api.deepinfra.com/v1/openai`)
- `DEEPINFRA_EMBEDDING_TIMEOUT`: Request timeout in seconds (default: `360`)

**OpenAI (Priority 2)**
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_EMBEDDING_MODEL`: Model name (default: `text-embedding-ada-002`)
- `OPENAI_EMBEDDING_DIMENSIONS`: Vector dimensions (default: `1536`)
- `OPENAI_EMBEDDING_BASE_URL` or `OPENAI_BASE_URL`: Base URL (default: `https://api.openai.com/v1`)
- `OPENAI_EMBEDDING_TIMEOUT`: Request timeout in seconds (default: `360`)

**Ollama (Priority 3 - Fallback)**
- `OLLAMA_EMBEDDING_MODEL` or `OLLAMA_BASE_URL`: Model name (default: `mxbai-embed-large`)
- `OLLAMA_EMBEDDING_DIMENSIONS`: Vector dimensions (default: `1024`)
- `OLLAMA_EMBEDDING_BASE_URL` or `OLLAMA_BASE_URL`: Base URL (default: `http://localhost:11434/v1`)
- `OLLAMA_EMBEDDING_TIMEOUT`: Request timeout in seconds (default: `360`)

### Embedding Models and Dimensions

Different providers use different embedding dimensions:

| Provider | Model | Dimensions | Notes |
|----------|-------|------------|-------|
| DeepInfra | `google/embeddinggemma-300m` | 768 | Cost-effective, fast |
| OpenAI | `text-embedding-ada-002` | 1536 | High quality |
| OpenAI | `text-embedding-3-small` | 1536 | Newer model |
| OpenAI | `text-embedding-3-large` | 3072 | Highest quality |
| Ollama | `mxbai-embed-large` | 1024 | Free, local |
| Ollama | `nomic-embed-text` | 768 | Alternative |
| Ollama | `all-minilm` | 384 | Smaller, faster |

**Important**: The database schema is configured for 1536 dimensions by default (OpenAI). If using a different provider/model, you may need to update:

- `api/models/embedding.py`: Change `Vector(1536)` to match your model's dimensions
- `migrations/001_add_pgvector_support.sql`: Change `vector(1536)` to match

However, PGVector supports variable dimensions per row, so mixing models is technically possible (though not recommended for consistency)

### Chunk Size and Overlap

Default settings:
- **Chunk size**: 500 words
- **Overlap**: 50 words

Adjust these based on your documents:
- Larger chunks = fewer embeddings, more context per chunk
- Smaller chunks = more embeddings, more precise matching
- More overlap = better context preservation across chunk boundaries

## Performance Optimization

### Index Tuning

The IVFFlat index is created with `lists = 100`. For larger datasets, adjust this:

```sql
-- For datasets with 100k+ documents
CREATE INDEX ix_document_embeddings_embedding
    ON document_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 1000);
```

Rule of thumb: `lists = rows / 1000` for datasets < 1M rows

### Batch Processing

For bulk embedding of many documents:

```python
from api.models import Document

# Get all documents without embeddings
documents = db.query(Document).all()

for doc in documents:
    if not doc.embeddings:
        embedder.embed_document(db, doc.id)
        print(f"Embedded document {doc.id}")
```

## Integration with Fact Extractor

The fact extractor can be updated to use the vector database instead of simple chunking. Example integration:

```python
from api.util.embedder import DocumentEmbedder

embedder = DocumentEmbedder()

# Instead of chunking entire document:
# relevant_text = embedder.get_relevant_context(
#     db=db,
#     query=extraction_query.query,
#     document_id=document.id,
#     max_tokens=2048
# )
#
# Then pass relevant_text to the LLM instead of full document chunks
```

## Troubleshooting

### "pgvector extension not available"

Make sure pgvector is installed in your PostgreSQL instance:

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-14-pgvector

# macOS with Homebrew
brew install pgvector

# From source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### "OpenAI API rate limits"

Consider:
1. Implementing rate limiting in your code
2. Using batch processing with delays
3. Using a lower-tier embedding model
4. Using a self-hosted embedding model (via OPENAI_BASE_URL)

### Slow similarity searches

1. Ensure indexes are created properly
2. Increase the `lists` parameter for larger datasets
3. Consider using HNSW index instead of IVFFlat for better performance (PostgreSQL 13+)

## Architecture

```
Document
    ↓
DocumentChunker (in vector_utils.py)
    ↓
Multiple Text Chunks
    ↓
Embedding Configuration (embedding_config.py)
    ├─→ DeepInfra (google/embeddinggemma-300m - 768 dims)
    ├─→ OpenAI (text-embedding-ada-002 - 1536 dims)
    └─→ Ollama (mxbai-embed-large - 1024 dims)
    ↓
Embedding Generator (via OpenAI-compatible API)
    ↓
Vector Embeddings (variable dimensions)
    ↓
PostgreSQL with PGVector
    ↓
Similarity Search (Cosine Distance)
    ↓
Relevant Context for LLM
```

## Future Enhancements

Potential improvements:
1. ✅ ~~Support for different embedding models~~ (Implemented: DeepInfra, OpenAI, Ollama)
2. Hybrid search (keyword + semantic)
3. Re-ranking of results
4. Automatic embedding regeneration on document updates
5. Caching of frequently-searched queries
6. Support for additional embedding providers (sentence-transformers, Cohere, etc.)