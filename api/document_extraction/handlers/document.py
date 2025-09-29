from api.document_extraction.extract import DocumentDecodeException
from api.document_extraction.handler_base import DocumentExtractionBase


class OfficeDocumentExtractionHandler(DocumentExtractionBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def format() -> list[str]:
        return ['doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'rtf', 'odt']

    def extract(self, input_file: str) -> str:
        """
        Implement logic to extract text from input file, if possible convert to Markdown, else raw text
        """
        from pathlib import Path
        from api.document_extraction.extract import DocumentDecodeException

        file_ext = Path(input_file).suffix.lower().lstrip('.')

        # Try direct pandoc conversion to Markdown first
        try:
            return self.pandoc_convert(input_file, file_ext, f"{file_ext.upper()} to Markdown conversion failed")
        except DocumentDecodeException:
            # If direct conversion fails, try via OpenOffice
            try:
                converted_file = self._openoffice_convert(input_file)
                return self.pandoc_convert(converted_file, "odt", "Office document to Markdown conversion failed")
            except DocumentDecodeException:
                # Final fallback: extract as plain text
                return self._extract_as_text(input_file)

    def _openoffice_convert(self, input_file: str) -> str:
        """
        Use OpenOffice headless, soffice executable, to convert the input_file to a format
        that can be converted into Markdown. This is for the case of more complex documents that
        PanDoc cannot convert directly.
        """
        import subprocess
        import os
        from pathlib import Path
        from api.document_extraction.handler_base import find_exe
        from api.document_extraction.extract import DocumentDecodeException

        # Convert to ODT using LibreOffice headless
        output_file = os.path.join(self.temp_dir, f"{Path(input_file).stem}.odt")

        command = [
            find_exe("soffice"),
            "--headless",
            "--convert-to", "odt",
            "--outdir", self.temp_dir,
            input_file
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0 or not os.path.exists(output_file):
            raise DocumentDecodeException(f"LibreOffice conversion failed: {result.stderr}")

        return output_file

    def _extract_as_text(self, input_file: str) -> str:
        """
        Fallback method to extract plain text using pandoc
        """
        from pathlib import Path

        file_ext = Path(input_file).suffix.lower().lstrip('.')

        # Try pandoc with plain text output as final fallback
        try:
            import subprocess
            from api.document_extraction.handler_base import find_exe, is_real_words

            command = [find_exe("pandoc"), input_file, "-f", file_ext, "-t", "plain"]
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0:
                content = result.stdout.strip()
                if content and is_real_words(content):
                    return content
        except:
            pass

        raise DocumentDecodeException("Unable to extract content from office document")