class DocumentDecodeException(Exception):
    pass


class DocumentUnknownTypeException(Exception):
    pass

def extract(input_file: str) -> str:
    """
    If the input_file is Markdown or raw text, no conversion needed, return the content.

    Read the contents of the handlers package, the modules in this
    package contain classes derived from DocumentExtractionBase.
    Call the static method format() to determine the file types supported
    by each.

    Then instantiate and run the appropriate handler for the type of the input file.

    IMPORTANT: This function expects a LOCAL filesystem path, not a storage path.
    When using S3 storage, the caller must use fs.get_local_path() to download
    the file before calling this function.

    Return the extracted content.
    """
    import os
    import importlib
    import inspect
    import tempfile
    from pathlib import Path
    from api.document_extraction.handler_base import DocumentExtractionBase

    # Get file extension
    file_extension = Path(input_file).suffix.lower().lstrip('.')

    # Handle Markdown and text files directly
    if file_extension in ['md', 'txt', '']:
        with open(input_file, 'r', encoding='utf-8') as f:
            return f.read()

    # Discover all handler classes dynamically
    handlers_dir = Path(__file__).parent / 'handlers'
    handler_classes = []

    # Scan all Python files in the handlers directory
    for py_file in handlers_dir.glob('*.py'):
        if py_file.name == '__init__.py':
            continue

        module_name = f'api.document_extraction.handlers.{py_file.stem}'
        try:
            module = importlib.import_module(module_name)

            # Find all classes that inherit from DocumentExtractionBase
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (obj != DocumentExtractionBase and
                    issubclass(obj, DocumentExtractionBase) and
                    obj.__module__ == module_name):
                    handler_classes.append(obj)
        except ImportError:
            continue

    # Create temporary directory for handlers
    with tempfile.TemporaryDirectory() as temp_dir:
        # Find appropriate handler
        for handler_class in handler_classes:
            supported_formats = handler_class.format()
            if file_extension in supported_formats:
                handler = handler_class(temp_dir=temp_dir)
                return handler.extract(input_file)

        # No handler found for this file type
        raise DocumentUnknownTypeException(f"No handler found for file type: {file_extension}")