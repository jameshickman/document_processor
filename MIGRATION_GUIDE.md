# Migration Guide: document_extract → document_extraction

This guide explains how to migrate from the deprecated `api.util.document_extract` module to the new `api.document_extraction` package.

## Overview

The `api.util.document_extract.py` module has been **deprecated** and replaced with a modern, pluggable document extraction system in `api.document_extraction/`.

### What's Changed

- **Old**: Monolithic document_extract.py with hardcoded format handlers
- **New**: Pluggable architecture with automatic handler discovery
- **Benefits**: Better maintainability, extensibility, and Markdown-first output

## Migration Status

### ✅ Immediate Compatibility
- **All existing code continues to work** without changes
- The deprecated module now acts as a compatibility wrapper
- Uses the new document_extraction system underneath

### ⚠️ Deprecation Warnings
```python
# This will show a deprecation warning:
from api.util.document_extract import extract
```

```
DeprecationWarning: api.util.document_extract is deprecated.
Use api.document_extraction.extract instead.
```

## Migration Steps

### Step 1: For Simple Text Extraction

**Old Code:**
```python
from api.util.document_extract import extract, DocumentDecodeException, DocumentUnknownTypeException

# This required user_id and db parameters
doc_content = extract_legacy_function(user_id, file_path, db)
```

**New Code:**
```python
from api.document_extraction.extract import extract, DocumentDecodeException, DocumentUnknownTypeException

# This only needs the file path
content = extract(file_path)
```

### Step 2: For Database Integration (like upload_document.py)

**Old Code Pattern:**
```python
from api.util.document_extract import extract, DocumentDecodeException, DocumentUnknownTypeException

def process_document(user_id: int, file_path: str, db: Session):
    try:
        db_document = extract(user_id, file_path, db)  # Old wrapper function
        return db_document
    except DocumentDecodeException:
        # Handle extraction failure
        pass
```

**New Code Pattern:**
```python
from api.document_extraction.extract import extract as new_extract, DocumentDecodeException, DocumentUnknownTypeException
from sqlalchemy import text

def process_document(user_id: int, file_path: str, db: Session):
    try:
        # Step 1: Extract content using new system
        content = new_extract(file_path)

        # Step 2: Handle database operations manually
        # Clean existing records
        q = text("DELETE FROM documents WHERE file_name = :name")
        db.execute(q, {"name": file_path})
        db.commit()

        # Create new document record
        db_document = Document(file_name=file_path, full_text=content, account_id=user_id)
        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        return db_document
    except DocumentDecodeException:
        # Handle extraction failure
        pass
```

## Key Differences

### 1. Function Signatures

| Aspect | Old System | New System |
|--------|------------|------------|
| **Main Function** | `extract(user_id, file_path, db)` | `extract(file_path)` |
| **Return Value** | `models.Document` (database object) | `str` (extracted content) |
| **Dependencies** | Database session required | No database dependency |

### 2. Supported Formats

| Format | Old Support | New Support | Notes |
|--------|-------------|-------------|-------|
| **PDF** | ✅ Plain text | ✅ Plain text | Same pdftotext backend |
| **HTML** | ✅ Markdown | ✅ Markdown | Same pandoc backend |
| **Office Docs** | ✅ Basic | ✅ Enhanced | Multi-stage fallback |
| **Text/Markdown** | ✅ Direct | ✅ Direct | No change |
| **New Formats** | ❌ Hardcoded | ✅ Pluggable | Add handlers easily |

### 3. Architecture

**Old System:**
- Single file with all conversion logic
- Hardcoded format support
- Database tightly coupled

**New System:**
- Pluggable handler architecture
- Dynamic format discovery
- Separation of concerns (extraction vs database)

## Testing Your Migration

### 1. Verify Compatibility
```python
import warnings

with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")

    # Your existing import - should work but show warning
    from api.util.document_extract import extract

    # Check for deprecation warning
    if w:
        print(f"Warning: {w[0].message}")
```

### 2. Test File Processing
```python
# Test that both systems produce the same results
from api.util.document_extract import extract as old_extract
from api.document_extraction.extract import extract as new_extract

# For files that don't need database operations
content_new = new_extract("test.txt")
print(f"New system: {len(content_new)} characters")
```

### 3. Validate New Features
```python
# Test automatic handler discovery
from api.document_extraction.extract import extract

# These should work automatically:
content = extract("document.pdf")     # PDF extraction
content = extract("webpage.html")     # HTML → Markdown
content = extract("presentation.pptx") # Office → Markdown
```

## Common Migration Scenarios

### Scenario 1: Upload API Endpoints
**Current Status:** ✅ **Working with compatibility wrapper**

```python
# api/util/upload_document.py continues to work
# Shows deprecation warnings to encourage migration
from api.util.document_extract import extract  # Still works
```

### Scenario 2: Batch Document Processing
**Migration Path:**
```python
# Old approach
for file_path in files:
    doc_obj = extract(user_id, file_path, db)

# New approach
for file_path in files:
    content = new_extract(file_path)
    # Handle database operations separately
    save_to_database(user_id, file_path, content, db)
```

### Scenario 3: Custom Document Handlers
**Old:** Modify document_extract.py directly
**New:** Add handler file to handlers/ directory
```python
# handlers/my_format.py
from api.document_extraction.handler_base import DocumentExtractionBase

class MyFormatHandler(DocumentExtractionBase):
    @staticmethod
    def format() -> list[str]:
        return ['xyz']

    def extract(self, input_file: str) -> str:
        # Conversion logic
        return converted_content
```

## Timeline

### Phase 1: Compatibility (Current)
- ✅ Old module works with deprecation warnings
- ✅ New system available for new code
- ✅ All existing functionality preserved

### Phase 2: Migration Encouraged (Next Release)
- ⚠️ More visible deprecation warnings
- 📖 Documentation updated to show new patterns
- 🔧 Migration tools and helpers

### Phase 3: Deprecation (Future Release)
- ❌ Old module removal planned
- 🔄 All internal code migrated
- 🚨 Breaking change notice

## Getting Help

### For Issues During Migration:
1. Check that file formats are supported in new system
2. Verify external tools (pandoc, pdftotext) are available
3. Test with sample files before full migration
4. Review error messages - they're more descriptive now

### For New Feature Requests:
1. Consider creating a custom handler
2. Check existing handlers for similar patterns
3. Refer to the pluggable architecture documentation

## Benefits of Migration

### For Developers:
- **Simpler API**: Just pass file path, get content
- **Better Separation**: Extraction logic separate from database
- **More Formats**: Automatic support for new document types
- **Better Testing**: Easier to unit test extraction logic

### For Operations:
- **Better Error Messages**: More specific failure reasons
- **Improved Logging**: Detailed conversion pipeline info
- **Tool Validation**: Checks for required external programs
- **Performance**: Optimized conversion pipelines

### For Future Development:
- **Extensibility**: Add new formats without core changes
- **Maintainability**: Clear separation of concerns
- **Quality**: Consistent Markdown output across formats
- **Standards**: Modern Python patterns and type hints