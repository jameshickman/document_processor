# Classifier and Extractor API - Project Analysis

## Executive Summary

The Classifier and Extractor API is a comprehensive document processing platform designed to automate the classification and extraction of information from diverse document formats. Built on FastAPI, this system leverages Large Language Models (LLMs) and vector search technology to transform unstructured document content into structured, actionable data. The platform serves dual purposes: enabling rapid development of document processing workflows through an intuitive web-based workbench, and providing robust API endpoints for seamless integration into existing business systems. With support for multiple document formats, flexible storage backends, and multiple LLM providers, the system offers a scalable solution for organizations looking to automate document-centric processes and extract valuable insights from their document repositories.

## Overview
This is a FastAPI-based document processing system that provides intelligent document classification and fact extraction using Large Language Models (LLMs). The system supports fuzzy matching with wildcards for classification and uses advanced LLM providers for accurate information extraction.

## Key Features

### Document Processing Framework
- **Plugin-based document extraction** with automatic format detection
- **Multi-format support**: PDF, DOCX, HTML, TXT, MD, and many other formats
- **Format conversion pipeline** using LibreOffice and Pandoc for complex documents
- **Markdown-first conversion** with fallback to plain text

### Document Classification
- **Fuzzy matching** with Levenshtein distance scoring
- **Wildcard support** for flexible pattern matching (`*`, `?`, `#`)
- Configurable matching distance and term weights
- Fast in-memory classification without LLM dependencies

### Fact Extraction
- LLM-powered information extraction from documents
- **Vector Search with PGVector** for semantic search
- Multiple LLM provider support (DeepInfra, OpenAI, Ollama)
- Document chunking for large files
- Intelligent prompt building

### API Features
- RESTful API endpoints for documents, classifiers, and extractors
- JWT-based authentication and authorization
- Role-based access control (RBAC)
- Document upload and storage management
- PostgreSQL database backend with PGVector support

## Architecture

### Project Structure
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
├── docs/                     # Documentation
├── testing/                  # Test files and sample documents
├── requirements.txt          # Python dependencies
```

### Core Components

#### 1. Document Extraction Framework
The system uses a plugin-based architecture for document extraction:
- **Automatic format detection** routes files to appropriate handlers
- **Dynamic handler discovery** automatically detects new format handlers
- **Extensible architecture** allows adding new file formats by dropping handler classes
- **Multi-stage conversion pipeline** handles complex document formats

#### 2. Classification Engine
- Uses fuzzy matching with Levenshtein distance
- Supports wildcard patterns for flexible matching
- In-memory processing for fast classification
- Configurable term weights and distance thresholds

#### 3. Fact Extraction Engine
- LLM-powered extraction with multiple provider support
- Vector search with PGVector for semantic context retrieval
- Automatic fallback to traditional chunking if PGVector unavailable
- Structured JSON output based on defined field specifications

#### 4. Storage Abstraction Layer
- Supports both local filesystem and S3-compatible storage
- Multi-tenancy isolation with user ID prefixes
- Automatic temp directory management for external commands
- Seamless sync between local and remote storage

## Technical Stack

### Backend Framework
- **FastAPI** - Modern, fast web framework for building APIs
- **Pydantic** - Data validation and settings management
- **SQLAlchemy** - Database ORM
- **PostgreSQL** - Primary database with PGVector extension

### Document Processing
- **LibreOffice** - For converting office documents
- **Pandoc** - For HTML to Markdown conversion
- **Poppler-utils** - For PDF text extraction
- **Marker-PDF** - For PDF processing

### LLM Integration
- **OpenAI** - Official OpenAI GPT models
- **Anthropic** - Claude models
- **DeepInfra** - Cloud-hosted LLMs
- **Ollama** - Local LLM service
- **LangChain** - LLM orchestration

### Vector Search
- **PGVector** - PostgreSQL extension for vector similarity search
- **Sentence Transformers** - Local embedding models
- **OpenAI Embeddings** - Cloud-based embedding models

### Frontend (Workbench)
- **Lit** - Modern web components framework
- **Vanilla JavaScript** - No heavy frontend framework dependencies
- **Jinja2 Templates** - Server-side rendering

## Configuration

### Environment Variables
The system uses a comprehensive environment configuration system:

- **Database**: PostgreSQL connection settings
- **Storage**: Local or S3-compatible storage configuration
- **LLM Providers**: Multiple LLM provider configurations
- **Embedding**: Vector embedding backend selection
- **Security**: JWT authentication and CORS settings

### Storage Backends
Two storage backends are supported:
1. **Local Storage**: Simple filesystem storage for development
2. **S3-Compatible Storage**: Scalable storage for production (AWS S3, MinIO, etc.)

## API Endpoints

### Workbench Endpoints (JWT-authenticated)
- Authentication and account management
- Document upload and management
- Classifier creation and testing
- Extractor development and testing

### Service/Integration Endpoints (HTTP Basic Auth)
- Programmatic document upload
- Classification and extraction APIs
- Configuration discovery endpoints
- PDF markup download endpoints

## Workbench Application

The system includes a web-based Workbench for developing and testing:

### Features
- Interactive document management
- Visual classifier development
- Extractor prompt testing
- Real-time results and scoring
- PDF markup with citation highlights

### Typical Workflow
1. Upload sample documents
2. Create and test classifiers
3. Build extraction prompts
4. Test and refine extractions
5. Integrate via service APIs

## Deployment

### Development Setup
- Virtual environment with Python 3.8+
- PostgreSQL with PGVector extension
- System dependencies (LibreOffice, Pandoc, poppler-utils)
- Environment configuration

### Production Setup
- Gunicorn for WSGI server
- Nginx as reverse proxy
- S3-compatible storage recommended
- Proper security configurations
- Monitoring and logging setup

## Dependencies

Key Python dependencies include:
- FastAPI for web framework
- SQLAlchemy for database ORM
- PGVector for vector search
- LangChain for LLM orchestration
- Various document processing libraries
- boto3 for S3 compatibility

## Use Cases

This system is ideal for:
- Document classification and routing
- Information extraction from unstructured documents
- Automated data entry from documents
- Content analysis and categorization
- Document processing workflows
- Building document-based AI applications

## Extensions

The system is designed to be extensible:
- New document format handlers can be added
- Multiple LLM providers can be integrated
- Custom classification algorithms can be implemented
- Additional storage backends can be supported
- New API endpoints can be added