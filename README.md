# Classifier and Extractor API

## Executive Summary

The Classifier and Extractor API is a comprehensive document processing platform designed to automate the classification and extraction of information from diverse document formats. Built on FastAPI, this system leverages Large Language Models (LLMs) and vector search technology to transform unstructured document content into structured, actionable data. The platform serves dual purposes: enabling rapid development of document processing workflows through an intuitive web-based workbench, and providing robust API endpoints for seamless integration into existing business systems. With support for multiple document formats, flexible storage backends, and multiple LLM providers, the system offers a scalable solution for organizations looking to automate document-centric processes and extract valuable insights from their document repositories.

## Features

### Plugin-Based Document Extraction Framework
- **Automatic format detection** - Intelligently routes files to the appropriate handler based on extension
- **Dynamic handler discovery** - New format handlers are automatically detected at runtime
- **Extensible architecture** - Add support for new file formats by simply dropping a handler class in the handlers directory
- **Markdown-first conversion** - Prioritizes Markdown output with graceful fallback to plain text
- **Multi-format support**:
  - **Text files**: `.txt`, `.md` (direct passthrough)
  - **PDF documents**: `.pdf` (via pdftotext)
  - **HTML/Web**: `.html`, `.htm` (converted to Markdown via Pandoc)
  - **Microsoft Office**: `.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx`
  - **LibreOffice/OpenOffice**: `.odt`, `.rtf`
  - Multi-stage conversion pipeline with LibreOffice and Pandoc for complex documents
- **Robust error handling** with validation of extracted text quality

### Document Classification
- **Fuzzy matching** with Levenshtein distance scoring
- **Wildcard support** for flexible pattern matching:
  - `*` - matches any word or number
  - `?` - matches words without numbers
  - `#` - matches words with numbers
- Configurable matching distance and term weights
- Fast in-memory classification without LLM dependencies

### Fact Extraction
- LLM-powered information extraction from documents
- **Vector Search with PGVector** - Semantic search for intelligent context retrieval:
  - Automatically generates and stores document embeddings
  - Uses similarity search to find relevant document sections
  - Reduces LLM token usage by sending only relevant context
  - Falls back to traditional chunking if PGVector unavailable
- Multiple LLM provider support with automatic fallback:
  1. **DeepInfra** - Cloud-hosted LLMs with competitive pricing
  2. **OpenAI** - Official OpenAI GPT models
  3. **Ollama** - Local LLM service (fallback)
- Document chunking for large files (when not using vector search)
- Intelligent prompt building
- Seamless integration with the document extraction framework

### API Features
- RESTful API endpoints for documents, classifiers, and extractors
- JWT-based authentication and authorization
- Role-based access control (RBAC)
- Document upload and storage management
- PostgreSQL database backend
- CORS support for web applications
- Static file serving with Nginx integration

## Requirements

### Core Requirements
- **Python 3.8+**
- **PostgreSQL 12+** with PGVector extension (for vector search)
- **LibreOffice** (for document format conversion)
- **Pandoc** (for HTML to Markdown conversion)
- **poppler-utils** (pdftotext for PDF extraction)

### LLM Provider (choose one)
- **DeepInfra API key** (recommended - cloud-hosted LLMs)
- **OpenAI API key** (for GPT models)
- **Ollama** (for local/self-hosted LLMs)

### Storage Backend (choose one)
- **Local filesystem** - Built-in, no additional setup
- **S3-compatible storage** - Requires boto3 library (included in requirements.txt)
  - AWS S3
  - MinIO (self-hosted)
  - DigitalOcean Spaces
  - Backblaze B2
  - Any S3-compatible service

### Optional
- **Nginx** - Recommended for production deployments
- **MinIO** - Self-hosted S3-compatible storage

## Quick Start

### Development Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd classifier_and_extractor
```

2. **Create and activate a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Install system dependencies:**
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install libreoffice pandoc poppler-utils postgresql-<version>-pgvector

# macOS
brew install libreoffice pandoc poppler pgvector
```

5. **Set up PostgreSQL database:**
```bash
# Create database
createdb classifier_extractor

# Enable PGVector extension (run in psql)
psql -d classifier_extractor -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

6. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your settings (see Configuration section below)
```

