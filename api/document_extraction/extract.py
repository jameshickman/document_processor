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

    Return the extracted content.
    """
    import os
    import importlib
    import inspect
    import tempfile
    from pathlib import Path
    from api.document_extraction.handler_base import DocumentExtractionBase
    from api.util.files_abstraction import get_filesystem

    # Get file extension
    file_extension = Path(input_file).suffix.lower().lstrip('.')

    # Handle Markdown and text files directly
    if file_extension in ['md', 'txt', '']:
        fs = get_filesystem()
        content = fs.read_file(input_file)
        return content.decode('utf-8')

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