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

### 3. OpenAI API Key (or Compatible API)

The system uses OpenAI's embedding API by default. Set your API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

For OpenAI-compatible APIs (like Ollama), you can also set:

```bash
export OPENAI_BASE_URL="http://localhost:11434/v1"
```

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
from api.models import get_db

# Initialize embedder
embedder = DocumentEmbedder(
    openai_api_key="your-key",  # Optional, uses env var if not provided
    embedding_model="text-embedding-ada-002",  # Default
    chunk_size=500,  # Words per chunk
    chunk_overlap=50  # Overlap between chunks
)

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
# 2. Generate them if needed
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

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_BASE_URL`: Base URL for OpenAI-compatible APIs (optional)
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_HOST`: Database host
- `POSTGRES_PORT`: Database port
- `POSTGRES_DB`: Database name

### Embedding Model

The default embedding model is `text-embedding-ada-002` which produces 1536-dimensional vectors. If you use a different model with different dimensions, you'll need to update the vector dimension in:

- `api/models/embedding.py` (line 23): Change `Vector(1536)` to your model's dimension
- `migrations/001_add_pgvector_support.sql` (line 12): Change `vector(1536)` to your model's dimension

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
Embedding Generator (OpenAI API)
    ↓
Vector Embeddings (1536 dimensions)
    ↓
PostgreSQL with PGVector
    ↓
Similarity Search (Cosine Distance)
    ↓
Relevant Context for LLM
```

## Future Enhancements

Potential improvements:
1. Support for different embedding models (sentence-transformers, etc.)
2. Hybrid search (keyword + semantic)
3. Re-ranking of results
4. Automatic embedding regeneration on document updates
5. Caching of frequently-searched queries