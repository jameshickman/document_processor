# Usage Tracking Implementation Plan

## Executive Summary

This document outlines the implementation plan for adding comprehensive usage tracking and reporting to the Classifier and Extractor API. The feature will enable accurate billing based on LLM model usage, track Workbench vs API usage patterns, and provide both self-service usage viewing (for all users) and administrative reporting interfaces (for users with the reporting role).

**Key Features:**
- **Self-Service Usage**: All authenticated users can view their own usage data, graphs, and download CSV reports
- **Administrative Reporting**: Users with the "reporting" role can view aggregated usage across all accounts with filtering by user, timeframe, and model
- **Multi-tenancy**: All tracking respects account boundaries; users can only see their own data unless they have reporting privileges

## Table of Contents

1. [Overview](#overview)
2. [Architecture Design](#architecture-design)
3. [Database Schema Changes](#database-schema-changes)
4. [Implementation Phases](#implementation-phases)
5. [Tracking Integration Points](#tracking-integration-points)
6. [API Endpoints](#api-endpoints)
7. [RBAC Extensions](#rbac-extensions)
8. [Frontend Dashboard](#frontend-dashboard)
9. [Testing Strategy](#testing-strategy)
10. [Migration Plan](#migration-plan)
11. [Security Considerations](#security-considerations)

---

## 1. Overview

### 1.1 Requirements Summary

Based on `USAGE_TRACKING.md`, the system must track:

**Usage Metrics:**
- Daily totals per user account
- Usage by specific LLM model
- Workbench vs API usage
- Document storage consumption (physical/object-store)
- Extraction and classification operations

**Reporting Features:**
- Graph of usage over time
- User selection filtering (reporting role only)
- Timeframe selection
- Model breakdown analysis
- CSV export capability

**Access Control:**
- **All users** can view their own usage history
- New "reporting" role for administrative users to view usage across all users
- Reporting interface in dashboard (available to all users, with scoped access)
- REST API endpoints for both self-service and administrative access

### 1.2 Design Principles

1. **Minimal Performance Impact**: Tracking should be asynchronous where possible
2. **Multi-Tenancy**: All tracking respects account boundaries
3. **Accurate Cost Attribution**: Track LLM model usage for precise billing
4. **Scalability**: Design for potential high-volume tracking
5. **Auditability**: Immutable tracking records with timestamps
6. **Privacy**: Aggregate data appropriately, no sensitive content in tracking

---

## 2. Architecture Design

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
├─────────────────────────────────────────────────────────────┤
│  Extractors  │  Classifiers  │  Documents  │  Auth/Account  │
└──────┬───────────────┬───────────────┬─────────────┬────────┘
       │               │               │             │
       └───────────────┴───────────────┴─────────────┘
                            │
                   ┌────────▼────────┐
                   │  Usage Tracker  │  ← New Component
                   │   (Middleware)  │
                   └────────┬────────┘
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
┌──────▼──────┐   ┌─────────▼────────┐   ┌──────▼──────┐
│ usage_logs  │   │ usage_summaries  │   │ storage_use │
│  (events)   │   │   (daily roll)   │   │  (daily)    │
└─────────────┘   └──────────────────┘   └─────────────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                   ┌────────▼────────┐
                   │ Reporting API   │  ← New Endpoints
                   │   & Dashboard   │
                   └─────────────────┘
```

### 2.2 Data Flow

**Tracking Flow:**
1. User performs action (extraction, classification, upload)
2. Operation executes normally
3. Background task logs usage event to `usage_logs`
4. Nightly aggregation job rolls up to `usage_summaries`
5. Storage calculation job updates `storage_usage`

**Reporting Flow:**
1. Admin user requests report via dashboard or API
2. Query `usage_summaries` for aggregate data
3. Join with `accounts` and `llm_models` for metadata
4. Format response (JSON for API, CSV for download)
5. Apply timeframe and filtering based on request

---

## 3. Database Schema Changes

### 3.1 New Tables

#### 3.1.1 `usage_logs` (Event Log)

Immutable log of every tracked operation.

```sql
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
    ip_address INET,

    -- Indexes
    CONSTRAINT check_operation_type CHECK (operation_type IN ('extraction', 'classification', 'embedding', 'upload', 'download')),
    CONSTRAINT check_source_type CHECK (source_type IN ('workbench', 'api')),
    CONSTRAINT check_status CHECK (status IN ('success', 'failure', 'partial'))
);

-- Indexes for efficient querying
CREATE INDEX idx_usage_logs_account_timestamp ON usage_logs(account_id, timestamp DESC);
CREATE INDEX idx_usage_logs_operation_type ON usage_logs(operation_type);
CREATE INDEX idx_usage_logs_timestamp ON usage_logs(timestamp DESC);
CREATE INDEX idx_usage_logs_provider_model ON usage_logs(provider, model_name) WHERE provider IS NOT NULL;
CREATE INDEX idx_usage_logs_source_type ON usage_logs(source_type);
```

#### 3.1.2 `usage_summaries` (Daily Aggregates)

Pre-aggregated daily summaries for fast reporting.

```sql
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
```

#### 3.1.3 `usage_summaries_by_model` (Daily Model Breakdown)

Per-model usage for billing and cost attribution.

```sql
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
```

#### 3.1.4 `storage_usage` (Daily Storage Tracking)

Track physical storage consumption per account.

```sql
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
```

### 3.2 Schema Modifications to Existing Tables

#### 3.2.1 `accounts` Table

Add reporting role and usage tracking flags.

```sql
-- New columns for accounts table
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS roles TEXT[] DEFAULT '{}';
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS usage_tracking_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS usage_limit_tokens BIGINT;  -- Optional token limit per month
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS usage_alert_threshold FLOAT;  -- Alert at % of limit (e.g., 0.8 = 80%)
```

---

## 4. Implementation Phases

### Phase 1: Database and Core Tracking (Week 1-2)

**Goal:** Set up database schema and implement basic event tracking.

**Tasks:**
1. Create migration script for new tables
2. Create SQLAlchemy models for tracking tables
3. Implement `UsageTracker` service class
4. Add basic event logging (extractions only)
5. Unit tests for tracking service

**Deliverables:**
- `/migrations/003_usage_tracking_schema.sql`
- `/api/models/usage_tracking.py`
- `/api/services/usage_tracker.py`
- Tests in `/api/tests/test_usage_tracker.py`

### Phase 2: Tracking Integration (Week 2-3)

**Goal:** Integrate tracking into all operation endpoints.

**Tasks:**
1. Add tracking to extraction endpoints
2. Add tracking to classification endpoints
3. Add tracking to document upload
4. Add tracking to embedding generation
5. Implement request source detection (workbench vs API)
6. Add token counting for LLM operations

**Deliverables:**
- Modified `/api/util/extraction_core.py`
- Modified `/api/util/extraction_background.py`
- Modified `/api/routes/service.py`
- Modified `/api/routes/documents.py`
- Modified `/api/routes/extractors.py`

### Phase 3: Aggregation and Storage Calculation (Week 3-4)

**Goal:** Implement daily rollup jobs and storage tracking.

**Tasks:**
1. Create aggregation job to roll up `usage_logs` to `usage_summaries`
2. Create storage calculation job
3. Implement background scheduler (APScheduler or similar)
4. Add job monitoring and error handling
5. Create admin endpoint to trigger manual rollup

**Deliverables:**
- `/api/jobs/usage_aggregation.py`
- `/api/jobs/storage_calculation.py`
- `/api/jobs/scheduler.py`
- Job configuration in `.env`

### Phase 4: RBAC and Usage API (Week 4-5)

**Goal:** Implement self-service usage endpoints and reporting role with administrative API.

**Tasks:**
1. Extend RBAC system with "reporting" role
2. Create self-service usage API endpoints (all users)
3. Create administrative reporting API endpoints (reporting role)
4. Implement filtering and aggregation logic
5. Add CSV export functionality for both endpoint types
6. Add API documentation (OpenAPI)

**Deliverables:**
- Modified `/api/rbac.py`
- `/api/routes/usage.py` (self-service endpoints)
- `/api/routes/reporting.py` (administrative endpoints)
- `/api/services/usage_service.py`
- `/api/services/reporting_service.py`
- `/api/util/csv_export.py`

### Phase 5: Dashboard UI (Week 5-6)

**Goal:** Build usage interface in the dashboard for all users with role-based features.

**Tasks:**
1. Create usage section template (visible to all users)
2. Implement usage graphs (Chart.js or similar)
3. Add filtering controls (date range for all; users/models for reporting role)
4. Add CSV download button
5. Add role-based UI rendering (hide account selector for non-reporting users)
6. Implement dual-mode component (self-service vs administrative)

**Deliverables:**
- `/api/templates/sections/usage.j2`
- `/api/public/js/components/usage_dashboard.js` (role-aware component)
- `/api/public/js/components/usage_chart.js`
- `/api/public/js/lib/csv_downloader.js`
- `/api/public/css/usage.css`

### Phase 6: Testing and Documentation (Week 6-7)

**Goal:** Comprehensive testing and documentation.

**Tasks:**
1. Integration tests for tracking flow
2. API endpoint tests
3. Performance testing for aggregation jobs
4. User documentation
5. API documentation
6. Admin guide for reporting

**Deliverables:**
- Test suite in `/api/tests/test_reporting_*.py`
- `/docs/USAGE_TRACKING_GUIDE.md`
- `/docs/REPORTING_API.md`
- Updated API documentation

### Phase 7: Deployment and Monitoring (Week 7)

**Goal:** Deploy to production and set up monitoring.

**Tasks:**
1. Database migration scripts
2. Environment variable configuration
3. Job scheduler deployment
4. Monitoring and alerting setup
5. Performance tuning
6. User training

---

## 5. Tracking Integration Points

### 5.1 Extraction Operations

**Location:** `/api/util/extraction_core.py`, `/api/util/extraction_background.py`

**Integration:**

```python
from api.services.usage_tracker import UsageTracker

async def run_extraction(
    extractor_id: int,
    document_id: int,
    db_session: Session,
    user_info: dict
):
    start_time = time.time()
    tracker = UsageTracker(db_session)

    try:
        # Existing extraction logic
        result = await perform_extraction(...)

        # Track successful extraction
        await tracker.log_extraction(
            account_id=user_info['user_id'],
            document_id=document_id,
            extractor_id=extractor_id,
            llm_model_id=extractor.llm_model_id,
            provider=result.provider,
            model_name=result.model_name,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            duration_ms=int((time.time() - start_time) * 1000),
            status='success',
            source_type=_detect_source_type(request)
        )

        return result

    except Exception as e:
        # Track failed extraction
        await tracker.log_extraction(
            account_id=user_info['user_id'],
            document_id=document_id,
            extractor_id=extractor_id,
            duration_ms=int((time.time() - start_time) * 1000),
            status='failure',
            error_message=str(e),
            source_type=_detect_source_type(request)
        )
        raise
```

### 5.2 Classification Operations

**Location:** `/api/routes/service.py`, classifier endpoints

**Integration:**

```python
@router.get("/classifier/{classifier_id}/{file_id}")
async def run_classification(
    classifier_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    user_info: dict = Depends(get_basic_auth)
):
    start_time = time.time()
    tracker = UsageTracker(db)

    try:
        # Existing classification logic
        result = classifier.classify(document)

        # Track classification
        await tracker.log_classification(
            account_id=user_info['user_id'],
            document_id=file_id,
            classifier_id=classifier_id,
            duration_ms=int((time.time() - start_time) * 1000),
            status='success',
            source_type='api'  # This endpoint is API-only
        )

        return result

    except Exception as e:
        await tracker.log_classification(
            account_id=user_info['user_id'],
            document_id=file_id,
            classifier_id=classifier_id,
            duration_ms=int((time.time() - start_time) * 1000),
            status='failure',
            error_message=str(e),
            source_type='api'
        )
        raise
```

### 5.3 Document Upload

**Location:** `/api/util/upload_document.py`

**Integration:**

```python
async def upload_document(
    file_content: bytes,
    file_name: str,
    account_id: int,
    db: Session,
    source_type: str = 'workbench'
):
    start_time = time.time()
    tracker = UsageTracker(db)

    try:
        # Existing upload logic
        document = await process_upload(file_content, file_name, account_id)

        # Track upload
        await tracker.log_upload(
            account_id=account_id,
            document_id=document.id,
            bytes_stored=len(file_content),
            duration_ms=int((time.time() - start_time) * 1000),
            status='success',
            source_type=source_type
        )

        return document

    except Exception as e:
        await tracker.log_upload(
            account_id=account_id,
            bytes_stored=len(file_content),
            duration_ms=int((time.time() - start_time) * 1000),
            status='failure',
            error_message=str(e),
            source_type=source_type
        )
        raise
```

### 5.4 Embedding Generation

**Location:** `/api/util/embedder.py`

**Integration:**

```python
async def generate_embeddings(
    document_id: int,
    account_id: int,
    db: Session
):
    start_time = time.time()
    tracker = UsageTracker(db)

    try:
        # Existing embedding logic
        embeddings = await create_embeddings(document)

        # Track embedding generation
        await tracker.log_embedding(
            account_id=account_id,
            document_id=document_id,
            provider=embedding_config.provider,
            model_name=embedding_config.model,
            input_tokens=calculate_embedding_tokens(document),
            duration_ms=int((time.time() - start_time) * 1000),
            status='success',
            source_type='workbench'  # Embeddings are typically background
        )

        return embeddings

    except Exception as e:
        await tracker.log_embedding(
            account_id=account_id,
            document_id=document_id,
            duration_ms=int((time.time() - start_time) * 1000),
            status='failure',
            error_message=str(e),
            source_type='workbench'
        )
        raise
```

### 5.5 Source Type Detection

**Helper Function:**

```python
def _detect_source_type(request: Request) -> str:
    """
    Detect if request came from workbench or API.

    Strategies:
    1. Check for JWT token (workbench) vs Basic Auth (API)
    2. Check User-Agent header
    3. Check Referer header
    4. Default to 'api' if uncertain
    """
    auth_header = request.headers.get('Authorization', '')

    # JWT token indicates workbench
    if auth_header.startswith('Bearer '):
        return 'workbench'

    # Basic auth indicates API
    if auth_header.startswith('Basic '):
        return 'api'

    # Check User-Agent for browser patterns
    user_agent = request.headers.get('User-Agent', '').lower()
    if any(browser in user_agent for browser in ['mozilla', 'chrome', 'safari', 'firefox']):
        return 'workbench'

    # Check if request came from the dashboard
    referer = request.headers.get('Referer', '')
    if referer and '/dashboard' in referer:
        return 'workbench'

    # Default to API
    return 'api'
```

---

## 6. API Endpoints

### 6.1 Self-Service Usage Endpoints

**Base Path:** `/usage`

**Authentication:** JWT token (any authenticated user)

**Access:** Users can only view their own usage data. Account ID is derived from JWT token.

#### 6.1.1 Get My Usage Summary

```
GET /usage/my-summary
```

**Query Parameters:**
- `start_date` (required): ISO 8601 date (e.g., "2024-01-01")
- `end_date` (required): ISO 8601 date
- `group_by` (optional): "day" | "week" | "month" (default: "day")

**Response:**
```json
{
  "account_id": 1,
  "account_name": "Acme Corp",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "group_by": "day",
  "data": [
    {
      "date": "2024-01-01",
      "total_operations": 150,
      "workbench_operations": 100,
      "api_operations": 50,
      "extractions": 80,
      "classifications": 70,
      "total_tokens": 125000,
      "input_tokens": 100000,
      "output_tokens": 25000,
      "successful_operations": 148,
      "failed_operations": 2
    }
  ],
  "total_records": 31
}
```

#### 6.1.2 Get My Model Usage

```
GET /usage/my-models
```

**Query Parameters:**
- `start_date` (required)
- `end_date` (required)
- `provider` (optional): Filter by provider
- `model_name` (optional): Filter by model name

**Response:**
```json
{
  "account_id": 1,
  "account_name": "Acme Corp",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "data": [
    {
      "date": "2024-01-01",
      "provider": "openai",
      "model_name": "gpt-4",
      "operation_count": 50,
      "input_tokens": 40000,
      "output_tokens": 10000,
      "total_tokens": 50000,
      "avg_duration_ms": 2500,
      "successful_operations": 49,
      "failed_operations": 1
    }
  ]
}
```

#### 6.1.3 Get My Storage Usage

```
GET /usage/my-storage
```

**Query Parameters:**
- `start_date` (required)
- `end_date` (required)

**Response:**
```json
{
  "account_id": 1,
  "account_name": "Acme Corp",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "data": [
    {
      "date": "2024-01-01",
      "total_bytes": 5368709120,
      "total_gb": 5.0,
      "document_count": 1250,
      "storage_backend": "s3",
      "pdf_bytes": 4294967296,
      "docx_bytes": 1073741824,
      "html_bytes": 0,
      "other_bytes": 0
    }
  ]
}
```

#### 6.1.4 Export My Usage to CSV

```
GET /usage/my-export/csv
```

**Query Parameters:**
- Same as other self-service endpoints
- `report_type` (required): "summary" | "by_model" | "storage"

**Response:**
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename="my_usage_report_2024-01-01_2024-01-31.csv"`

### 6.2 Administrative Reporting Endpoints

**Base Path:** `/reporting`

**Authentication:** JWT token with "reporting" role

**Access:** Users with reporting role can view usage data across all accounts with filtering options.

#### 6.2.1 Get Usage Summary

```
GET /reporting/usage/summary
```

**Query Parameters:**
- `start_date` (required): ISO 8601 date (e.g., "2024-01-01")
- `end_date` (required): ISO 8601 date
- `account_id` (optional): Filter by specific account (omit for all accounts)
- `group_by` (optional): "day" | "week" | "month" (default: "day")

**Response:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "group_by": "day",
  "data": [
    {
      "date": "2024-01-01",
      "account_id": 1,
      "account_name": "Acme Corp",
      "total_operations": 150,
      "workbench_operations": 100,
      "api_operations": 50,
      "extractions": 80,
      "classifications": 70,
      "total_tokens": 125000,
      "input_tokens": 100000,
      "output_tokens": 25000,
      "successful_operations": 148,
      "failed_operations": 2
    }
  ],
  "total_records": 31
}
```

#### 6.2.2 Get Model Usage

```
GET /reporting/usage/by-model
```

**Query Parameters:**
- `start_date` (required)
- `end_date` (required)
- `account_id` (optional)
- `provider` (optional): Filter by provider
- `model_name` (optional): Filter by model name

**Response:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "data": [
    {
      "date": "2024-01-01",
      "account_id": 1,
      "account_name": "Acme Corp",
      "provider": "openai",
      "model_name": "gpt-4",
      "operation_count": 50,
      "input_tokens": 40000,
      "output_tokens": 10000,
      "total_tokens": 50000,
      "avg_duration_ms": 2500,
      "successful_operations": 49,
      "failed_operations": 1
    },
    {
      "date": "2024-01-01",
      "account_id": 1,
      "account_name": "Acme Corp",
      "provider": "deepinfra",
      "model_name": "meta-llama/Llama-2-70b-chat-hf",
      "operation_count": 30,
      "input_tokens": 60000,
      "output_tokens": 15000,
      "total_tokens": 75000,
      "avg_duration_ms": 1800,
      "successful_operations": 30,
      "failed_operations": 0
    }
  ]
}
```

#### 6.2.3 Get Storage Usage

```
GET /reporting/storage
```

**Query Parameters:**
- `start_date` (required)
- `end_date` (required)
- `account_id` (optional)

**Response:**
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "data": [
    {
      "date": "2024-01-01",
      "account_id": 1,
      "account_name": "Acme Corp",
      "total_bytes": 5368709120,
      "total_gb": 5.0,
      "document_count": 1250,
      "storage_backend": "s3",
      "pdf_bytes": 4294967296,
      "docx_bytes": 1073741824,
      "html_bytes": 0,
      "other_bytes": 0
    }
  ]
}
```

#### 6.2.4 Get Event Logs

```
GET /reporting/logs
```

**Query Parameters:**
- `start_date` (required)
- `end_date` (required)
- `account_id` (optional)
- `operation_type` (optional)
- `source_type` (optional)
- `status` (optional)
- `limit` (default: 100, max: 1000)
- `offset` (default: 0)

**Response:**
```json
{
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-01T23:59:59Z",
  "filters": {
    "account_id": 1,
    "operation_type": "extraction"
  },
  "pagination": {
    "limit": 100,
    "offset": 0,
    "total": 523
  },
  "data": [
    {
      "id": 12345,
      "timestamp": "2024-01-01T14:23:45Z",
      "account_id": 1,
      "account_name": "Acme Corp",
      "operation_type": "extraction",
      "source_type": "api",
      "document_id": 567,
      "extractor_id": 12,
      "provider": "openai",
      "model_name": "gpt-4",
      "input_tokens": 2500,
      "output_tokens": 500,
      "total_tokens": 3000,
      "duration_ms": 2340,
      "status": "success"
    }
  ]
}
```

#### 6.2.5 Export to CSV

```
GET /reporting/export/csv
```

**Query Parameters:**
- Same as other endpoints
- `report_type` (required): "summary" | "by_model" | "storage" | "logs"

**Response:**
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename="usage_report_2024-01-01_2024-01-31.csv"`

**CSV Format (summary):**
```csv
Date,Account ID,Account Name,Total Operations,Workbench Operations,API Operations,Extractions,Classifications,Total Tokens,Input Tokens,Output Tokens,Successful,Failed
2024-01-01,1,Acme Corp,150,100,50,80,70,125000,100000,25000,148,2
```

#### 6.2.6 Get Account List

```
GET /reporting/accounts
```

**Query Parameters:**
- `active_only` (default: true)

**Response:**
```json
{
  "accounts": [
    {
      "id": 1,
      "name": "Acme Corp",
      "email": "admin@acme.com",
      "active": true,
      "created_at": "2023-06-15T10:00:00Z"
    }
  ]
}
```

### 6.3 Admin Endpoints

**Base Path:** `/admin/usage`

**Authentication:** JWT token with "admin" role

#### 6.3.1 Trigger Aggregation

```
POST /admin/usage/aggregate
```

**Request Body:**
```json
{
  "date": "2024-01-01",  // Optional, defaults to yesterday
  "force": false         // Force re-aggregation even if already done
}
```

**Response:**
```json
{
  "status": "success",
  "date": "2024-01-01",
  "records_processed": 1523,
  "summaries_created": 45,
  "duration_ms": 3450
}
```

#### 6.3.2 Calculate Storage

```
POST /admin/usage/calculate-storage
```

**Request Body:**
```json
{
  "date": "2024-01-01",  // Optional, defaults to today
  "account_id": 1        // Optional, calculate for specific account
}
```

**Response:**
```json
{
  "status": "success",
  "date": "2024-01-01",
  "accounts_processed": 45,
  "total_bytes": 107374182400,
  "duration_ms": 8230
}
```

---

## 7. RBAC Extensions

### 7.1 Role Definitions

**Existing Roles (from current implementation):**
- **User** (default): Access to own resources, including own usage data
- **Admin**: Full system access, including all usage data and system administration

**New Role:**
- **Reporting**: Read-only access to usage data across all accounts (administrative reporting)

### 7.2 Role Assignment

**Database Schema:**

The `accounts.roles` column (TEXT[]) will store multiple roles:

```sql
-- Example role assignments
UPDATE accounts SET roles = ARRAY['user'] WHERE id = 1;  -- Regular user
UPDATE accounts SET roles = ARRAY['user', 'reporting'] WHERE id = 2;  -- User with reporting access
UPDATE accounts SET roles = ARRAY['user', 'admin'] WHERE id = 3;  -- Admin
```

### 7.3 RBAC Implementation

**Modified:** `/api/rbac.py`

```python
from enum import Enum

class Role(str, Enum):
    USER = "user"
    REPORTING = "reporting"
    ADMIN = "admin"

# Dependency for self-service usage endpoints (all authenticated users)
def get_current_user(
    token: str = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
):
    """
    Verify user is authenticated and return user info.
    All authenticated users can access their own usage data.
    """
    try:
        payload = jwt.decode(
            token.credentials,
            JWT_SECRET,
            algorithms=["HS256"]
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# New dependency for administrative reporting endpoints
def require_reporting_role(
    token: str = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
):
    """
    Verify user has reporting or admin role for cross-account access.
    """
    try:
        payload = jwt.decode(
            token.credentials,
            JWT_SECRET,
            algorithms=["HS256"]
        )

        user_roles = payload.get('roles', [])

        # Admin automatically has reporting access
        if Role.ADMIN in user_roles or Role.REPORTING in user_roles:
            return payload

        raise HTTPException(
            status_code=403,
            detail="Reporting access required"
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 7.4 JWT Token Updates

**Modified:** `/api/routes/auth.py`

```python
def create_jwt_token(account: Account) -> str:
    """
    Create JWT token with roles claim.
    """
    payload = {
        "username": account.email,
        "email": account.email,
        "name": account.name,
        "user_id": account.id,
        "roles": account.roles or ["user"],  # Include roles
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }

    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
```

### 7.5 Role Management Endpoints

**New:** `/api/routes/admin.py`

```python
@router.post("/admin/accounts/{account_id}/roles")
async def update_account_roles(
    account_id: int,
    roles: List[Role],
    db: Session = Depends(get_db),
    user_info: dict = Depends(require_admin_role)
):
    """
    Update roles for an account (admin only).
    """
    account = db.query(models.Account).filter(
        models.Account.id == account_id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.roles = [r.value for r in roles]
    db.commit()

    return {
        "account_id": account_id,
        "roles": account.roles
    }

@router.get("/admin/accounts/{account_id}/roles")
async def get_account_roles(
    account_id: int,
    db: Session = Depends(get_db),
    user_info: dict = Depends(require_admin_role)
):
    """
    Get roles for an account (admin only).
    """
    account = db.query(models.Account).filter(
        models.Account.id == account_id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return {
        "account_id": account_id,
        "roles": account.roles or ["user"]
    }
```

---

## 8. Frontend Dashboard

### 8.1 Navigation Menu Update

**Modified:** `/api/public/js/lib/menu.js`

Add usage menu item (visible to all users):

```javascript
const menuItems = [
    { id: 'files', label: 'Documents', icon: 'file-text' },
    { id: 'extractors', label: 'Extractors', icon: 'search' },
    { id: 'classifiers', label: 'Classifiers', icon: 'filter' },
    { id: 'models', label: 'Models', icon: 'cpu' },
    { id: 'api_setup', label: 'API', icon: 'key' },
    // New item - visible to all users
    { id: 'usage', label: 'Usage', icon: 'bar-chart-2' },
    { id: 'about', label: 'About', icon: 'info' }
];

// Menu item is always visible; content will be scoped based on user role
// - Regular users see only their own usage
// - Users with reporting role see all users with filtering options
```

### 8.2 Usage Dashboard Component

**New File:** `/api/public/js/components/usage_dashboard.js`

```javascript
class UsageDashboard extends ComponentBase {
    constructor() {
        super();
        this.currentView = 'summary';  // 'summary', 'by_model', 'storage'
        this.dateRange = {
            start: this.getDefaultStartDate(),
            end: this.getDefaultEndDate()
        };
        this.filters = {
            accountId: null,  // Only used by reporting role
            provider: null,
            modelName: null
        };
        this.chart = null;
        this.hasReportingRole = false;  // Determined from user token
        this.isAdmin = false;
    }

    async init() {
        // Check user roles
        const userInfo = this.getUserInfo();  // From JWT token
        this.hasReportingRole = userInfo.roles.includes('reporting') || userInfo.roles.includes('admin');
        this.isAdmin = userInfo.roles.includes('admin');
    }

    getDefaultStartDate() {
        // Default to 30 days ago
        const date = new Date();
        date.setDate(date.getDate() - 30);
        return date.toISOString().split('T')[0];
    }

    getDefaultEndDate() {
        // Default to today
        return new Date().toISOString().split('T')[0];
    }

    async render() {
        return `
            <div class="usage-dashboard">
                <h1>${this.hasReportingRole ? 'Usage Reporting' : 'My Usage'}</h1>

                <!-- Filters -->
                <div class="usage-filters">
                    <div class="filter-group">
                        <label>Date Range:</label>
                        <input type="date" id="start-date" value="${this.dateRange.start}">
                        <span>to</span>
                        <input type="date" id="end-date" value="${this.dateRange.end}">
                    </div>

                    ${this.hasReportingRole ? `
                    <div class="filter-group">
                        <label>Account:</label>
                        <select id="account-filter">
                            <option value="">All Accounts</option>
                            ${await this.renderAccountOptions()}
                        </select>
                    </div>
                    ` : ''}

                    <div class="filter-group">
                        <label>View:</label>
                        <select id="view-select">
                            <option value="summary">Summary</option>
                            <option value="by_model">By Model</option>
                            <option value="storage">Storage</option>
                        </select>
                    </div>

                    <button id="apply-filters" class="btn btn-primary">Apply</button>
                    <button id="export-csv" class="btn btn-secondary">Export CSV</button>
                </div>

                <!-- Chart -->
                <div class="usage-chart">
                    <canvas id="usage-chart-canvas"></canvas>
                </div>

                <!-- Data Table -->
                <div class="usage-table-container">
                    <div id="table-container"></div>
                </div>
            </div>
        `;
    }

    async afterRender() {
        // Attach event listeners
        document.getElementById('apply-filters').addEventListener('click', () => {
            this.updateFilters();
            this.loadData();
        });

        document.getElementById('export-csv').addEventListener('click', () => {
            this.exportCSV();
        });

        document.getElementById('view-select').addEventListener('change', (e) => {
            this.currentView = e.target.value;
            this.loadData();
        });

        // Load initial data
        await this.loadData();
    }

    updateFilters() {
        this.dateRange.start = document.getElementById('start-date').value;
        this.dateRange.end = document.getElementById('end-date').value;
        this.filters.accountId = document.getElementById('account-filter').value || null;
    }

    async loadData() {
        try {
            const params = new URLSearchParams({
                start_date: this.dateRange.start,
                end_date: this.dateRange.end
            });

            // Only add account_id filter for reporting role
            if (this.hasReportingRole && this.filters.accountId) {
                params.append('account_id', this.filters.accountId);
            }

            let endpoint;
            const basePath = this.hasReportingRole ? '/reporting' : '/usage';

            switch (this.currentView) {
                case 'by_model':
                    endpoint = this.hasReportingRole
                        ? `${basePath}/usage/by-model`
                        : `${basePath}/my-models`;
                    break;
                case 'storage':
                    endpoint = this.hasReportingRole
                        ? `${basePath}/storage`
                        : `${basePath}/my-storage`;
                    break;
                default:
                    endpoint = this.hasReportingRole
                        ? `${basePath}/usage/summary`
                        : `${basePath}/my-summary`;
            }

            const response = await API.get(`${endpoint}?${params}`);

            this.renderChart(response.data);
            this.renderTable(response.data);

        } catch (error) {
            console.error('Failed to load reporting data:', error);
            this.showError('Failed to load usage data');
        }
    }

    renderChart(data) {
        // Destroy existing chart
        if (this.chart) {
            this.chart.destroy();
        }

        const ctx = document.getElementById('usage-chart-canvas').getContext('2d');

        // Different chart configurations based on view
        let chartConfig;

        switch (this.currentView) {
            case 'by_model':
                chartConfig = this.getModelChartConfig(data);
                break;
            case 'storage':
                chartConfig = this.getStorageChartConfig(data);
                break;
            default:
                chartConfig = this.getSummaryChartConfig(data);
        }

        this.chart = new Chart(ctx, chartConfig);
    }

    getSummaryChartConfig(data) {
        return {
            type: 'line',
            data: {
                labels: data.map(d => d.date),
                datasets: [
                    {
                        label: 'Total Operations',
                        data: data.map(d => d.total_operations),
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },
                    {
                        label: 'Workbench',
                        data: data.map(d => d.workbench_operations),
                        borderColor: 'rgb(54, 162, 235)',
                        tension: 0.1
                    },
                    {
                        label: 'API',
                        data: data.map(d => d.api_operations),
                        borderColor: 'rgb(255, 99, 132)',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Usage Over Time'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        };
    }

    getModelChartConfig(data) {
        // Group by model and sum tokens
        const modelTotals = {};
        data.forEach(d => {
            const key = `${d.provider}:${d.model_name}`;
            if (!modelTotals[key]) {
                modelTotals[key] = 0;
            }
            modelTotals[key] += d.total_tokens;
        });

        return {
            type: 'bar',
            data: {
                labels: Object.keys(modelTotals),
                datasets: [{
                    label: 'Total Tokens',
                    data: Object.values(modelTotals),
                    backgroundColor: 'rgb(75, 192, 192)'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Token Usage by Model'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        };
    }

    getStorageChartConfig(data) {
        return {
            type: 'line',
            data: {
                labels: data.map(d => d.date),
                datasets: [{
                    label: 'Storage (GB)',
                    data: data.map(d => d.total_gb),
                    borderColor: 'rgb(153, 102, 255)',
                    tension: 0.1,
                    fill: true,
                    backgroundColor: 'rgba(153, 102, 255, 0.2)'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Storage Usage Over Time'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        };
    }

    renderTable(data) {
        const container = document.getElementById('table-container');

        if (data.length === 0) {
            container.innerHTML = '<p>No data available for selected filters.</p>';
            return;
        }

        // Generate table based on view
        let html = '<table class="usage-table"><thead><tr>';

        // Table headers based on view
        const headers = this.getTableHeaders();
        headers.forEach(h => {
            html += `<th>${h}</th>`;
        });
        html += '</tr></thead><tbody>';

        // Table rows
        data.forEach(row => {
            html += '<tr>';
            const cells = this.getTableCells(row);
            cells.forEach(c => {
                html += `<td>${c}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    }

    getTableHeaders() {
        switch (this.currentView) {
            case 'by_model':
                return ['Date', 'Account', 'Provider', 'Model', 'Operations', 'Total Tokens', 'Avg Duration (ms)', 'Success Rate'];
            case 'storage':
                return ['Date', 'Account', 'Total GB', 'Document Count', 'PDF', 'DOCX', 'Other'];
            default:
                return ['Date', 'Account', 'Total Ops', 'Workbench', 'API', 'Extractions', 'Classifications', 'Total Tokens', 'Success Rate'];
        }
    }

    getTableCells(row) {
        switch (this.currentView) {
            case 'by_model':
                return [
                    row.date,
                    row.account_name || 'Unknown',
                    row.provider,
                    row.model_name,
                    row.operation_count,
                    row.total_tokens.toLocaleString(),
                    row.avg_duration_ms,
                    `${((row.successful_operations / row.operation_count) * 100).toFixed(1)}%`
                ];
            case 'storage':
                return [
                    row.date,
                    row.account_name || 'Unknown',
                    row.total_gb.toFixed(2),
                    row.document_count,
                    this.formatBytes(row.pdf_bytes),
                    this.formatBytes(row.docx_bytes),
                    this.formatBytes(row.other_bytes)
                ];
            default:
                return [
                    row.date,
                    row.account_name || 'Unknown',
                    row.total_operations,
                    row.workbench_operations,
                    row.api_operations,
                    row.extractions,
                    row.classifications,
                    row.total_tokens.toLocaleString(),
                    `${((row.successful_operations / row.total_operations) * 100).toFixed(1)}%`
                ];
        }
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async exportCSV() {
        const params = new URLSearchParams({
            start_date: this.dateRange.start,
            end_date: this.dateRange.end,
            report_type: this.currentView
        });

        // Only add account_id filter for reporting role
        if (this.hasReportingRole && this.filters.accountId) {
            params.append('account_id', this.filters.accountId);
        }

        const basePath = this.hasReportingRole ? '/reporting' : '/usage';
        const endpoint = this.hasReportingRole
            ? `${basePath}/export/csv`
            : `${basePath}/my-export/csv`;
        const url = `${endpoint}?${params}`;

        // Trigger download
        const a = document.createElement('a');
        a.href = url;
        a.download = `usage_report_${this.dateRange.start}_${this.dateRange.end}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    async renderAccountOptions() {
        // Only reporting role users need account options
        if (!this.hasReportingRole) {
            return '';
        }

        try {
            const response = await API.get('/reporting/accounts');
            return response.accounts.map(acc =>
                `<option value="${acc.id}">${acc.name}</option>`
            ).join('');
        } catch (error) {
            console.error('Failed to load accounts:', error);
            return '';
        }
    }

    showError(message) {
        // Show error message to user
        const container = document.getElementById('table-container');
        container.innerHTML = `<div class="error">${message}</div>`;
    }
}

// Register component
window.UsageDashboard = UsageDashboard;
```

### 8.3 Template Integration

**New File:** `/api/templates/sections/usage.j2`

```html
<div id="usage-section" class="section" style="display: none;">
    <div id="usage-component-container"></div>
</div>

<script>
    // Initialize usage component when section is shown
    document.addEventListener('DOMContentLoaded', function() {
        const usageSection = document.getElementById('usage-section');
        const container = document.getElementById('usage-component-container');

        // Initialize when first shown
        let usageComponent = null;

        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === 'style') {
                    const display = usageSection.style.display;
                    if (display !== 'none' && !usageComponent) {
                        usageComponent = new UsageDashboard();
                        usageComponent.init();  // Initialize role checks
                        usageComponent.mount(container);
                    }
                }
            });
        });

        observer.observe(usageSection, { attributes: true });
    });
</script>
```

### 8.4 CSS Styles

**New File:** `/api/public/css/usage.css`

```css
.usage-dashboard {
    padding: 20px;
}

.usage-filters {
    display: flex;
    gap: 20px;
    margin-bottom: 30px;
    padding: 20px;
    background: #f5f5f5;
    border-radius: 8px;
    flex-wrap: wrap;
    align-items: flex-end;
}

.filter-group {
    display: flex;
    flex-direction: column;
    gap: 5px;
}

.filter-group label {
    font-weight: bold;
    font-size: 14px;
}

.filter-group input,
.filter-group select {
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

.usage-chart {
    margin-bottom: 30px;
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.usage-chart canvas {
    max-height: 400px;
}

.usage-table-container {
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    overflow-x: auto;
}

.usage-table {
    width: 100%;
    border-collapse: collapse;
}

.usage-table th,
.usage-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

.usage-table th {
    background: #f5f5f5;
    font-weight: bold;
    position: sticky;
    top: 0;
}

.usage-table tr:hover {
    background: #f9f9f9;
}

.btn {
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: bold;
}

.btn-primary {
    background: #007bff;
    color: white;
}

.btn-primary:hover {
    background: #0056b3;
}

.btn-secondary {
    background: #6c757d;
    color: white;
}

.btn-secondary:hover {
    background: #545b62;
}

.error {
    padding: 20px;
    background: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
    border-radius: 4px;
}
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Test File:** `/api/tests/test_usage_tracker.py`

```python
import pytest
from api.services.usage_tracker import UsageTracker
from api.models import usage_tracking
from datetime import datetime, date

def test_log_extraction_success(db_session):
    tracker = UsageTracker(db_session)

    log_entry = tracker.log_extraction(
        account_id=1,
        document_id=100,
        extractor_id=5,
        provider='openai',
        model_name='gpt-4',
        input_tokens=1000,
        output_tokens=200,
        duration_ms=2500,
        status='success',
        source_type='workbench'
    )

    assert log_entry.id is not None
    assert log_entry.operation_type == 'extraction'
    assert log_entry.total_tokens == 1200
    assert log_entry.status == 'success'

def test_log_extraction_failure(db_session):
    tracker = UsageTracker(db_session)

    log_entry = tracker.log_extraction(
        account_id=1,
        document_id=100,
        extractor_id=5,
        duration_ms=100,
        status='failure',
        error_message='Model timeout',
        source_type='api'
    )

    assert log_entry.status == 'failure'
    assert log_entry.error_message == 'Model timeout'
    assert log_entry.total_tokens is None

def test_aggregate_daily_summaries(db_session):
    # Create test data
    tracker = UsageTracker(db_session)
    test_date = date(2024, 1, 1)

    # Log multiple operations
    for i in range(10):
        tracker.log_extraction(
            account_id=1,
            document_id=100 + i,
            extractor_id=5,
            provider='openai',
            model_name='gpt-4',
            input_tokens=1000,
            output_tokens=200,
            duration_ms=2500,
            status='success',
            source_type='workbench'
        )

    # Run aggregation
    from api.jobs.usage_aggregation import aggregate_usage_for_date
    summary = aggregate_usage_for_date(db_session, test_date)

    assert summary.total_operations == 10
    assert summary.extractions == 10
    assert summary.total_tokens == 12000
    assert summary.successful_operations == 10
```

### 9.2 Integration Tests

**Test File:** `/api/tests/test_reporting_api.py`

```python
import pytest
from fastapi.testclient import TestClient
from api.main import app

def test_usage_summary_endpoint(client: TestClient, reporting_token: str):
    response = client.get(
        "/reporting/usage/summary",
        params={
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        },
        headers={"Authorization": f"Bearer {reporting_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total_records" in data

def test_usage_by_model_endpoint(client: TestClient, reporting_token: str):
    response = client.get(
        "/reporting/usage/by-model",
        params={
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "provider": "openai"
        },
        headers={"Authorization": f"Bearer {reporting_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data

def test_csv_export(client: TestClient, reporting_token: str):
    response = client.get(
        "/reporting/export/csv",
        params={
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "report_type": "summary"
        },
        headers={"Authorization": f"Bearer {reporting_token}"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv"
    assert "usage_report" in response.headers["content-disposition"]

def test_unauthorized_access(client: TestClient, user_token: str):
    # Regular user without reporting role
    response = client.get(
        "/reporting/usage/summary",
        params={
            "start_date": "2024-01-01",
            "end_date": "2024-01-31"
        },
        headers={"Authorization": f"Bearer {user_token}"}
    )

    assert response.status_code == 403
```

### 9.3 Performance Tests

**Test File:** `/api/tests/performance/test_tracking_overhead.py`

```python
import pytest
import time
from api.services.usage_tracker import UsageTracker

def test_tracking_overhead(db_session):
    """
    Verify that tracking adds minimal overhead to operations.
    Target: < 10ms per log entry
    """
    tracker = UsageTracker(db_session)

    iterations = 100
    start_time = time.time()

    for i in range(iterations):
        tracker.log_extraction(
            account_id=1,
            document_id=i,
            extractor_id=5,
            provider='openai',
            model_name='gpt-4',
            input_tokens=1000,
            output_tokens=200,
            duration_ms=2500,
            status='success',
            source_type='workbench'
        )

    elapsed_ms = (time.time() - start_time) * 1000
    avg_overhead = elapsed_ms / iterations

    assert avg_overhead < 10, f"Tracking overhead too high: {avg_overhead:.2f}ms"

def test_aggregation_performance(db_session):
    """
    Verify aggregation can handle large volumes.
    Target: < 1 minute for 100k records
    """
    # Create 100k test records (via fixture or bulk insert)
    # ...

    from api.jobs.usage_aggregation import aggregate_usage_for_date

    start_time = time.time()
    summary = aggregate_usage_for_date(db_session, date(2024, 1, 1))
    elapsed_s = time.time() - start_time

    assert elapsed_s < 60, f"Aggregation too slow: {elapsed_s:.2f}s"
```

### 9.4 End-to-End Tests

Test the full flow from operation to reporting dashboard:

1. Perform extraction via API
2. Verify usage log created
3. Run aggregation job
4. Verify summary created
5. Query reporting API
6. Verify data matches

---

## 10. Migration Plan

### 10.1 Migration Script

**File:** `/migrations/003_usage_tracking_schema.sql`

```sql
-- Migration: Add usage tracking tables
-- Version: 003
-- Date: 2024-01-15

BEGIN;

-- Create usage_logs table
CREATE TABLE IF NOT EXISTS usage_logs (
    id BIGSERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    operation_type VARCHAR(50) NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    extractor_id INTEGER REFERENCES extractors(id) ON DELETE SET NULL,
    classifier_id INTEGER REFERENCES classifiers(id) ON DELETE SET NULL,
    llm_model_id INTEGER REFERENCES llm_models(id) ON DELETE SET NULL,
    provider VARCHAR(50),
    model_name VARCHAR(255),
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    bytes_stored BIGINT,
    duration_ms INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    user_agent TEXT,
    ip_address INET,
    CONSTRAINT check_operation_type CHECK (operation_type IN ('extraction', 'classification', 'embedding', 'upload', 'download')),
    CONSTRAINT check_source_type CHECK (source_type IN ('workbench', 'api')),
    CONSTRAINT check_status CHECK (status IN ('success', 'failure', 'partial'))
);

CREATE INDEX idx_usage_logs_account_timestamp ON usage_logs(account_id, timestamp DESC);
CREATE INDEX idx_usage_logs_operation_type ON usage_logs(operation_type);
CREATE INDEX idx_usage_logs_timestamp ON usage_logs(timestamp DESC);
CREATE INDEX idx_usage_logs_provider_model ON usage_logs(provider, model_name) WHERE provider IS NOT NULL;
CREATE INDEX idx_usage_logs_source_type ON usage_logs(source_type);

-- Create usage_summaries table
CREATE TABLE IF NOT EXISTS usage_summaries (
    id BIGSERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    workbench_operations INTEGER DEFAULT 0,
    api_operations INTEGER DEFAULT 0,
    total_operations INTEGER DEFAULT 0,
    extractions INTEGER DEFAULT 0,
    classifications INTEGER DEFAULT 0,
    embeddings INTEGER DEFAULT 0,
    uploads INTEGER DEFAULT 0,
    downloads INTEGER DEFAULT 0,
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    successful_operations INTEGER DEFAULT 0,
    failed_operations INTEGER DEFAULT 0,
    bytes_uploaded BIGINT DEFAULT 0,
    bytes_downloaded BIGINT DEFAULT 0,
    avg_duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, date)
);

CREATE INDEX idx_usage_summaries_account_date ON usage_summaries(account_id, date DESC);
CREATE INDEX idx_usage_summaries_date ON usage_summaries(date DESC);

-- Create usage_summaries_by_model table
CREATE TABLE IF NOT EXISTS usage_summaries_by_model (
    id BIGSERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    llm_model_id INTEGER REFERENCES llm_models(id) ON DELETE SET NULL,
    operation_count INTEGER DEFAULT 0,
    input_tokens BIGINT DEFAULT 0,
    output_tokens BIGINT DEFAULT 0,
    total_tokens BIGINT DEFAULT 0,
    avg_duration_ms INTEGER,
    successful_operations INTEGER DEFAULT 0,
    failed_operations INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, date, provider, model_name)
);

CREATE INDEX idx_usage_summaries_by_model_account_date ON usage_summaries_by_model(account_id, date DESC);
CREATE INDEX idx_usage_summaries_by_model_provider_model ON usage_summaries_by_model(provider, model_name);

-- Create storage_usage table
CREATE TABLE IF NOT EXISTS storage_usage (
    id BIGSERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_bytes BIGINT NOT NULL DEFAULT 0,
    document_count INTEGER NOT NULL DEFAULT 0,
    storage_backend VARCHAR(20),
    pdf_bytes BIGINT DEFAULT 0,
    docx_bytes BIGINT DEFAULT 0,
    html_bytes BIGINT DEFAULT 0,
    other_bytes BIGINT DEFAULT 0,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(account_id, date)
);

CREATE INDEX idx_storage_usage_account_date ON storage_usage(account_id, date DESC);
CREATE INDEX idx_storage_usage_date ON storage_usage(date DESC);

-- Add columns to accounts table
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS roles TEXT[] DEFAULT '{}';
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS usage_tracking_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS usage_limit_tokens BIGINT;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS usage_alert_threshold FLOAT;

-- Set default role for existing accounts
UPDATE accounts SET roles = ARRAY['user'] WHERE roles = '{}' OR roles IS NULL;

COMMIT;
```

### 10.2 Migration Execution

```bash
# Run migration
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/003_usage_tracking_schema.sql

# Verify tables created
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "\dt usage_*"

# Verify indexes created
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "\di usage_*"
```

### 10.3 Rollback Script

**File:** `/migrations/003_usage_tracking_schema_rollback.sql`

```sql
-- Rollback: Remove usage tracking tables
-- Version: 003
-- Date: 2024-01-15

BEGIN;

-- Drop tables (cascade will remove foreign keys)
DROP TABLE IF EXISTS storage_usage CASCADE;
DROP TABLE IF EXISTS usage_summaries_by_model CASCADE;
DROP TABLE IF EXISTS usage_summaries CASCADE;
DROP TABLE IF EXISTS usage_logs CASCADE;

-- Remove columns from accounts table
ALTER TABLE accounts DROP COLUMN IF EXISTS roles;
ALTER TABLE accounts DROP COLUMN IF EXISTS usage_tracking_enabled;
ALTER TABLE accounts DROP COLUMN IF EXISTS usage_limit_tokens;
ALTER TABLE accounts DROP COLUMN IF EXISTS usage_alert_threshold;

COMMIT;
```

---

## 11. Security Considerations

### 11.1 Data Privacy

**Principle:** Track usage without exposing sensitive content.

**Implementation:**
- Do NOT store document content in usage logs
- Do NOT store extraction results in usage logs
- Store only metadata: document IDs, operation types, token counts
- Mask IP addresses after 90 days (GDPR compliance)
- Provide data export for account holders (GDPR right to access)
- Support data deletion on account deletion (CASCADE constraints)

### 11.2 Access Control

**Reporting Role Restrictions:**
- Read-only access to aggregated data
- Cannot modify usage logs (immutable audit trail)
- Cannot access other admin functions
- Rate limiting on reporting endpoints

**Admin Role:**
- Full access to usage data
- Can trigger manual aggregation
- Can assign roles to accounts
- Audit logging for role changes

### 11.3 Performance and DoS Protection

**Rate Limiting:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.get("/reporting/usage/summary")
@limiter.limit("60/minute")  # 60 requests per minute
async def get_usage_summary(...):
    ...
```

**Query Limits:**
- Maximum date range: 1 year
- Maximum CSV export: 100k records
- Pagination for log queries
- Query timeout: 30 seconds

**Caching:**
- Cache aggregated summaries (Redis)
- Cache duration: 1 hour for current day, 24 hours for past days
- Invalidate cache on manual aggregation

### 11.4 Audit Logging

**Log Critical Actions:**
- Role assignments/changes
- Access to cross-account data
- Manual aggregation triggers
- CSV exports (who, when, what filters)

**Audit Log Table:**
```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    actor_account_id INTEGER REFERENCES accounts(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address INET
);
```

### 11.5 Data Retention

**Policy:**
- `usage_logs`: Retain for 13 months (1 year + 1 month for overlap)
- `usage_summaries`: Retain indefinitely (aggregated, minimal storage)
- `storage_usage`: Retain for 13 months

**Automated Cleanup Job:**
```python
# In api/jobs/cleanup.py

def cleanup_old_usage_logs():
    """Delete usage logs older than 13 months."""
    cutoff_date = datetime.now() - timedelta(days=395)  # ~13 months

    deleted = db.query(UsageLog).filter(
        UsageLog.timestamp < cutoff_date
    ).delete()

    db.commit()
    logger.info(f"Deleted {deleted} old usage log records")
```

---

## 12. Configuration

### 12.1 Environment Variables

Add to `.env`:

```bash
# Usage Tracking Configuration
USAGE_TRACKING_ENABLED=true
USAGE_AGGREGATION_SCHEDULE="0 2 * * *"  # Daily at 2 AM
STORAGE_CALC_SCHEDULE="0 3 * * *"       # Daily at 3 AM
USAGE_LOG_RETENTION_DAYS=395            # 13 months
USAGE_CACHE_TTL=3600                    # 1 hour cache for current day

# Reporting Configuration
REPORTING_MAX_DATE_RANGE_DAYS=365
REPORTING_MAX_EXPORT_RECORDS=100000
REPORTING_RATE_LIMIT="60/minute"

# Chart.js CDN (for frontend)
CHARTJS_CDN="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"
```

### 12.2 Job Scheduler Configuration

**File:** `/api/jobs/scheduler.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import os

scheduler = AsyncIOScheduler()

def configure_jobs():
    """Configure scheduled jobs for usage tracking."""

    if os.getenv('USAGE_TRACKING_ENABLED', 'true').lower() == 'true':
        # Daily aggregation job
        aggregation_schedule = os.getenv('USAGE_AGGREGATION_SCHEDULE', '0 2 * * *')
        scheduler.add_job(
            run_usage_aggregation,
            trigger=CronTrigger.from_crontab(aggregation_schedule),
            id='usage_aggregation',
            name='Daily Usage Aggregation',
            replace_existing=True
        )

        # Storage calculation job
        storage_schedule = os.getenv('STORAGE_CALC_SCHEDULE', '0 3 * * *')
        scheduler.add_job(
            run_storage_calculation,
            trigger=CronTrigger.from_crontab(storage_schedule),
            id='storage_calculation',
            name='Daily Storage Calculation',
            replace_existing=True
        )

        # Cleanup job (monthly)
        scheduler.add_job(
            cleanup_old_usage_logs,
            trigger=CronTrigger(day=1, hour=4),  # 1st of month at 4 AM
            id='usage_cleanup',
            name='Monthly Usage Log Cleanup',
            replace_existing=True
        )

async def run_usage_aggregation():
    """Run daily usage aggregation."""
    from api.jobs.usage_aggregation import aggregate_yesterday
    from api.models.database import get_db

    async for db in get_db():
        try:
            await aggregate_yesterday(db)
        except Exception as e:
            logger.error(f"Usage aggregation failed: {e}")

async def run_storage_calculation():
    """Run daily storage calculation."""
    from api.jobs.storage_calculation import calculate_storage_for_all_accounts
    from api.models.database import get_db

    async for db in get_db():
        try:
            await calculate_storage_for_all_accounts(db)
        except Exception as e:
            logger.error(f"Storage calculation failed: {e}")
```

**Integration in `main.py`:**

```python
from api.jobs.scheduler import scheduler, configure_jobs

@app.on_event("startup")
async def startup_event():
    # Existing startup code...

    # Start job scheduler
    configure_jobs()
    scheduler.start()
    logger.info("Job scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    # Existing shutdown code...

    # Stop job scheduler
    scheduler.shutdown()
    logger.info("Job scheduler stopped")
```

---

## 13. Deployment Checklist

### 13.1 Pre-Deployment

- [ ] Run all tests (unit, integration, performance)
- [ ] Review and test migration scripts
- [ ] Verify environment variables configured
- [ ] Review security settings and rate limits
- [ ] Test rollback procedure
- [ ] Prepare deployment documentation
- [ ] Schedule maintenance window

### 13.2 Deployment Steps

1. **Backup Database**
   ```bash
   pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER $POSTGRES_DB > backup_pre_usage_tracking.sql
   ```

2. **Run Migration**
   ```bash
   psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/003_usage_tracking_schema.sql
   ```

3. **Deploy Application Code**
   ```bash
   git pull origin main
   pip install -r requirements.txt
   systemctl restart classifier-extractor-api
   ```

4. **Verify Deployment**
   - Check logs for errors
   - Test basic operations (upload, extract)
   - Verify usage logs created
   - Test reporting endpoints
   - Verify job scheduler running

5. **Assign Reporting Roles**
   ```bash
   # Via API or direct SQL
   UPDATE accounts SET roles = ARRAY['user', 'reporting'] WHERE email = 'admin@example.com';
   ```

### 13.3 Post-Deployment

- [ ] Monitor application logs for errors
- [ ] Monitor database performance
- [ ] Verify tracking working for all operation types
- [ ] Test reporting dashboard
- [ ] Verify scheduled jobs running
- [ ] Monitor tracking overhead impact
- [ ] User acceptance testing
- [ ] Update documentation

### 13.4 Rollback Plan

If issues occur:

1. **Stop Application**
   ```bash
   systemctl stop classifier-extractor-api
   ```

2. **Rollback Database**
   ```bash
   psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -f migrations/003_usage_tracking_schema_rollback.sql
   ```

3. **Revert Code**
   ```bash
   git checkout <previous-commit>
   systemctl start classifier-extractor-api
   ```

---

## 14. Future Enhancements

### 14.1 Phase 2 Features (Future)

1. **Cost Calculation**
   - Track actual costs per model
   - Cost projections and alerts
   - Budget management per account

2. **Advanced Analytics**
   - Anomaly detection (unusual usage patterns)
   - Predictive analytics (forecasting)
   - Performance trends analysis
   - Error pattern analysis

3. **Real-Time Dashboard**
   - WebSocket updates for live data
   - Real-time usage graphs
   - Active operations monitoring

4. **Alerts and Notifications**
   - Usage threshold alerts
   - Cost alerts
   - Error rate alerts
   - Email/Slack notifications

5. **Multi-Tenant Billing**
   - Invoice generation
   - Payment integration
   - Usage-based pricing tiers
   - Overage handling

6. **Enhanced Reporting**
   - Custom report builder
   - Scheduled reports (email)
   - Report templates
   - Data warehouse integration

### 14.2 Technical Improvements

1. **Performance Optimization**
   - Partitioning `usage_logs` by date
   - Materialized views for common queries
   - Background aggregation optimization
   - Query caching layer (Redis)

2. **Data Pipeline**
   - Stream processing (Kafka)
   - Real-time aggregation
   - Data archival to cold storage
   - Analytics database (ClickHouse)

3. **Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Alert manager integration
   - SLO/SLI tracking

---

## Appendix A: File Structure

```
/home/telendry/code/ai/classifier_and_extractor/
├── api/
│   ├── models/
│   │   └── usage_tracking.py          # New: SQLAlchemy models
│   ├── routes/
│   │   ├── usage.py                   # New: Self-service usage endpoints
│   │   ├── reporting.py               # New: Administrative reporting endpoints
│   │   └── admin.py                   # New: Admin endpoints
│   ├── services/
│   │   ├── usage_tracker.py           # New: Core tracking service
│   │   ├── usage_service.py           # New: Self-service usage logic
│   │   └── reporting_service.py       # New: Administrative reporting logic
│   ├── jobs/
│   │   ├── scheduler.py               # New: Job scheduler
│   │   ├── usage_aggregation.py       # New: Aggregation jobs
│   │   ├── storage_calculation.py     # New: Storage jobs
│   │   └── cleanup.py                 # New: Cleanup jobs
│   ├── util/
│   │   └── csv_export.py              # New: CSV export utility
│   ├── templates/sections/
│   │   └── usage.j2                   # New: Usage template
│   ├── public/
│   │   ├── js/components/
│   │   │   ├── usage_dashboard.js     # New: Usage dashboard component
│   │   │   └── usage_chart.js         # New: Chart component
│   │   ├── js/lib/
│   │   │   └── csv_downloader.js      # New: CSV download helper
│   │   └── css/
│   │       └── usage.css              # New: Usage styles
│   └── tests/
│       ├── test_usage_tracker.py      # New: Unit tests
│       ├── test_usage_api.py          # New: Self-service API tests
│       ├── test_reporting_api.py      # New: Administrative reporting tests
│       └── performance/
│           └── test_tracking_overhead.py  # New: Performance tests
├── migrations/
│   ├── 003_usage_tracking_schema.sql      # New: Migration
│   └── 003_usage_tracking_schema_rollback.sql  # New: Rollback
├── docs/
│   ├── USAGE_TRACKING_GUIDE.md        # New: User guide
│   └── REPORTING_API.md               # New: API documentation
└── USAGE_TRACKING_IMPLEMENTATION_PLAN.md  # This document
```

---

## Appendix B: Dependencies

Add to `requirements.txt`:

```
# Usage tracking and reporting
apscheduler==3.10.4      # Job scheduling
pandas==2.1.4            # Data manipulation for reporting
slowapi==0.1.9           # Rate limiting
redis==5.0.1             # Caching (optional)
```

Add to frontend (via CDN or npm):

```
chart.js@4.4.0           # Charting library
```

---

## Appendix C: Database Size Estimates

**Assumptions:**
- 100 users
- 50 operations per user per day
- 5,000 operations per day total

**Storage Requirements:**

| Table | Record Size | Daily Records | Monthly Size | Annual Size |
|-------|-------------|---------------|--------------|-------------|
| `usage_logs` | ~500 bytes | 5,000 | 75 MB | 900 MB |
| `usage_summaries` | ~200 bytes | 100 | 6 MB | 72 MB |
| `usage_summaries_by_model` | ~200 bytes | 300 | 18 MB | 216 MB |
| `storage_usage` | ~100 bytes | 100 | 3 MB | 36 MB |
| **Total** | | | **102 MB/month** | **1.2 GB/year** |

**With Indexes:** ~2x overhead = **2.4 GB/year**

**Cleanup Impact:** With 13-month retention, max storage: **~2.6 GB**

---

## Appendix D: Success Metrics

### Phase 1-3 (Tracking Infrastructure)
- [ ] All extraction operations logged successfully
- [ ] All classification operations logged successfully
- [ ] All upload operations logged successfully
- [ ] Tracking overhead < 10ms per operation
- [ ] Zero failed operations due to tracking errors

### Phase 4-5 (Reporting)
- [ ] Reporting API responds in < 500ms for typical queries
- [ ] CSV export completes in < 10s for 10k records
- [ ] Dashboard loads in < 2s
- [ ] Charts render in < 500ms

### Phase 6-7 (Production)
- [ ] Zero production incidents related to tracking
- [ ] Aggregation jobs complete successfully every day
- [ ] Storage calculations accurate within 1%
- [ ] User satisfaction > 4/5 for reporting interface

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-15 | System | Initial implementation plan |
| 1.1 | 2026-01-19 | System | Updated to reflect requirement changes: all users can view their own usage; reporting role is for cross-account administrative access. Added self-service endpoints and updated UI components to be role-aware. |

---

**End of Implementation Plan**