7. **Run the development server:**
```bash
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

8. **Access the application:**
- Workbench UI: http://localhost:8000/
- API Documentation: http://localhost:8000/docs

### Production Setup

For production deployment with Gunicorn, Nginx, and proper security:

1. Follow steps 1-6 from Development Setup

2. **Configure production storage backend** (see [Storage Configuration](#storage-configuration))

3. **Set up Gunicorn:**
```bash
# Copy and configure the Gunicorn config
cp example.gunicorn.conf.py gunicorn.conf.py
# Edit gunicorn.conf.py with your production settings

# Run with Gunicorn
gunicorn -c gunicorn.conf.py api.main:app
```

4. **Set up Nginx** as reverse proxy (see [DEPLOYMENT.md](DEPLOYMENT.md))

5. **Configure systemd service** for auto-start (see [DEPLOYMENT.md](DEPLOYMENT.md))

For detailed production deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Configuration

Create a `.env` file in the project root with the following settings:

### Database Configuration
```bash
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=classifier_extractor
```

### Server Configuration
```bash
HOST=0.0.0.0
PORT=8000
DEBUG=false  # Set to true for development
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
```

### Storage Configuration

The application supports two storage backends: local filesystem and S3-compatible storage (AWS S3, MinIO, etc.).

#### Local Storage (Development/Small Deployments)

Use local filesystem storage for development or single-server deployments:

```bash
STORAGE_BACKEND=local
DOCUMENT_STORAGE=/path/to/document/storage
```

The system will store all uploaded files in the specified directory, organized by user ID:
```
/path/to/document/storage/
├── 1/           # User ID 1's documents
│   ├── file1.pdf
│   └── file2.docx
├── 2/           # User ID 2's documents
│   └── report.pdf
```

#### S3-Compatible Storage (Production/Scalable Deployments)

Use S3-compatible storage for production deployments with multiple servers or cloud infrastructure:

```bash
STORAGE_BACKEND=s3
S3_ENDPOINT=https://s3.amazonaws.com       # Or MinIO URL: http://minio:9000
S3_BUCKET=documents
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_REGION=us-east-1                        # Optional, AWS region
S3_PREFIX=production                       # Optional, base prefix within bucket
TEMP_DIR=/tmp/document_cache               # Optional, local cache directory
```

**S3 Storage Features:**
- **Multi-tenancy isolation**: Every file is automatically stored under the user's account ID prefix (e.g., `123/document.pdf` or `production/123/document.pdf` with base prefix)
- **Automatic temp directory management**: Files are automatically downloaded to local temp storage when external commands (PDF processing, format conversion) need filesystem access
- **Seamless sync**: Modified files are automatically uploaded back to S3
- **Compatible with**: AWS S3, MinIO, DigitalOcean Spaces, Backblaze B2, Wasabi, and any S3-compatible service
- **Cost-effective**: Pay only for storage used, no local disk requirements
- **Scalable**: Multiple application servers can share the same storage backend

**S3 File Organization:**
```
bucket-name/
├── production/          # Optional base prefix (environment separation)
│   ├── 1/              # User/Account ID 1
│   │   ├── file1.pdf
│   │   └── file2.docx
│   ├── 2/              # User/Account ID 2
│   │   └── report.pdf
```

Without `S3_PREFIX`, files are stored directly under account ID:
```
bucket-name/
├── 1/                  # User/Account ID 1
│   ├── file1.pdf
│   └── file2.docx
├── 2/                  # User/Account ID 2
│   └── report.pdf
```

**MinIO Setup** (Self-hosted S3-compatible storage):
```bash
# Install MinIO (Linux)
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio
./minio server /path/to/data --console-address ":9001"

