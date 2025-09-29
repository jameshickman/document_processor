# Document Extraction: Pluggable Conversion Framework

A robust, extensible document conversion system that automatically converts various file formats to Markdown or plain text. This package **replaces the deprecated `api/util/document_extract.py`** with a modern, plugin-based architecture.

> **Migration Status**: ✅ **Complete** - The deprecated module now acts as a compatibility wrapper using this new system. See [MIGRATION_GUIDE.md](../../../MIGRATION_GUIDE.md) for details.

## Overview

The document extraction system provides:
- **Automatic format detection** based on file extensions
- **Dynamic handler discovery** - new handlers are automatically detected
- **Markdown-first conversion** with graceful fallback to plain text
- **Pluggable architecture** - easily add support for new formats
- **Robust error handling** with meaningful exceptions

## Quick Start

```python
from api.document_extraction.extract import extract

# Extract content from any supported file
content = extract("document.pdf")          # Returns Markdown or plain text
content = extract("presentation.pptx")     # Converts to Markdown
content = extract("webpage.html")          # HTML → Markdown conversion
content = extract("README.md")             # Direct text passthrough
```

## Supported File Formats

| Format | Extensions | Handler | Output |
|--------|------------|---------|---------|
| **Text Files** | `.txt`, `.md`, `` (no extension) | Built-in | Direct passthrough |
| **HTML/Web** | `.html`, `.htm` | HTMLExtractionHandler | Markdown via Pandoc |
| **PDF Documents** | `.pdf` | PDFextractionHandler | Plain text via pdftotext |
| **Office Documents** | `.doc`, `.docx`, `.ppt`, `.pptx`, `.xls`, `.xlsx`, `.rtf`, `.odt` | OfficeDocumentExtractionHandler | Markdown via Pandoc/LibreOffice |

## Architecture

### Core Components

```
api/document_extraction/
├── extract.py              # Main entry point with dynamic handler discovery
├── handler_base.py         # Base class and utility functions
├── handlers/               # Handler plugins directory
│   ├── __init__.py
│   ├── document.py         # Office document handler
│   ├── html.py            # HTML conversion handler
│   ├── pdf.py             # PDF extraction handler
│   └── README.md          # This documentation
└── __init__.py
```

### Dynamic Handler Discovery

The system automatically discovers handlers at runtime:

1. Scans the `handlers/` directory for Python modules
2. Imports each module and inspects for classes inheriting from `DocumentExtractionBase`
3. Calls the static `format()` method to determine supported file extensions
4. Routes files to appropriate handlers based on extension matching

This means **adding a new handler requires no changes to the core system** - just drop a new handler file in the `handlers/` directory.

## Creating Custom Handlers

### Step 1: Inherit from DocumentExtractionBase

```python
# handlers/my_format.py
from api.document_extraction.handler_base import DocumentExtractionBase

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
        return converted_content
```

### Step 2: Implement Conversion Logic

Your handler should prioritize Markdown output with fallback to plain text:

```python
def extract(self, input_file: str) -> str:
    try:
        # Try Markdown conversion first
        return self.pandoc_convert(input_file, "myformat", "Conversion failed")
    except DocumentDecodeException:
        # Fall back to plain text extraction
        return self._extract_as_text(input_file)
```

### Step 3: Leverage Base Class Utilities

The base class provides useful methods:

- `pandoc_convert(file_name, type_from, exception_message)` - Convert via Pandoc
- `find_exe(command_name)` - Locate system executables
- `is_real_words(content)` - Validate extracted text quality
- `self.temp_dir` - Temporary directory for intermediate files

## Handler Examples

### HTML Handler (Simple)
```python
class HTMLExtractionHandler(DocumentExtractionBase):
    @staticmethod
    def format() -> list[str]:
        return ['html', 'htm']

    def extract(self, input_file: str) -> str:
        return self.pandoc_convert(input_file, "html", "HTML extraction failed")
```

### PDF Handler (With Validation)
```python
class PDFextractionHandler(DocumentExtractionBase):
    def extract(self, input_file: str) -> str:
        # Use pdftotext for extraction
        command = [find_exe("pdftotext"), input_file, "-"]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            raise DocumentDecodeException(f"pdftotext failed: {result.stderr}")

        content = result.stdout.strip()

        # Validate output quality
        if not content or not is_real_words(content):
            raise DocumentDecodeException("PDF extraction produced garbage text")

        return content
```

