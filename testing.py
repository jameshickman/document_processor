import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
from typing import Dict, List

from lib.classifier import (
    Term, Classification, ClassificationInput,
    has_number, is_number_word, is_pure_word, wildcard_match,
    normalize_text, get_ngrams, calculate_constrained_distance,
    find_term_matches, document_classifier, document_classifier_simple
)

from lib.fact_extractor.fact_extractor import FactExtractor
from lib.fact_extractor.models import LLMConfig, ExtractionQuery, ExtractionResult


class TestClassifier(unittest.TestCase):

    def test_has_number(self):
        self.assertTrue(has_number("test123"))
        self.assertTrue(has_number("123"))
        self.assertTrue(has_number("test1"))
        self.assertFalse(has_number("test"))
        self.assertFalse(has_number(""))

    def test_is_number_word(self):
        self.assertTrue(is_number_word("123"))
        self.assertTrue(is_number_word("test123"))
        self.assertFalse(is_number_word("test"))
        self.assertFalse(is_number_word(""))

    def test_is_pure_word(self):
        self.assertTrue(is_pure_word("test"))
        self.assertTrue(is_pure_word("TEST"))
        self.assertFalse(is_pure_word("test123"))
        self.assertFalse(is_pure_word("123"))
        self.assertFalse(is_pure_word("test-word"))

    def test_wildcard_match(self):
        # Test * wildcard
        self.assertTrue(wildcard_match("anything", "*"))
        self.assertTrue(wildcard_match("123", "*"))
        
        # Test ? wildcard
        self.assertTrue(wildcard_match("word", "?"))
        self.assertFalse(wildcard_match("word123", "?"))
        self.assertFalse(wildcard_match("123", "?"))
        
        # Test # wildcard
        self.assertTrue(wildcard_match("123", "#"))
        self.assertTrue(wildcard_match("word123", "#"))
        self.assertFalse(wildcard_match("word", "#"))
        
        # Test exact match
        self.assertTrue(wildcard_match("exact", "exact"))
        self.assertFalse(wildcard_match("exact", "different"))

    def test_normalize_text(self):
        self.assertEqual(normalize_text("Hello, World!"), "hello world")
        self.assertEqual(normalize_text("  Multiple   spaces  "), "multiple spaces")
        self.assertEqual(normalize_text("UPPERCASE"), "uppercase")
        self.assertEqual(normalize_text("Test-123"), "test 123")

    def test_get_ngrams(self):
        words = ["the", "quick", "brown", "fox"]
        self.assertEqual(get_ngrams(words, 1), ["the", "quick", "brown", "fox"])
        self.assertEqual(get_ngrams(words, 2), ["the quick", "quick brown", "brown fox"])
        self.assertEqual(get_ngrams(words, 3), ["the quick brown", "quick brown fox"])
        self.assertEqual(get_ngrams(words, 5), [])

    def test_calculate_constrained_distance(self):
        # Test exact match
        self.assertEqual(calculate_constrained_distance(["test"], ["test"]), 0)
        
        # Test number constraint violation
        self.assertEqual(calculate_constrained_distance(["test"], ["test123"]), -1)
        
        # Test wildcard matching
        self.assertEqual(calculate_constrained_distance(["word"], ["*"]), 0)
        self.assertEqual(calculate_constrained_distance(["word"], ["?"]), 0)
        self.assertEqual(calculate_constrained_distance(["word123"], ["#"]), 0)
        
        # Test wildcard constraint violation
        self.assertEqual(calculate_constrained_distance(["word123"], ["?"]), -1)

    def test_find_term_matches(self):
        document_words = ["the", "quick", "brown", "fox", "jumps"]
        
        # Test exact match
        score = find_term_matches(document_words, "quick brown", 0, 1.0)
        self.assertEqual(score, 1.0)
        
        # Test no match
        score = find_term_matches(document_words, "elephant", 0, 1.0)
        self.assertEqual(score, 0.0)
        
        # Test wildcard match
        score = find_term_matches(document_words, "* brown", 0, 2.0)
        self.assertEqual(score, 2.0)

    def test_document_classifier(self):
        document_text = "The quick brown fox jumps over the lazy dog"
        
        classifications = [
            Classification(
                name="animal_document",
                terms=[
                    Term(term="fox", distance=0, weight=1.0),
                    Term(term="dog", distance=0, weight=1.0)
                ]
            ),
            Classification(
                name="color_document",
                terms=[
                    Term(term="brown", distance=0, weight=0.5),
                    Term(term="green", distance=0, weight=0.5)
                ]
            )
        ]
        
        results = document_classifier(document_text, classifications)
        self.assertEqual(results["animal_document"], 2.0)
        self.assertEqual(results["color_document"], 0.5)

    def test_document_classifier_simple(self):
        document_text = "Test document with numbers 123"
        
        classifications_data = [
            {
                "name": "test_classification",
                "terms": [
                    {"term": "test", "distance": 0, "weight": 1.0},
                    {"term": "numbers #", "distance": 0, "weight": 2.0}
                ]
            }
        ]
        
        results = document_classifier_simple(document_text, classifications_data)
        self.assertEqual(results["test_classification"], 3.0)

    def test_pydantic_models(self):
        # Test Term model
        term = Term(term="test", distance=1, weight=2.0)
        self.assertEqual(term.term, "test")
        self.assertEqual(term.distance, 1)
        self.assertEqual(term.weight, 2.0)
        
        # Test Classification model
        classification = Classification(
            name="test_class",
            terms=[Term(term="test", distance=0, weight=1.0)]
        )
        self.assertEqual(classification.name, "test_class")
        self.assertEqual(len(classification.terms), 1)


