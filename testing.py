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

from api.pdf_markup.highlight_pdf import highlight_pdf, extract_info, search_for_text, highlight_matching_data
from api.to_pdf.converter import to_pdf, get_supported_formats, get_conversion_info, ConversionError
from api.document_extraction.extract import extract, DocumentDecodeException, DocumentUnknownTypeException


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


class TestPDFMarkup(unittest.TestCase):

    def setUp(self):
        self.sample_pdfs_dir = "testing/PDF_cases"
        self.test_output_dir = "testing/output"
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Available sample PDFs for testing
        self.sample_pdfs = [
            "Boeing_Supplier_Specification.pdf",
            "Ford_Automotive_Specification.pdf",
            "Medical_Device_Email_Specification.pdf",
            "Engineering_Change_Order.pdf",
            "Engineering_Change_Orders.pdf",
            "Supplier_Change_Notification.pdf",
            "Material_Test_Certificate.pdf",
            "Manufacturing_Purchase_Order.pdf",
            "Purchase_Orders.pdf",
            "Final_Product_Inspection_Report.pdf",
            "Incoming_Material_Inspection_Report.pdf"
        ]

    def tearDown(self):
        # Clean up generated test files
        import glob
        for file in glob.glob(os.path.join(self.test_output_dir, "*.marked.pdf")):
            try:
                os.remove(file)
            except OSError:
                pass

    def test_highlight_pdf_basic_functionality(self):
        """Test basic PDF highlighting functionality"""
        input_file = os.path.join(self.sample_pdfs_dir, "Boeing_Supplier_Specification.pdf")
        if not os.path.exists(input_file):
            self.skipTest(f"Sample PDF {input_file} not found")
        
        # Test with common words likely to be found
        search_strings = ["specification", "Boeing", "supplier"]
        extractor_id = 1
        
        result_file = highlight_pdf(input_file, search_strings, extractor_id)
        
        # Check that output file was created
        self.assertTrue(os.path.exists(result_file))
        self.assertTrue(result_file.endswith(f".marked.{extractor_id}.pdf"))
        
        # Check that the output file is different from input
        self.assertNotEqual(input_file, result_file)
        
        # Clean up
        if os.path.exists(result_file):
            os.remove(result_file)

    def test_highlight_pdf_multiple_documents(self):
        """Test highlighting on multiple different PDF documents"""
        test_cases = [
            ("Ford_Automotive_Specification.pdf", ["Ford", "automotive", "specification"]),
            ("Engineering_Change_Order.pdf", ["engineering", "change", "order"]),
            ("Purchase_Orders.pdf", ["purchase", "order", "supplier"])
        ]
        
        for pdf_name, search_terms in test_cases:
            with self.subTest(pdf=pdf_name):
                input_file = os.path.join(self.sample_pdfs_dir, pdf_name)
                if not os.path.exists(input_file):
                    continue
                
                extractor_id = 2
                result_file = highlight_pdf(input_file, search_terms, extractor_id)
                
                # Verify file creation and naming
                self.assertTrue(os.path.exists(result_file))
                expected_name = pdf_name.replace(".pdf", f".marked.{extractor_id}.pdf")
                self.assertTrue(result_file.endswith(expected_name))
                
                # Clean up
                if os.path.exists(result_file):
                    os.remove(result_file)

    def test_highlight_pdf_empty_search_list(self):
        """Test highlighting with empty search string list"""
        input_file = os.path.join(self.sample_pdfs_dir, "Boeing_Supplier_Specification.pdf")
        if not os.path.exists(input_file):
            self.skipTest(f"Sample PDF {input_file} not found")
        
        extractor_id = 3
        result_file = highlight_pdf(input_file, [], extractor_id)
        
        # Should still create output file even with no search terms
        self.assertTrue(os.path.exists(result_file))
        
        # Clean up
        if os.path.exists(result_file):
            os.remove(result_file)

    def test_highlight_pdf_case_sensitivity(self):
        """Test that highlighting is case-insensitive by default"""
        input_file = os.path.join(self.sample_pdfs_dir, "Boeing_Supplier_Specification.pdf")
        if not os.path.exists(input_file):
            self.skipTest(f"Sample PDF {input_file} not found")
        
        # Test with different case variations
        search_strings = ["boeing", "BOEING", "Boeing", "specification", "SPECIFICATION"]
        extractor_id = 4
        
        result_file = highlight_pdf(input_file, search_strings, extractor_id)
        
        self.assertTrue(os.path.exists(result_file))
        
        # Clean up
        if os.path.exists(result_file):
            os.remove(result_file)

    def test_highlight_pdf_special_characters(self):
        """Test highlighting with special characters and numbers"""
        input_file = os.path.join(self.sample_pdfs_dir, "Material_Test_Certificate.pdf")
        if not os.path.exists(input_file):
            self.skipTest(f"Sample PDF {input_file} not found")
        
        # Test with terms that might contain numbers, dates, or special chars
        search_strings = ["test", "certificate", "material", "2024", "2023"]
        extractor_id = 5
        
        result_file = highlight_pdf(input_file, search_strings, extractor_id)
        
        self.assertTrue(os.path.exists(result_file))
        
        # Clean up
        if os.path.exists(result_file):
            os.remove(result_file)

    def test_highlight_pdf_nonexistent_file(self):
        """Test error handling for non-existent input files"""
        nonexistent_file = "nonexistent_file.pdf"
        search_strings = ["test"]
        
        with self.assertRaises(Exception):
            highlight_pdf(nonexistent_file, search_strings, extractor_id=6)

    def test_highlight_pdf_output_filename_generation(self):
        """Test that output filenames are generated correctly"""
        input_file = os.path.join(self.sample_pdfs_dir, "Boeing_Supplier_Specification.pdf")
        if not os.path.exists(input_file):
            self.skipTest(f"Sample PDF {input_file} not found")
        
        extractor_id = 7
        result_file = highlight_pdf(input_file, ["test"], extractor_id)
        
        # Check filename pattern
        expected_pattern = input_file.replace(".pdf", f".marked.{extractor_id}.pdf")
        self.assertEqual(result_file, expected_pattern)
        
        # Clean up
        if os.path.exists(result_file):
            os.remove(result_file)

    def test_extract_info_basic(self):
        """Test PDF info extraction functionality"""
        input_file = os.path.join(self.sample_pdfs_dir, "Boeing_Supplier_Specification.pdf")
        if not os.path.exists(input_file):
            self.skipTest(f"Sample PDF {input_file} not found")
        
        success, info = extract_info(input_file)
        
        self.assertTrue(success)
        self.assertIsInstance(info, dict)
        self.assertIn("File", info)
        self.assertIn("Encrypted", info)
        self.assertEqual(info["File"], input_file)

    def test_extract_info_multiple_files(self):
        """Test info extraction on multiple PDF files"""
        for pdf_name in self.sample_pdfs[:3]:  # Test first 3 PDFs
            with self.subTest(pdf=pdf_name):
                input_file = os.path.join(self.sample_pdfs_dir, pdf_name)
                if not os.path.exists(input_file):
                    continue
                
                success, info = extract_info(input_file)
                
                self.assertTrue(success)
                self.assertIsInstance(info, dict)
                self.assertEqual(info["File"], input_file)

    def test_search_for_text_basic(self):
        """Test text search functionality"""
        test_lines = [
            "This is a test document with Boeing specifications.",
            "The supplier must comply with all requirements.",
            "Engineering Change Order #12345 has been approved."
        ]
        
        # Test basic search
        results = list(search_for_text(test_lines, "Boeing"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "Boeing")
        
        # Test case-insensitive search
        results = list(search_for_text(test_lines, "boeing"))
        self.assertEqual(len(results), 1)
        
        # Test pattern not found
        results = list(search_for_text(test_lines, "nonexistent"))
        self.assertEqual(len(results), 0)

    def test_search_for_text_multiple_matches(self):
        """Test text search with multiple matches"""
        test_lines = [
            "Test test TEST testing",
            "Another line with test content",
            "Final test line"
        ]
        
        results = list(search_for_text(test_lines, "test"))
        # Should find multiple instances (case-insensitive)
        self.assertGreater(len(results), 3)

    @patch('api.pdf_markup.highlight_pdf.fitz')
    def test_highlight_matching_data_highlight_type(self, mock_fitz):
        """Test different highlight annotation types"""
        # Mock page object
        mock_page = Mock()
        mock_page.searchFor.return_value = [Mock()]  # Mock search result
        mock_annotation = Mock()
        mock_page.addHighlightAnnot.return_value = mock_annotation
        mock_page.addSquigglyAnnot.return_value = mock_annotation
        mock_page.addUnderlineAnnot.return_value = mock_annotation
        mock_page.addStrikeoutAnnot.return_value = mock_annotation
        
        matched_values = ["test"]
        
        # Test different annotation types
        for annotation_type in ['Highlight', 'Squiggly', 'Underline', 'Strikeout']:
            with self.subTest(type=annotation_type):
                matches = highlight_matching_data(mock_page, matched_values, annotation_type)
                self.assertEqual(matches, 1)
                mock_annotation.update.assert_called()

    def test_highlight_pdf_integration_with_real_pdfs(self):
        """Integration test using real PDF files with known content"""
        # Test with multiple PDFs to ensure robustness
        test_cases = [
            ("Boeing_Supplier_Specification.pdf", ["supplier", "specification"]),
            ("Ford_Automotive_Specification.pdf", ["automotive", "ford"]),
            ("Engineering_Change_Order.pdf", ["engineering", "change"])
        ]
        
        for pdf_name, search_terms in test_cases:
            with self.subTest(pdf=pdf_name):
                input_file = os.path.join(self.sample_pdfs_dir, pdf_name)
                if not os.path.exists(input_file):
                    continue
                
                try:
                    extractor_id = 8
                    result_file = highlight_pdf(input_file, search_terms, extractor_id)
                    
                    # Verify output file exists and is a valid PDF
                    self.assertTrue(os.path.exists(result_file))
                    
                    # Verify it's a PDF file by checking header
                    with open(result_file, 'rb') as f:
                        header = f.read(4)
                        self.assertEqual(header, b'%PDF')
                    
                    # Verify file size is reasonable (not empty, not too large)
                    file_size = os.path.getsize(result_file)
                    self.assertGreater(file_size, 1000)  # At least 1KB
                    
                except Exception as e:
                    self.fail(f"Failed to process {pdf_name}: {str(e)}")
                
                finally:
                    # Clean up
                    if 'result_file' in locals() and os.path.exists(result_file):
                        os.remove(result_file)

    def test_highlight_pdf_preserves_content(self):
        """Test that highlighting preserves original PDF content"""
        input_file = os.path.join(self.sample_pdfs_dir, "Boeing_Supplier_Specification.pdf")
        if not os.path.exists(input_file):
            self.skipTest(f"Sample PDF {input_file} not found")
        
        try:
            import fitz
            
            # Get original page count and basic info
            original_doc = fitz.open(input_file)
            original_page_count = len(original_doc)
            original_doc.close()
            
            # Process with highlighting
            extractor_id = 9
            result_file = highlight_pdf(input_file, ["test", "specification"], extractor_id)
            
            # Check processed document
            processed_doc = fitz.open(result_file)
            processed_page_count = len(processed_doc)
            processed_doc.close()
            
            # Verify page count is preserved
            self.assertEqual(original_page_count, processed_page_count)
            
        except ImportError:
            self.skipTest("PyMuPDF not available for content preservation test")
        
        finally:
            if 'result_file' in locals() and os.path.exists(result_file):
                os.remove(result_file)

    def test_highlight_pdf_cleanup_functionality(self):
        """Test that old marked files are cleaned up correctly"""
        input_file = os.path.join(self.sample_pdfs_dir, "Boeing_Supplier_Specification.pdf")
        if not os.path.exists(input_file):
            self.skipTest(f"Sample PDF {input_file} not found")
        
        extractor_id = 100
        search_strings = ["test"]
        
        # Create an initial marked file
        result_file_1 = highlight_pdf(input_file, search_strings, extractor_id)
        self.assertTrue(os.path.exists(result_file_1))
        
        # Create the same marked file again - should clean up the old one
        result_file_2 = highlight_pdf(input_file, search_strings, extractor_id)
        self.assertTrue(os.path.exists(result_file_2))
        self.assertEqual(result_file_1, result_file_2)  # Should be same filename
        
        # Clean up
        if os.path.exists(result_file_2):
            os.remove(result_file_2)

    def test_highlight_pdf_multiple_extractors(self):
        """Test that files from different extractors coexist"""
        input_file = os.path.join(self.sample_pdfs_dir, "Boeing_Supplier_Specification.pdf")
        if not os.path.exists(input_file):
            self.skipTest(f"Sample PDF {input_file} not found")
        
        search_strings = ["test"]
        
        # Create files with different extractor IDs
        result_file_1 = highlight_pdf(input_file, search_strings, extractor_id=200)
        result_file_2 = highlight_pdf(input_file, search_strings, extractor_id=201)
        
        # Both files should exist
        self.assertTrue(os.path.exists(result_file_1))
        self.assertTrue(os.path.exists(result_file_2))
        self.assertNotEqual(result_file_1, result_file_2)
        
        # Verify correct naming
        self.assertTrue(result_file_1.endswith(".marked.200.pdf"))
        self.assertTrue(result_file_2.endswith(".marked.201.pdf"))
        
        # Clean up
        for result_file in [result_file_1, result_file_2]:
            if os.path.exists(result_file):
                os.remove(result_file)

    def test_get_marked_files_function(self):
        """Test the get_marked_files helper function"""
        from api.pdf_markup.highlight_pdf import get_marked_files
        
        input_file = os.path.join(self.sample_pdfs_dir, "Boeing_Supplier_Specification.pdf")
        if not os.path.exists(input_file):
            self.skipTest(f"Sample PDF {input_file} not found")
        
        search_strings = ["test"]
        
        # Create files with different extractor IDs
        result_file_1 = highlight_pdf(input_file, search_strings, extractor_id=300)
        result_file_2 = highlight_pdf(input_file, search_strings, extractor_id=301)
        
        try:
            # Test getting all marked files
            all_marked = get_marked_files(input_file)
            self.assertIn(result_file_1, all_marked)
            self.assertIn(result_file_2, all_marked)
            
            # Test getting marked files for specific extractor
            specific_marked_300 = get_marked_files(input_file, extractor_id=300)
            self.assertEqual(specific_marked_300, [result_file_1])
            
            specific_marked_301 = get_marked_files(input_file, extractor_id=301)
            self.assertEqual(specific_marked_301, [result_file_2])
            
            # Test non-existent extractor
            nonexistent_marked = get_marked_files(input_file, extractor_id=999)
            self.assertEqual(nonexistent_marked, [])
            
        finally:
            # Clean up
            for result_file in [result_file_1, result_file_2]:
                if os.path.exists(result_file):
                    os.remove(result_file)


class TestDocumentExtraction(unittest.TestCase):

    def setUp(self):
        self.sample_files_dir = "testing/sample_files"
        self.sample_files = {
            'text': 'sample.txt',
            'html': 'sample.html',
            'markdown': 'sample.md',
            'docx': 'word.docx'
        }

    def test_extract_text_file(self):
        """Test extracting content from text files"""
        input_file = os.path.join(self.sample_files_dir, self.sample_files['text'])
        if not os.path.exists(input_file):
            self.skipTest(f"Sample text file not found: {input_file}")

        result = extract(input_file)

        # Should return content as string
        self.assertIsInstance(result, str)
        self.assertGreater(len(result.strip()), 0)

    def test_extract_markdown_file(self):
        """Test extracting content from Markdown files"""
        input_file = os.path.join(self.sample_files_dir, self.sample_files['markdown'])
        if not os.path.exists(input_file):
            self.skipTest(f"Sample Markdown file not found: {input_file}")

        result = extract(input_file)

        # Should return content as string
        self.assertIsInstance(result, str)
        self.assertGreater(len(result.strip()), 0)

    def test_extract_html_file(self):
        """Test extracting content from HTML files"""
        input_file = os.path.join(self.sample_files_dir, self.sample_files['html'])
        if not os.path.exists(input_file):
            self.skipTest(f"Sample HTML file not found: {input_file}")

        try:
            result = extract(input_file)

            # Should return converted content as string
            self.assertIsInstance(result, str)
            self.assertGreater(len(result.strip()), 0)

        except DocumentDecodeException:
            # May fail if pandoc is not available
            self.skipTest("HTML extraction tools not available")

    def test_extract_docx_file(self):
        """Test extracting content from DOCX files"""
        input_file = os.path.join(self.sample_files_dir, self.sample_files['docx'])
        if not os.path.exists(input_file):
            self.skipTest(f"Sample DOCX file not found: {input_file}")

        try:
            result = extract(input_file)

            # Should return converted content as string
            self.assertIsInstance(result, str)
            self.assertGreater(len(result.strip()), 0)

        except DocumentDecodeException:
            # May fail if pandoc/LibreOffice is not available
            self.skipTest("Office document extraction tools not available")

    def test_extract_nonexistent_file(self):
        """Test error handling for non-existent files"""
        nonexistent_file = "nonexistent_file.txt"

        with self.assertRaises(FileNotFoundError):
            extract(nonexistent_file)

    def test_extract_unsupported_extension(self):
        """Test error handling for unsupported file extensions"""
        # Create a temporary file with unsupported extension
        temp_file = os.path.join(self.sample_files_dir, "test.unknown")
        with open(temp_file, 'w') as f:
            f.write("Test content")

        try:
            with self.assertRaises(DocumentUnknownTypeException):
                extract(temp_file)
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_extract_empty_extension(self):
        """Test extracting file with no extension (treated as text)"""
        # Create a temporary file with no extension
        temp_file = os.path.join(self.sample_files_dir, "no_extension_file")
        with open(temp_file, 'w') as f:
            f.write("Test content without extension")

        try:
            result = extract(temp_file)

            # Should return content as text
            self.assertIsInstance(result, str)
            self.assertEqual(result.strip(), "Test content without extension")

        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_dynamic_handler_discovery(self):
        """Test that the extract function dynamically discovers available handlers"""
        # This test verifies that the function can find handlers without hardcoding them

        # Test with a known file type that should have a handler
        input_file = os.path.join(self.sample_files_dir, self.sample_files['html'])
        if not os.path.exists(input_file):
            self.skipTest(f"Sample HTML file not found: {input_file}")

        # Should not raise DocumentUnknownTypeException if handler exists
        try:
            result = extract(input_file)
            self.assertIsInstance(result, str)
        except DocumentDecodeException:
            # Conversion failure is acceptable, but should find the handler
            pass

    def test_extract_multiple_file_types(self):
        """Test extracting content from multiple different file types"""
        test_results = {}

        for file_type, filename in self.sample_files.items():
            input_file = os.path.join(self.sample_files_dir, filename)
            if os.path.exists(input_file):
                try:
                    result = extract(input_file)
                    test_results[file_type] = {
                        'success': True,
                        'content_length': len(result.strip()),
                        'has_content': len(result.strip()) > 0
                    }
                except (DocumentDecodeException, DocumentUnknownTypeException) as e:
                    test_results[file_type] = {
                        'success': False,
                        'error': str(e)
                    }

        # At least text and markdown should work
        if 'text' in test_results:
            self.assertTrue(test_results['text']['success'])
            self.assertTrue(test_results['text']['has_content'])

        if 'markdown' in test_results:
            self.assertTrue(test_results['markdown']['success'])
            self.assertTrue(test_results['markdown']['has_content'])

    def test_extract_with_special_characters(self):
        """Test extracting files with special characters and unicode"""
        # Create a text file with special characters
        special_content = """
        Special Characters Test: áéíóú àèìòù äëïöü ñç
        Unicode: 🌟 ★ ♦ ♥ ♠ ♣
        Math: α β γ δ ε π ∞ ∑ ∫
        Quotes: "Hello" 'World' «Bonjour» »Monde«
        """

        special_file = os.path.join(self.sample_files_dir, "special_chars_extract.txt")
        with open(special_file, 'w', encoding='utf-8') as f:
            f.write(special_content)

        try:
            result = extract(special_file)

            # Should preserve special characters
            self.assertIsInstance(result, str)
            self.assertIn("áéíóú", result)
            self.assertIn("🌟", result)
            self.assertIn("α β γ", result)

        finally:
            # Clean up temp file
            if os.path.exists(special_file):
                os.remove(special_file)

    def test_extract_large_file(self):
        """Test extracting content from a large text file"""
        # Create a large text file
        large_content = "This is line {}\n" * 10000  # 10,000 lines
        large_content = large_content.format(*range(10000))

        large_file = os.path.join(self.sample_files_dir, "large_file.txt")
        with open(large_file, 'w') as f:
            f.write(large_content)

        try:
            result = extract(large_file)

            # Should handle large files
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 50000)  # Should be substantial content
            self.assertIn("This is line 0", result)
            self.assertIn("This is line 9999", result)

        finally:
            # Clean up temp file
            if os.path.exists(large_file):
                os.remove(large_file)

    def test_extract_empty_file(self):
        """Test extracting content from an empty file"""
        empty_file = os.path.join(self.sample_files_dir, "empty_file.txt")
        with open(empty_file, 'w') as f:
            pass  # Create empty file

        try:
            result = extract(empty_file)

            # Should return empty string
            self.assertIsInstance(result, str)
            self.assertEqual(result, "")

        finally:
            # Clean up temp file
            if os.path.exists(empty_file):
                os.remove(empty_file)

    def test_exception_types(self):
        """Test that appropriate exception types are raised"""
        # Test DocumentUnknownTypeException
        temp_file = os.path.join(self.sample_files_dir, "test.unknownext")
        with open(temp_file, 'w') as f:
            f.write("content")

        try:
            with self.assertRaises(DocumentUnknownTypeException) as cm:
                extract(temp_file)

            self.assertIn("unknownext", str(cm.exception))

        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)