# Configure application for MinIO
STORAGE_BACKEND=s3
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=documents
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
```

### Authentication & Security
```bash
JWT_SECRET=your-super-secure-jwt-secret-key-minimum-32-characters
```

### LLM Configuration

Choose one of the following providers:

**DeepInfra (Recommended):**
```bash
DEEPINFRA_API_TOKEN=your_deepinfra_token
DEEPINFRA_MODEL_NAME=meta-llama/Llama-2-70b-chat-hf
DEEPINFRA_TEMPERATURE=0.7
DEEPINFRA_MAX_NEW_TOKENS=250
DEEPINFRA_TIMEOUT=360
```

**OpenAI:**
```bash
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4
OPENAI_TEMPERATURE=0.05
OPENAI_MAX_TOKENS=2048
OPENAI_TIMEOUT=360
```

**Ollama (Local):**
```bash
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL_NAME=gemma3n
OLLAMA_TEMPERATURE=0.05
OLLAMA_MAX_TOKENS=2048
OLLAMA_TIMEOUT=360
```

### Additional Configuration
```bash
PROMPT_LOG=/path/to/prompt/log/file  # Optional: Log prompts for debugging
```

### Complete Configuration Example

Here's a complete `.env` file example for development:

```bash
# Database
POSTGRES_USER=devuser
POSTGRES_PASSWORD=devpass
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=classifier_extractor

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=true
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Storage (Local for development)
STORAGE_BACKEND=local
DOCUMENT_STORAGE=/home/user/documents

# LLM Provider (DeepInfra)
DEEPINFRA_API_TOKEN=your_token_here
DEEPINFRA_MODEL_NAME=meta-llama/Llama-3.1-70B-Instruct
DEEPINFRA_EMBEDDING_MODEL=google/embeddinggemma-300m
DEEPINFRA_EMBEDDING_DIMENSIONS=768

# Authentication
JWT_SECRET=development-secret-key-change-in-production
GOOGLE_OAUTH_CLIENT_ID=your_google_oauth_client_id
GOOGLE_OAUTH_CLIENT_SECRET=your_google_oauth_secret
```

For production, use S3 storage and properly secured credentials:

```bash
# Production Storage (S3)
STORAGE_BACKEND=s3
S3_ENDPOINT=https://s3.amazonaws.com
S3_BUCKET=mycompany-documents
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_REGION=us-east-1
S3_PREFIX=production

# Production settings
DEBUG=false
ALLOWED_ORIGINS=https://app.mycompany.com,https://api.mycompany.com
JWT_SECRET=production-secret-minimum-32-chars-long-random-string
```

See [LLMCONFIG.md](LLMCONFIG.md) for detailed LLM configuration options.

## Vector Search for Intelligent Extraction

The system uses PGVector for semantic search to significantly improve fact extraction accuracy and efficiency.

### How It Works

1. **Automatic Embedding Generation**
   - When a document is first processed for extraction, the system automatically:
   - Chunks the document into semantic segments (500 words with 50-word overlap)
   - Generates vector embeddings using OpenAI's embedding API
   - Stores embeddings in PostgreSQL with PGVector extension

2. **Semantic Search**
   - Instead of processing the entire document sequentially:
   - The extraction query is embedded
   - Similar chunks are found using cosine similarity
   - Only the most relevant sections (up to 2048 tokens) are sent to the LLM

3. **Automatic Fallback**
   - If PGVector is unavailable or embeddings fail, the system automatically falls back to traditional chunking
   - Ensures the system always works, even without vector search

### Benefits

- **Improved Accuracy**: Semantic search finds contextually relevant sections, not just keyword matches
- **Cost Reduction**: Sends only relevant text to LLM, reducing token usage by up to 70%
- **Faster Processing**: Less text to process means faster extraction
- **Better Context**: LLM receives focused, relevant information instead of potentially irrelevant chunks

### PGVector Setup

#### PostgreSQL Setup (Ubuntu/Debian)

```bash
# Install pgvector extension
sudo apt-get install postgresql-<version>-pgvector

# The application will automatically enable the extension on startup
```

#### PostgreSQL Setup (macOS)

```bash
# Install via Homebrew
brew install pgvector
```

#### Manual Database Setup

If automatic setup doesn't work, manually run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Or run the migration script:

```bash
psql -U your_user -d your_database -f migrations/001_add_pgvector_support.sql
```

### Configuration

Vector search requires an OpenAI API key for generating embeddings:

```bash
# Required for vector embeddings
OPENAI_API_KEY=sk-your-openai-key-here

