from api.document_extraction.handler_base import DocumentExtractionBase

class HTMLExtractionHandler(DocumentExtractionBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def format() -> list[str]:
        return ['html', 'htm']

    def extract(self, input_file: str) -> str:
        """
        Use the PanDoc helper to convert the HTML to Markdown
        """
        return self.pandoc_convert(input_file, "html", "HTML extraction failed")