class TestFactExtractor(unittest.TestCase):

    def setUp(self):
        # Use the same environment variable configuration as production
        self.config = LLMConfig(
            base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.environ.get("OPENAI_API_KEY", "test_key"),
            model_name=os.environ.get("OPENAI_MODEL_NAME", "gemma3n"),
            temperature=float(os.environ.get("OPENAI_TEMPERATURE", 0.05)),
            max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", 2048)),
            timeout=int(os.environ.get("OPENAI_TIMEOUT", 360)),
        )
        
    @patch('lib.fact_extractor.fact_extractor.ChatOpenAI')
    def test_initialization(self, mock_chat_openai):
        extractor = FactExtractor(self.config)
        
        self.assertEqual(extractor.config, self.config)
        self.assertIsNotNone(extractor.chunker)
        self.assertIsNotNone(extractor.prompt_builder)
        mock_chat_openai.assert_called_once()

    def test_parse_llm_response_valid_json(self):
        extractor = FactExtractor(self.config)
        
        response_text = """
        Here is the extracted information:
        {
            "confidence": 0.95,
            "found": true,
            "explanation": "Found the requested information",
            "field1": "value1",
            "field2": "value2"
        }
        """
        
        fields = {"field1": "Description 1", "field2": "Description 2"}
        result = extractor._parse_llm_response(response_text, fields)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.confidence, 0.95)
        self.assertTrue(result.found)
        self.assertEqual(result.explanation, "Found the requested information")
        self.assertEqual(result.extracted_data["field1"], "value1")
        self.assertEqual(result.extracted_data["field2"], "value2")

    def test_parse_llm_response_invalid_json(self):
        extractor = FactExtractor(self.config)
        
        response_text = "This is not valid JSON"
        fields = {"field1": "Description 1"}
        result = extractor._parse_llm_response(response_text, fields)
        
        self.assertIsNone(result)

    def test_parse_llm_response_malformed_json(self):
        extractor = FactExtractor(self.config)
        
        response_text = '{"confidence": 0.8, "found": true, "incomplete": '
        fields = {"field1": "Description 1"}
        result = extractor._parse_llm_response(response_text, fields)
        
        self.assertIsNone(result)

    @patch('lib.fact_extractor.fact_extractor.ChatOpenAI')
    def test_extract_facts_found(self, mock_chat_openai):
        # Mock the LLM response
        mock_response = Mock()
        mock_response.content = """
        {
            "confidence": 0.9,
            "found": true,
            "explanation": "Information found in document",
            "name": "John Doe",
            "age": "30"
        }
        """
        
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm_instance
        
        extractor = FactExtractor(self.config)
        
        document_text = "John Doe is 30 years old and works as an engineer."
        query = ExtractionQuery(
            query="Find person's name and age",
            fields={"name": "Person's full name", "age": "Person's age"}
        )
        
        result = extractor.extract_facts(document_text, query)
        
        self.assertIsNotNone(result)
        self.assertTrue(result.found)
        self.assertEqual(result.confidence, 0.9)
        self.assertEqual(result.extracted_data["name"], "John Doe")
        self.assertEqual(result.extracted_data["age"], "30")

    @patch('lib.fact_extractor.fact_extractor.ChatOpenAI')
    def test_extract_facts_not_found(self, mock_chat_openai):
        # Mock the LLM response
        mock_response = Mock()
        mock_response.content = """
        {
            "confidence": 0.1,
            "found": false,
            "explanation": "Information not found in document"
        }
        """
        
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm_instance
        
        extractor = FactExtractor(self.config)
        
        document_text = "This document talks about weather patterns."
        query = ExtractionQuery(
            query="Find person's name and age",
            fields={"name": "Person's full name", "age": "Person's age"}
        )
        
        result = extractor.extract_facts(document_text, query)
        
        self.assertIsNotNone(result)
        self.assertFalse(result.found)

    @patch('lib.fact_extractor.fact_extractor.ChatOpenAI')
    def test_extract_facts_llm_error(self, mock_chat_openai):
        # Mock LLM to raise an exception
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.side_effect = Exception("LLM API Error")
        mock_chat_openai.return_value = mock_llm_instance
        
        extractor = FactExtractor(self.config)
        
        document_text = "Test document"
        query = ExtractionQuery(
            query="Find something",
            fields={"field": "Field description"}
        )
        
        result = extractor.extract_facts(document_text, query)
        
        # Should return default not found result when all chunks fail
        self.assertIsNotNone(result)
        self.assertFalse(result.found)
        self.assertEqual(result.confidence, 0.0)

    @patch('lib.fact_extractor.fact_extractor.ChatOpenAI')
    def test_extract_facts_chunked_document(self, mock_chat_openai):
        # Mock the LLM response for found case
        mock_response = Mock()
        mock_response.content = """
        {
            "confidence": 0.85,
            "found": true,
            "explanation": "Found in second chunk",
            "info": "target information"
        }
        """
        
        mock_llm_instance = Mock()
        mock_llm_instance.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm_instance
        
        extractor = FactExtractor(self.config)
        
        # Create a document that will be chunked (assuming CHUNK_SIZE is around 1000)
        large_document = "word " * 2000  # This should trigger chunking
        
        query = ExtractionQuery(
            query="Find specific information",
            fields={"info": "Target information"}
        )
        
        result = extractor.extract_facts(large_document, query)
        
        self.assertIsNotNone(result)
        self.assertTrue(result.found)
        self.assertEqual(result.extracted_data["info"], "target information")

    @patch('lib.fact_extractor.fact_extractor.ChatOpenAI')
    def test_llm_initialization_with_production_config(self, mock_chat_openai):
        extractor = FactExtractor(self.config)
        
        # Verify that ChatOpenAI was called with the production configuration
        mock_chat_openai.assert_called_once_with(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            model=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=self.config.timeout
        )