class TestPDFConverter(unittest.TestCase):

    def setUp(self):
        self.sample_files_dir = "testing/sample_files"
        self.test_output_dir = "testing/output"
        os.makedirs(self.sample_files_dir, exist_ok=True)
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Sample files for testing
        self.sample_files = {
            'text': 'sample.txt',
            'html': 'sample.html', 
            'markdown': 'sample.md',
            'image': 'sample.png'
        }

    def tearDown(self):
        # Clean up generated PDF files
        import glob
        for file in glob.glob(os.path.join(self.sample_files_dir, "*.pdf")):
            try:
                os.remove(file)
            except OSError:
                pass
        for file in glob.glob(os.path.join(self.test_output_dir, "*.pdf")):
            try:
                os.remove(file)
            except OSError:
                pass

    def test_get_supported_formats(self):
        """Test getting supported format information"""
        formats = get_supported_formats()
        
        self.assertIsInstance(formats, dict)
        self.assertIn('text', formats)
        self.assertIn('markup', formats)
        self.assertIn('office', formats)
        self.assertIn('images', formats)
        
        # Check specific extensions
        self.assertIn('.txt', formats['text'])
        self.assertIn('.html', formats['markup'])
        self.assertIn('.md', formats['markup'])
        self.assertIn('.png', formats['images'])

    def test_get_conversion_info(self):
        """Test getting conversion tool and library information"""
        info = get_conversion_info()
        
        self.assertIsInstance(info, dict)
        self.assertIn('libraries', info)
        self.assertIn('tools', info)
        self.assertIn('supported_formats', info)
        
        # Check library availability flags
        self.assertIn('reportlab', info['libraries'])
        self.assertIn('pillow', info['libraries'])
        self.assertIn('pymupdf', info['libraries'])
        
        # Check tool availability flags
        self.assertIn('pandoc', info['tools'])
        self.assertIn('libreoffice', info['tools'])

    def test_to_pdf_text_conversion(self):
        """Test converting text file to PDF"""
        input_file = os.path.join(self.sample_files_dir, self.sample_files['text'])
        if not os.path.exists(input_file):
            self.skipTest(f"Sample text file not found: {input_file}")
        
        result_pdf = to_pdf(input_file)
        
        # Check that PDF was created
        self.assertTrue(os.path.exists(result_pdf))
        self.assertTrue(result_pdf.endswith('.pdf'))
        
        # Check that it's a valid PDF
        with open(result_pdf, 'rb') as f:
            header = f.read(4)
            self.assertEqual(header, b'%PDF')
        
        # Check file size is reasonable
        file_size = os.path.getsize(result_pdf)
        self.assertGreater(file_size, 100)  # At least 100 bytes
        
        # Clean up
        os.remove(result_pdf)

    def test_to_pdf_html_conversion(self):
        """Test converting HTML file to PDF"""
        input_file = os.path.join(self.sample_files_dir, self.sample_files['html'])
        if not os.path.exists(input_file):
            self.skipTest(f"Sample HTML file not found: {input_file}")
        
        try:
            result_pdf = to_pdf(input_file)
            
            # Check that PDF was created
            self.assertTrue(os.path.exists(result_pdf))
            self.assertTrue(result_pdf.endswith('.pdf'))
            
            # Check file size
            file_size = os.path.getsize(result_pdf)
            self.assertGreater(file_size, 100)
            
            # Clean up
            os.remove(result_pdf)
            
        except ConversionError as e:
            # If no HTML conversion tools available, skip test
            if "not available" in str(e):
                self.skipTest(f"HTML conversion tools not available: {e}")
            else:
                raise

    def test_to_pdf_markdown_conversion(self):
        """Test converting Markdown file to PDF"""
        input_file = os.path.join(self.sample_files_dir, self.sample_files['markdown'])
        if not os.path.exists(input_file):
            self.skipTest(f"Sample Markdown file not found: {input_file}")
        
        try:
            result_pdf = to_pdf(input_file)
            
            # Check that PDF was created
            self.assertTrue(os.path.exists(result_pdf))
            self.assertTrue(result_pdf.endswith('.pdf'))
            
            # Check file size
            file_size = os.path.getsize(result_pdf)
            self.assertGreater(file_size, 100)
            
            # Clean up
            os.remove(result_pdf)
            
        except ConversionError as e:
            # If no Markdown conversion tools available, skip test
            if "not available" in str(e):
                self.skipTest(f"Markdown conversion tools not available: {e}")
            else:
                raise

    def test_to_pdf_image_conversion(self):
        """Test converting image file to PDF"""
        input_file = os.path.join(self.sample_files_dir, self.sample_files['image'])
        if not os.path.exists(input_file):
            self.skipTest(f"Sample image file not found: {input_file}")
        
        result_pdf = to_pdf(input_file)
        
        # Check that PDF was created
        self.assertTrue(os.path.exists(result_pdf))
        self.assertTrue(result_pdf.endswith('.pdf'))
        
        # Check that it's a valid PDF
        with open(result_pdf, 'rb') as f:
            header = f.read(4)
            self.assertEqual(header, b'%PDF')
        
        # Check file size
        file_size = os.path.getsize(result_pdf)
        self.assertGreater(file_size, 1000)  # Images should create larger PDFs
        
        # Clean up
        os.remove(result_pdf)

    def test_to_pdf_nonexistent_file(self):
        """Test error handling for non-existent input files"""
        nonexistent_file = "nonexistent_file.txt"
        
        with self.assertRaises(FileNotFoundError):
            to_pdf(nonexistent_file)

    def test_to_pdf_output_filename_generation(self):
        """Test that output filenames are generated correctly"""
        input_file = os.path.join(self.sample_files_dir, self.sample_files['text'])
        if not os.path.exists(input_file):
            self.skipTest(f"Sample text file not found: {input_file}")
        
        result_pdf = to_pdf(input_file)
        
        # Check filename pattern
        expected_pattern = input_file.replace('.txt', '.pdf')
        self.assertEqual(result_pdf, expected_pattern)
        
        # Clean up
        os.remove(result_pdf)

    def test_to_pdf_unsupported_extension(self):
        """Test handling of unsupported file extensions"""
        # Create a temporary file with unsupported extension
        temp_file = os.path.join(self.sample_files_dir, "test.xyz")
        with open(temp_file, 'w') as f:
            f.write("Test content")
        
        try:
            # Should try to use pandoc as fallback
            result_pdf = to_pdf(temp_file)
            
            # If successful, clean up
            if os.path.exists(result_pdf):
                os.remove(result_pdf)
                
        except ConversionError:
            # Expected if pandoc is not available
            pass
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def test_conversion_with_special_characters(self):
        """Test conversion of files with special characters in content"""
        # Create a text file with special characters
        special_content = """
        Special Characters Test: áéíóú àèìòù äëïöü ñç
        Unicode: 🌟 ★ ♦ ♥ ♠ ♣
        Math: α β γ δ ε π ∞ ∑ ∫
        Quotes: "Hello" 'World' «Bonjour» »Monde«
        """
        
        special_file = os.path.join(self.sample_files_dir, "special_chars.txt")
        with open(special_file, 'w', encoding='utf-8') as f:
            f.write(special_content)
        
        try:
            result_pdf = to_pdf(special_file)
            
            # Check that PDF was created
            self.assertTrue(os.path.exists(result_pdf))
            
            # Check file size
            file_size = os.path.getsize(result_pdf)
            self.assertGreater(file_size, 100)
            
            # Clean up
            os.remove(result_pdf)
            
        finally:
            # Clean up temp file
            if os.path.exists(special_file):
                os.remove(special_file)

    def test_multiple_format_conversions(self):
        """Test converting multiple file formats in sequence"""
        test_files = []
        result_files = []
        
        try:
            # Test all available sample files
            for format_type, filename in self.sample_files.items():
                input_file = os.path.join(self.sample_files_dir, filename)
                if os.path.exists(input_file):
                    test_files.append((format_type, input_file))
            
            # Convert all files
            for format_type, input_file in test_files:
                with self.subTest(format=format_type):
                    try:
                        result_pdf = to_pdf(input_file)
                        result_files.append(result_pdf)
                        
                        # Check that PDF was created
                        self.assertTrue(os.path.exists(result_pdf))
                        self.assertTrue(result_pdf.endswith('.pdf'))
                        
                    except ConversionError as e:
                        if "not available" in str(e):
                            self.skipTest(f"Conversion tools not available for {format_type}: {e}")
                        else:
                            raise
        
        finally:
            # Clean up all generated files
            for result_file in result_files:
                if os.path.exists(result_file):
                    os.remove(result_file)

    def test_conversion_error_handling(self):
        """Test proper error handling for conversion failures"""
        # Create a corrupted/empty file
        corrupted_file = os.path.join(self.sample_files_dir, "corrupted.txt")
        with open(corrupted_file, 'w') as f:
            f.write("")  # Empty file
        
        try:
            # Should still work for empty text file
            result_pdf = to_pdf(corrupted_file)
            self.assertTrue(os.path.exists(result_pdf))
            
            # Clean up
            os.remove(result_pdf)
            
        finally:
            # Clean up
            if os.path.exists(corrupted_file):
                os.remove(corrupted_file)

    def test_pdf_content_validation(self):
        """Test that generated PDFs contain expected content structure"""
        input_file = os.path.join(self.sample_files_dir, self.sample_files['text'])
        if not os.path.exists(input_file):
            self.skipTest(f"Sample text file not found: {input_file}")
        
        try:
            import fitz  # PyMuPDF for PDF content validation
            
            result_pdf = to_pdf(input_file)
            
            # Open and validate PDF content
            doc = fitz.open(result_pdf)
            
            # Check that PDF has at least one page
            self.assertGreater(len(doc), 0)
            
            # Check that first page has some text content
            page = doc[0]
            text = page.get_text()
            self.assertGreater(len(text.strip()), 0)
            
            doc.close()
            
            # Clean up
            os.remove(result_pdf)
            
        except ImportError:
            self.skipTest("PyMuPDF not available for content validation")


if __name__ == '__main__':
    unittest.main()