# Optional: Use OpenAI-compatible API for embeddings
OPENAI_BASE_URL=http://localhost:11434/v1
```

**Note**: The embedding model (text-embedding-ada-002) is separate from the LLM used for extraction. You can use OpenAI embeddings while using a different provider (DeepInfra, Ollama) for extraction.

### Monitoring Vector Search

Check the application logs to see if vector search is active:

- `"Vector search enabled for fact extraction"` - System using vector search
- `"Using vector search for context retrieval"` - Active search for a query
- `"Using traditional chunking approach"` - Fallback to chunking

For detailed setup instructions, see [docs/PGVECTOR_SETUP.md](docs/PGVECTOR_SETUP.md).

## Usage

### Development Server

Run the development server:
```bash
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the main script directly:
```bash
python api/main.py
```

Access the API documentation at `http://localhost:8000/docs`

### Workbench Application

The system includes a web-based Workbench application for developing and testing classification rules and extractor prompts. Access it at `http://localhost:8000/`

#### Features

The Workbench provides an interactive interface for:

1. **Document Management**
   - Upload documents in various formats (PDF, DOCX, ODT, HTML, text, etc.)
   - View uploaded documents in a side panel
   - Select files for processing and testing

2. **Classifier Development**
   - Create classifier sets to group related categories
   - Define classification categories (e.g., "Invoice", "Contract", "Report")
   - Add search terms with configurable:
     - **Distance**: Maximum Levenshtein distance for fuzzy matching
     - **Weight**: Importance score for the term
   - Use wildcards in terms:
     - `*` - Matches any word or number (e.g., "invoice *" matches "invoice 123", "invoice total")
     - `?` - Matches any single word (e.g., "contract ?" matches "contract date")
     - `#` - Matches any number (e.g., "total #" matches "total 1500")
   - Test classifiers against uploaded documents
   - View classification scores and results in real-time

3. **Extractor Development**
   - Create extractors with custom prompts describing the information to extract
   - **Define structured data fields** - Specify the exact fields you want to extract:
     - **Field Name**: Unique identifier for the field (e.g., "invoice_number", "contract_date", "total_amount")
     - **Field Description**: Instructions for what to extract (e.g., "The invoice number from the document header")
     - Add multiple fields to extract different data points from the same document
   - LLM returns extracted data as **structured JSON** matching your field definitions
   - Test extractors against documents and see results in structured format
   - Iterate on field descriptions to improve extraction accuracy
   - See highlighted citations in marked-up PDFs showing where data was extracted from

4. **Service API Configuration**
   - Generate HTTP Basic Auth credentials for integration endpoints
   - View API endpoint documentation
   - Test integration endpoints directly from the browser

#### Typical Workflow

1. **Upload Documents**: Add a batch of sample documents to test with
2. **Create Classifiers**: Build classification rules to categorize document types
3. **Test & Refine**: Run classifiers and adjust terms, weights, and distances based on results
4. **Build Extractors**: Create extraction prompts for each document type
5. **Test Extraction**: Run extractors and refine prompts and field descriptions
6. **Integrate**: Use the Service API endpoints to integrate with external systems

#### Technology Stack

The Workbench is built with:
- **Lit** - Modern web components framework
- **Vanilla JavaScript** - No heavy frontend framework dependencies
- **Jinja2 Templates** - Server-side rendering
- **RESTful API** - JWT-authenticated backend communication

### Production Deployment

#### Storage Backend Considerations

**When to use Local Storage:**
- Single-server deployments
- Development environments
- Small-scale deployments (<1000 documents)
- Low budget constraints

**When to use S3 Storage:**
- Multi-server deployments (load balancing)
- Cloud-native deployments
- Large-scale deployments (>1000 documents)
- Disaster recovery requirements
- Automatic backups and versioning needed
- Cost-effective long-term storage

#### Production Checklist

- [ ] Set `DEBUG=false` in environment
- [ ] Use strong `JWT_SECRET` (minimum 32 characters)
- [ ] Configure S3 storage for multi-server deployments
- [ ] Set up PostgreSQL with proper user permissions
- [ ] Enable PGVector extension for vector search
- [ ] Configure allowed origins for CORS
- [ ] Set up Nginx as reverse proxy
- [ ] Configure SSL/TLS certificates
- [ ] Set up systemd service for auto-start
- [ ] Configure log rotation
- [ ] Set up monitoring and alerts
- [ ] Regular database backups
- [ ] Configure S3 bucket lifecycle policies (if using S3)