### Office Documents Handler (Multi-stage)
```python
class OfficeDocumentExtractionHandler(DocumentExtractionBase):
    def extract(self, input_file: str) -> str:
        try:
            # Try direct Pandoc conversion
            return self.pandoc_convert(input_file, file_ext, "Direct conversion failed")
        except DocumentDecodeException:
            try:
                # Fall back to LibreOffice + Pandoc
                odt_file = self._openoffice_convert(input_file)
                return self.pandoc_convert(odt_file, "odt", "Office conversion failed")
            except DocumentDecodeException:
                # Final fallback to plain text
                return self._extract_as_text(input_file)
```

## Error Handling

The system uses specific exceptions for different failure modes:

```python
from api.document_extraction.extract import DocumentDecodeException, DocumentUnknownTypeException

try:
    content = extract("document.xyz")
except DocumentUnknownTypeException:
    print("No handler available for this file type")
except DocumentDecodeException:
    print("File format recognized but conversion failed")
except FileNotFoundError:
    print("File does not exist")
```

## Dependencies

### Required System Tools
- **pandoc** - Universal document converter (most handlers)
- **pdftotext** - PDF text extraction (poppler-utils package)
- **soffice** - LibreOffice headless mode (complex office documents)

### Installation Examples

**Ubuntu/Debian:**
```bash
sudo apt install pandoc poppler-utils libreoffice
```

**macOS (Homebrew):**
```bash
brew install pandoc poppler libreoffice
```

**Windows:**
- Install Pandoc from [pandoc.org](https://pandoc.org/installing.html)
- Install Poppler from [poppler for Windows](https://blog.alivate.com.au/poppler-windows/)
- Install LibreOffice from [libreoffice.org](https://www.libreoffice.org/)

## Testing

The system includes comprehensive tests in `testing.py`:

```python
# Run document extraction tests
python -m unittest testing.TestDocumentExtraction -v

# Or run all tests
python testing.py
```

Test coverage includes:
- All supported file formats
- Error handling scenarios
- Dynamic handler discovery
- Unicode and special character handling
- Large file processing
- Empty file handling

## Best Practices

### For Handler Development:
1. **Always validate output** using `is_real_words()` for text quality
2. **Implement fallbacks** - try Markdown first, fall back to plain text
3. **Use temporary files** via `self.temp_dir` for intermediate processing
4. **Handle tool failures gracefully** with meaningful error messages
5. **Test with real-world files** including edge cases

### For Integration:
1. **Check tool availability** before deploying to production
2. **Monitor conversion quality** in your application logs
3. **Implement timeouts** for long-running conversions
4. **Cache results** when processing the same files repeatedly

## Troubleshooting

### Common Issues:

**"No handler found for file type"**
- Add a handler for that file extension
- Check file extension is correctly detected

**"pdftotext failed" or "pandoc failed"**
- Verify tools are installed and in PATH
- Check file is not corrupted or password-protected

**"Extraction produced garbage text"**
- File may have embedded fonts or be image-based
- Try OCR preprocessing for scanned documents

**Handler not discovered**
- Ensure handler class inherits from `DocumentExtractionBase`
- Verify `format()` method returns correct extensions list
- Check for import errors in handler module

## Extending the System

### Adding New Format Support:
1. Create handler in `handlers/` directory
2. Implement required methods
3. Test with sample files
4. No core system changes needed!

### Advanced Features:
- **OCR Integration** - Add image-based document support
- **Batch Processing** - Process multiple files efficiently
- **Format-specific Options** - Pass conversion parameters
- **Quality Metrics** - Score conversion accuracy
- **Caching Layer** - Store converted content

## Migration from Legacy System

If migrating from `api/util/document_extract.py`:

**Old:**
```python
from api.util.document_extract import extract_document
content = extract_document(file_path, file_type)
```

**New:**
```python
from api.document_extraction.extract import extract
content = extract(file_path)  # Auto-detects type
```

The new system provides the same functionality with improved reliability, extensibility, and maintainability.