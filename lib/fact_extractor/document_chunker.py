import re
import logging
from typing import List

from api.util.pdf_extract import CHUNK_SIZE

logger = logging.getLogger(__name__)


class DocumentChunker:
    """Utility class for splitting documents into manageable chunks."""
    
    def __init__(self, max_words: int = CHUNK_SIZE):
        self.max_words = max_words
    
    def count_words(self, text: str) -> int:
        """Count words in a text string."""
        return len(re.findall(r'\b\w+\b', text))
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex."""
        # Simple sentence splitting - can be enhanced with nltk/spacy for better accuracy
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk_document(self, document_text: str) -> List[str]:
        """
        Split document into chunks of no more than max_words.
        Preserves sentence boundaries when possible.
        """
        word_count = self.count_words(document_text)
        
        if word_count <= self.max_words:
            return [document_text]

        chunks = []

        words = document_text.split()
        for i in range(0, len(words), CHUNK_SIZE):
            i_from = i
            if i > 0:
                i_from = i - 200
            l_chunk = words[i_from:i + CHUNK_SIZE]
            logger.info("Text chunk size: %s", len(l_chunk))
            chunk_text = " ".join(l_chunk)
            chunks.append(chunk_text)
        
        return chunks