For detailed production deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## API Endpoints

The API provides two types of endpoints:

1. **Workbench Endpoints** (JWT-authenticated) - For the web-based workbench application to manage classifiers, extractors, and documents
2. **Service/Integration Endpoints** (HTTP Basic Auth) - For programmatic integration with external systems

### Service/Integration Endpoints (HTTP Basic Auth)

These endpoints are designed for system-to-system integration and require HTTP Basic Authentication:

#### Document Management
- `POST /service/file` - Upload a document file
- `PUT /service/file/markdown` - Upload markdown content as a document
- `DELETE /service/file/{file_id}` - Remove a document

#### Classification & Extraction
- `GET /service/classifier/{classifier_id}/{file_id}` - Run classifier on a document
- `GET /service/extractor/{extractor_id}/{document_id}` - Run extractor synchronously and get results
- `POST /service/extractor` - Run extractor asynchronously with webhook callback

#### Configuration Discovery
- `GET /service/classifiers` - List all available classifiers (names and IDs)
- `GET /service/extractors` - List all available extractors (names and IDs)

#### PDF Markup
- `GET /service/marked-pdf/{extractor_id}/{file_id}` - Download marked-up PDF with highlighted citations
- `GET /service/marked-pdf-status/{file_id}` - Get status of available marked versions

### Workbench Endpoints (JWT-authenticated)

These endpoints support the interactive workbench application:

#### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and receive JWT token
- `POST /auth/refresh` - Refresh JWT token

#### Account Management
- `GET /account/profile` - Get user profile
- `PUT /account/profile` - Update user profile
- `DELETE /account` - Delete account

#### Documents
- `POST /documents/upload` - Upload a document
- `GET /documents` - List documents
- `GET /documents/{id}` - Get document details
- `DELETE /documents/{id}` - Delete document

#### Classifiers
- `GET /classifiers` - List available classifiers
- `POST /classifiers` - Create a new classifier
- `POST /classifiers/{id}/classify` - Classify a document
- `PUT /classifiers/{id}` - Update classifier
- `DELETE /classifiers/{id}` - Delete classifier

#### Extractors
- `GET /extractors` - List available extractors
- `POST /extractors` - Create a new extractor
- `POST /extractors/{id}/extract` - Extract facts from a document
- `PUT /extractors/{id}` - Update extractor
- `DELETE /extractors/{id}` - Delete extractor

#### API Configuration
- `GET /api_config` - Get API configuration options

## Document Classification Example

```python
from lib.classifier import ClassificationInput, Classification, Term

# Define classifications
classifications = [
    Classification(
        name="Invoice",
        terms=[
            Term(term="invoice", distance=1, weight=5.0),
            Term(term="bill", distance=1, weight=3.0),
            Term(term="amount due", distance=2, weight=4.0)
        ]
    ),
    Classification(
        name="Contract",
        terms=[
            Term(term="agreement", distance=1, weight=5.0),
            Term(term="contract", distance=1, weight=5.0),
            Term(term="party *", distance=2, weight=3.0)  # Wildcard
        ]
    )
]

# Classify document
input_data = ClassificationInput(
    document_text="This is an invoice for services rendered...",
    classifications=classifications
)

# Returns classification results with scores
```

## Fact Extraction Example

```python
from lib.fact_extractor import FactExtractor, ExtractionQuery
from lib.fact_extractor.llm_provider_config import get_llm_config

# Initialize extractor
config = get_llm_config()
extractor = FactExtractor(config)

# Define extraction query
query = ExtractionQuery(
    document_text="Contract between Acme Corp and XYZ Ltd...",
    queries=[
        "What are the names of the parties involved?",
        "What is the contract value?",
        "What is the contract duration?"
    ]
)

# Extract facts
result = extractor.extract(query)
```

## Project Structure

