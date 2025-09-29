from api.document_extraction.handler_base import DocumentExtractionBase

class PDFextractionHandler(DocumentExtractionBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def format() -> list[str]:
        return ['pdf']

    def extract(self, input_file: str) -> str:
        """
        Implement logic to use pdftotext to read the text from the PDF file.

        Use the is_real_words to make sure usable text extracted from the PDF
        and throw the DocumentDecodeException if the result is garbage.
        """
        import subprocess
        from api.document_extraction.handler_base import find_exe, is_real_words
        from api.document_extraction.extract import DocumentDecodeException

        # Use pdftotext to extract text
        command = [find_exe("pdftotext"), input_file, "-"]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            raise DocumentDecodeException(f"pdftotext failed: {result.stderr}")

        content = result.stdout.strip()

        if not content or not is_real_words(content):
            raise DocumentDecodeException("PDF extraction failed or produced garbage text")

        return content