class TestFactExtractorModels(unittest.TestCase):

    def test_extraction_query_valid(self):
        query = ExtractionQuery(
            query="What is the person's name?",
            fields={"name": "Full name of the person"}
        )
        self.assertEqual(query.query, "What is the person's name?")
        self.assertEqual(query.fields["name"], "Full name of the person")

    def test_extraction_query_empty_query(self):
        with self.assertRaises(ValueError):
            ExtractionQuery(
                query="",
                fields={"name": "Full name"}
            )

    def test_extraction_query_empty_fields(self):
        with self.assertRaises(ValueError):
            ExtractionQuery(
                query="What is the name?",
                fields={}
            )

    def test_extraction_result_valid(self):
        result = ExtractionResult(
            confidence=0.85,
            found=True,
            explanation="Found the information",
            extracted_data={"name": "John Doe"}
        )
        self.assertEqual(result.confidence, 0.85)
        self.assertTrue(result.found)
        self.assertEqual(result.explanation, "Found the information")
        self.assertEqual(result.extracted_data["name"], "John Doe")

    def test_extraction_result_confidence_rounding(self):
        result = ExtractionResult(
            confidence=0.123456,
            found=True,
            explanation="Test",
            extracted_data={}
        )
        self.assertEqual(result.confidence, 0.123)

    def test_llm_config_defaults(self):
        config = LLMConfig(api_key="test_key")
        self.assertEqual(config.base_url, "https://api.openai.com/v1")
        self.assertEqual(config.model_name, "gpt-3.5-turbo")
        self.assertEqual(config.temperature, 0.1)
        self.assertEqual(config.max_tokens, 2000)
        self.assertEqual(config.timeout, 60)

    def test_llm_config_production_defaults(self):
        # Test using the same defaults as production
        config = LLMConfig(
            base_url=os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.environ.get("OPENAI_API_KEY", "test_key"),
            model_name=os.environ.get("OPENAI_MODEL_NAME", "gemma3n"),
            temperature=float(os.environ.get("OPENAI_TEMPERATURE", 0.05)),
            max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", 2048)),
            timeout=int(os.environ.get("OPENAI_TIMEOUT", 360)),
        )
        
        # Verify defaults match production
        if "OPENAI_BASE_URL" not in os.environ:
            self.assertEqual(config.base_url, "http://localhost:11434/v1")
        if "OPENAI_MODEL_NAME" not in os.environ:
            self.assertEqual(config.model_name, "gemma3n")
        if "OPENAI_TEMPERATURE" not in os.environ:
            self.assertEqual(config.temperature, 0.05)
        if "OPENAI_MAX_TOKENS" not in os.environ:
            self.assertEqual(config.max_tokens, 2048)
        if "OPENAI_TIMEOUT" not in os.environ:
            self.assertEqual(config.timeout, 360)


if __name__ == '__main__':
    unittest.main()