```
classifier_and_extractor/
├── api/                      # FastAPI application
│   ├── main.py              # Application entry point
│   ├── routes/              # API route handlers
│   ├── models/              # Database models
│   │   ├── embedding.py     # PGVector embedding model
│   │   ├── documents.py     # Document model with embeddings relationship
│   │   └── database.py      # Database initialization with PGVector
│   ├── document_extraction/ # Plugin-based document extraction
│   │   ├── extract.py       # Main extraction entry point
│   │   ├── handler_base.py  # Base class for handlers
│   │   └── handlers/        # Format-specific handlers
│   │       ├── document.py  # Office document handler
│   │       ├── html.py      # HTML handler
│   │       ├── pdf.py       # PDF handler
│   │       └── README.md    # Handler documentation
│   ├── util/                # Utility functions
│   │   ├── files_abstraction.py  # Storage backend abstraction (Local/S3)
│   │   ├── upload_document.py    # Document upload handling
│   │   ├── embedder.py      # High-level document embedding interface
│   │   ├── vector_utils.py  # Vector search and embedding utilities
│   │   └── extraction_core.py  # Extraction with vector search support
│   ├── pdf_markup/          # PDF highlighting functionality
│   │   └── highlight_pdf.py # PDF annotation with citations
│   ├── to_pdf/              # Document conversion
│   │   └── converter.py     # Format to PDF conversion
│   ├── public/              # Static files
│   └── templates/           # HTML templates
├── lib/                      # Core libraries
│   ├── classifier.py        # Document classification
│   └── fact_extractor/      # Fact extraction
│       ├── fact_extractor.py  # With vector search integration
│       ├── document_chunker.py
│       ├── prompt_builder.py
│       ├── models.py
│       └── llm_provider_config.py
├── migrations/               # Database migration scripts
│   └── 001_add_pgvector_support.sql
├── docs/                     # Documentation
│   └── PGVECTOR_SETUP.md    # PGVector setup guide
├── testing/                  # Test files and sample documents
├── requirements.txt          # Python dependencies (includes boto3 for S3)
├── example.gunicorn.conf.py # Gunicorn configuration template
├── .env.example             # Environment variables template
├── DEPLOYMENT.md            # Production deployment guide
├── LLMCONFIG.md             # LLM configuration guide
├── MIGRATION_GUIDE.md       # Migration guide for updates
└── LICENSE.txt              # GNU GPL v3 License
```

## Testing

Run tests using:
```bash
python testing.py
```

Sample test documents are available in `testing/sample_files/`.

## Extending the Document Extraction Framework

The plugin-based architecture makes it easy to add support for new file formats. To create a custom handler:

### 1. Create a Handler Class

Create a new file in `api/document_extraction/handlers/`:

```python
# handlers/my_format.py
from api.document_extraction.handler_base import DocumentExtractionBase
from api.document_extraction.extract import DocumentDecodeException

class MyFormatHandler(DocumentExtractionBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def format() -> list[str]:
        """Return list of supported file extensions (without dots)"""
        return ['xyz', 'abc']

    def extract(self, input_file: str) -> str:
        """Extract and convert content to Markdown or plain text"""
        # Your conversion logic here
        # Use self.temp_dir for intermediate files
        # Raise DocumentDecodeException on failure
        return converted_content
```

### 2. No Configuration Needed

The system automatically discovers your handler at runtime by:
- Scanning the `handlers/` directory
- Finding classes that inherit from `DocumentExtractionBase`
- Calling the `format()` method to determine supported extensions

### 3. Use Base Class Utilities

Your handler can leverage these utility methods:
- `self.pandoc_convert(file_name, type_from, exception_message)` - Convert via Pandoc
- `find_exe(command_name)` - Locate system executables (pandoc, pdftotext, etc.)
- `is_real_words(content)` - Validate extracted text quality
- `self.temp_dir` - Temporary directory for intermediate processing

See `api/document_extraction/handlers/README.md` for detailed documentation and examples.

## Migration Guide

When upgrading to newer versions, refer to [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for breaking changes and migration instructions.

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE.txt](LICENSE.txt) file for details.

## Contributing

Contributions are welcome! Please ensure your code follows the project structure and includes appropriate tests.

## Support

For issues, questions, or feature requests, please open an issue on the project repository.

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Classification powered by [RapidFuzz](https://github.com/maxbachmann/RapidFuzz)
- LLM integration via [LangChain](https://www.langchain.com/)
- Vector search powered by [PGVector](https://github.com/pgvector/pgvector)
- Document processing with [PyMuPDF](https://pymupdf.readthedocs.io/), [marker-pdf](https://github.com/VikParuchuri/marker), and LibreOffice