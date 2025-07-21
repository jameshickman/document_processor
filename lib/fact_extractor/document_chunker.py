import re
from typing import List

from api.util.pdf_extract import CHUNK_SIZE


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
        
        sentences = self.split_into_sentences(document_text)
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for sentence in sentences:
            sentence_word_count = self.count_words(sentence)
            
            # If adding this sentence would exceed the limit, save current chunk
            if current_word_count + sentence_word_count > self.max_words and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_word_count = sentence_word_count
            else:
                current_chunk.append(sentence)
                current_word_count += sentence_word_count
        
        # Add the last chunk if it has content
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks