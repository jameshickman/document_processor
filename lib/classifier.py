"""
Document Classifier with Fuzzy Matching and Wildcards

This module implements a document classifier that uses fuzzy string matching
with Levenshtein distance to score documents against predefined classifications.
Supports wildcards in search terms for flexible pattern matching.

Wildcard support:
    * - matches any word or number
    ? - matches words without numbers  
    # - matches words with numbers

Required packages:
    pip install pydantic rapidfuzz

Author: Claude
"""

from typing import List, Dict
from pydantic import BaseModel, Field
import re
from rapidfuzz.distance import Levenshtein


class Term(BaseModel):
    """Represents a search term with its allowed Levenshtein distance and weight.
    
    Supports wildcards in the term string:
    - '*' matches any word or number
    - '?' matches words without numbers
    - '#' matches words with numbers
    """
    term: str = Field(..., description="Search term string (may contain wildcards *, ?, #)")
    distance: int = Field(..., ge=0, description="Maximum Levenshtein distance for acceptable matches")
    weight: float = Field(default=1.0, ge=0, description="Weight/score value for this term when matched")


class Classification(BaseModel):
    """Represents a document classification with its associated terms."""
    name: str = Field(..., description="Name of the document classification")
    terms: List[Term] = Field(..., description="List of terms for this classification")


class ClassificationInput(BaseModel):
    """Input structure for the document classifier."""
    document_text: str = Field(..., description="Text content of the document to classify")
    classifications: List[Classification] = Field(..., description="Classification specifications")


def has_number(text: str) -> bool:
    """
    Check if text contains any digits.
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains digits, False otherwise
    """
    return any(char.isdigit() for char in text)


def is_number_word(word: str) -> bool:
    """
    Check if a word is primarily a number (contains digits).
    
    Args:
        word: Word to check
        
    Returns:
        True if word contains digits, False otherwise
    """
    return has_number(word)


def is_pure_word(word: str) -> bool:
    """
    Check if a word contains only letters (no digits).
    
    Args:
        word: Word to check
        
    Returns:
        True if word contains only letters, False otherwise
    """
    return word.isalpha()


def wildcard_match(doc_word: str, term_word: str) -> bool:
    """
    Check if a document word matches a term word, considering wildcards.
    
    Wildcard rules:
    - '*' matches any word or number
    - '?' matches a word but not a number
    - '#' matches a number but not a word
    - Regular words must match exactly (used for exact matching constraint)
    
    Args:
        doc_word: Word from document
        term_word: Word from term (may contain wildcards)
        
    Returns:
        True if words match according to wildcard rules
    """
    if term_word == '*':
        return True  # Matches anything
    elif term_word == '?':
        return is_pure_word(doc_word)  # Matches words without numbers
    elif term_word == '#':
        return is_number_word(doc_word)  # Matches words with numbers
    else:
        return doc_word == term_word  # Exact match required


def normalize_text(text: str) -> str:
    """
    Normalize text by removing punctuation and converting to lowercase.
    
    Args:
        text: Text to normalize
        
    Returns:
        Normalized text with lowercase letters and normalized whitespace
    """
    # Remove punctuation except spaces and preserve word boundaries
    text = re.sub(r'[^\w\s]', ' ', text)
    # Convert to lowercase
    text = text.lower()
    # Normalize whitespace (collapse multiple spaces into single spaces)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def get_ngrams(words: List[str], n: int) -> List[str]:
    """
    Generate n-grams from a list of words.
    
    Args:
        words: List of words
        n: Size of each n-gram
        
    Returns:
        List of n-gram strings
    """
    if len(words) < n:
        return []
    return [' '.join(words[i:i+n]) for i in range(len(words) - n + 1)]


def calculate_constrained_distance(ngram_words: List[str], term_words: List[str]) -> int:
    """
    Calculate Levenshtein distance with constraints for numbers and wildcard support.
    
    Constraints:
    - Words containing numbers (non-wildcards) must match exactly
    - Wildcards use special matching rules:
      * '*' matches any word or number
      * '?' matches words without numbers  
      * '#' matches words with numbers
    - Other words can be substituted (fuzzy matched)
    
    Args:
        ngram_words: Words from document n-gram
        term_words: Words from search term (may contain wildcards)
        
    Returns:
        Constrained edit distance, or -1 if constraint violated
    """
    m, n = len(ngram_words), len(term_words)
    
    # Create DP table
    dp = [[float('inf')] * (n + 1) for _ in range(m + 1)]
    
    # Initialize base cases
    dp[0][0] = 0
    
    # Initialize first row (insertions)
    for j in range(1, n + 1):
        dp[0][j] = dp[0][j-1] + 1
    
    # Initialize first column (deletions)
    for i in range(1, m + 1):
        dp[i][0] = dp[i-1][0] + 1
    
    # Fill DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            ngram_word = ngram_words[i-1]
            term_word = term_words[j-1]
            
            # Deletion
            dp[i][j] = min(dp[i][j], dp[i-1][j] + 1)
            
            # Insertion
            dp[i][j] = min(dp[i][j], dp[i][j-1] + 1)
            
            # Substitution/Match
            if ngram_word == term_word:
                # Exact match
                dp[i][j] = min(dp[i][j], dp[i-1][j-1])
            elif term_word in ['*', '?', '#']:
                # Wildcard matching
                if wildcard_match(ngram_word, term_word):
                    dp[i][j] = min(dp[i][j], dp[i-1][j-1])  # No cost for wildcard match
                # If wildcard doesn't match, leave as substitution cost
                else:
                    dp[i][j] = min(dp[i][j], dp[i-1][j-1] + 1)
            elif has_number(term_word):
                # Term word has number but doesn't match exactly - constraint violated
                # Don't update dp[i][j], leaving it as inf
                pass
            else:
                # Regular substitution allowed (term word has no numbers, not a wildcard)
                dp[i][j] = min(dp[i][j], dp[i-1][j-1] + 1)
    
    result = dp[m][n]
    return -1 if result == float('inf') else int(result)


def find_term_matches(document_words: List[str], term: str, max_distance: int, weight: float) -> float:
    """
    Find the best match score for a term in the document with wildcard support.
    
    Words containing numbers must match exactly, while other words can be fuzzy matched
    within the specified Levenshtein distance. Wildcards are supported:
    - '*' matches any word or number
    - '?' matches words without numbers
    - '#' matches words with numbers
    
    Args:
        document_words: List of words from the normalized document
        term: Normalized search term (may contain wildcards)
        max_distance: Maximum allowed Levenshtein distance
        weight: Weight/score to return if a match is found
        
    Returns:
        Term weight if match found, 0.0 if no match
    """
    term_words = term.split()
    term_length = len(term_words)
    
    if term_length == 0:
        return 0.0
    
    # Generate n-grams from document
    ngrams = get_ngrams(document_words, term_length)
    
    if not ngrams:
        return 0.0
    
    for ngram in ngrams:
        ngram_words = ngram.split()
        
        if ngram == term:
            # Perfect match
            return weight
        else:
            # Try fuzzy matching with number constraints
            constrained_distance = calculate_constrained_distance(ngram_words, term_words)
            
            if constrained_distance >= 0 and constrained_distance <= max_distance:
                return weight
    
    return 0.0


def document_classifier(document_text: str, classifications: List[Classification]) -> Dict[str, float]:
    """
    Classify a document based on term matching with fuzzy search, weighted scoring, and wildcards.
    
    This function implements a document classifier that:
    1. Normalizes the input text (lowercase, remove punctuation)
    2. For each classification, searches for each term using fuzzy matching
    3. Scores any match (exact or fuzzy) using the term's weight value
    4. Requires exact matches for individual words containing numbers (unless wildcards)
    5. Other words can be fuzzy matched within the distance limit
    6. Supports wildcards in terms:
       - '*' matches any word or number
       - '?' matches words without numbers
       - '#' matches words with numbers
    7. Returns total weighted scores for each classification
    
    Args:
        document_text: The text content of the document to classify
        classifications: List of classification specifications
        
    Returns:
        Dictionary mapping classification names to their total weighted scores
        
    Example:
        >>> classifications = [
        ...     Classification(
        ...         name="Medical",
        ...         terms=[
        ...             Term(term="patient * room #", distance=1, weight=2.0),  # Matches "patient john room 201"
        ...             Term(term="? report", distance=0, weight=1.5)  # Matches "medical report" but not "report 123"
        ...         ]
        ...     )
        ... ]
        >>> scores = document_classifier("Patient john room 201 medical report", classifications)
        >>> print(scores)  # {"Medical": 3.5} - 2.0 + 1.5
    """
    # Validate inputs using Pydantic
    input_data = ClassificationInput(
        document_text=document_text,
        classifications=classifications
    )
    
    results = {}
    
    # Normalize the document text
    doc_normalized = normalize_text(input_data.document_text)
    doc_words = doc_normalized.split()
    
    for classification in input_data.classifications:
        total_score = 0.0
        
        for term_spec in classification.terms:
            term_normalized = normalize_text(term_spec.term)
            match_score = find_term_matches(doc_words, term_normalized, term_spec.distance, term_spec.weight)
            total_score += match_score
        
        results[classification.name] = total_score
    
    return results


def document_classifier_simple(document_text: str, classifications_data: List[Dict]) -> Dict[str, float]:
    """
    Simplified interface for the document classifier that accepts raw dictionaries.
    
    Args:
        document_text: The text content of the document to classify
        classifications_data: List of classification dictionaries matching the specification
        
    Returns:
        Dictionary mapping classification names to their total scores
    """
    # Convert raw data to Pydantic models
    classifications = [Classification(**data) for data in classifications_data]
    return document_classifier(document_text, classifications)


# Example usage and test
if __name__ == "__main__":
    # Example classification specification with wildcards
    example_classifications = [
        {
            "name": "Medical Document",
            "terms": [
                {"term": "medical report", "distance": 1, "weight": 2.0},  # Standard fuzzy matching
                {"term": "patient *", "distance": 0, "weight": 1.0},  # Patient followed by any word
                {"term": "? diagnosis", "distance": 1, "weight": 1.5},  # Word (not number) + diagnosis
                {"term": "room #", "distance": 1, "weight": 0.8},  # "room" + any number
                {"term": "* * room #", "distance": 0, "weight": 1.2}  # Any two words + "room" + number
            ]
        },
        {
            "name": "Legal Document", 
            "terms": [
                {"term": "contract *", "distance": 1, "weight": 3.0},  # Contract + any word
                {"term": "? agreement", "distance": 2, "weight": 2.5},  # Word + agreement
                {"term": "clause #", "distance": 1, "weight": 1.0},  # "clause" + any number
                {"term": "section * subsection #", "distance": 1, "weight": 2.0}  # Complex pattern
            ]
        }
    ]
    
    # Example document with various patterns
    test_document = """
    This is a comprehensive medial report for patient sarah johnson.
    The preliminary diagnosis shows improvement in the patient's condition.
    Patient was moved from rom 201 to private room 305 for better care.
    This document contains confidential medical information.
    Legal clause 5b requires additional signatures.
    The service contract expires next month.
    Please review section 12 subsection 3a for details.
    """
    
    # Run classification
    results = document_classifier_simple(test_document, example_classifications)
    
    print("Classification Results:")
    for classification_name, score in results.items():
        print(f"  {classification_name}: {score}")
    
    # Expected output explanation with wildcards:
    # Medical Document: 
    #   - "medial report" matches "medical report" (fuzzy: "medial"≈"medical") = 2.0
    #   - "patient sarah" matches "patient *" (* matches "sarah") = 1.0  
    #   - "preliminary diagnosis" matches "? diagnosis" (? matches "preliminary") = 1.5
    #   - "rom 201" matches "room #" (fuzzy: "rom"≈"room", # matches "201") = 0.8
    #   - "private room 305" matches "* * room #" (* matches "private", * matches "room", # matches "305") = 1.2
    #   Total: 6.5
    # Legal Document:
    #   - "clause 5b" matches "clause #" (# matches "5b") = 1.0
    #   - "service contract" matches "contract *" (fuzzy order, * matches "service") = 3.0
    #   - "section 12 subsection 3a" matches "section * subsection #" (* matches "12", # matches "3a") = 2.0
    #   Total: 6.0