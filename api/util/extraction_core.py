"""
Core extraction utilities shared between routes and background processes.
Consolidates duplicate code for extractor execution and PDF markup operations.
"""
import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from lib.fact_extractor.fact_extractor import FactExtractor
from lib.fact_extractor.models import ExtractionQuery, ExtractionResult


@dataclass
class ExtractorExecutionResult:
    """Result of running an extractor with optional PDF markup."""
    extraction_result: ExtractionResult
    marked_pdf_path: Optional[str] = None
    marked_pdf_available: bool = False


def execute_extractor(
    document_text: str,
    extractor_prompt: str,
    extractor_fields: Dict[str, str],
    llm_config: Any
) -> ExtractionResult:
    """Execute the fact extractor with given parameters."""
    fact_extractor = FactExtractor(llm_config)
    extraction_query = ExtractionQuery(
        query=extractor_prompt,
        fields=extractor_fields,
    )
    return fact_extractor.extract_facts(document_text, extraction_query)


def collect_citations_from_result(extraction_result: ExtractionResult) -> List[str]:
    """Collect all citations from extraction result data."""
    all_citations = []
    
    if not (extraction_result.found and extraction_result.extracted_data):
        return all_citations
    
    for field_name, field_data in extraction_result.extracted_data.items():
        # Add field data if it's a string (direct field value)
        if isinstance(field_data, str):
            all_citations.append(field_data)
        
        # Check for citations within field data if it's a dictionary
        if isinstance(field_data, dict) and 'citation' in field_data:
            citations = field_data['citation']
            if isinstance(citations, list):
                all_citations.extend(citations)
            elif isinstance(citations, str):
                all_citations.append(citations)
    
    # Remove empty citations and duplicates, ensure all items are strings
    return list(set([c for c in all_citations if isinstance(c, str) and c and c.strip()]))


def create_marked_pdf(
    document_file_path: str,
    citations: List[str],
    extractor_id: int,
    use_logging: bool = True
) -> Optional[str]:
    """Create a marked-up PDF with highlighted citations."""
    if not citations:
        return None
    
    try:
        from api.to_pdf.converter import to_pdf, ConversionError
        from api.pdf_markup.highlight_pdf import highlight_pdf
        
        # Determine source PDF path
        source_pdf_path = document_file_path
        
        # If the original file is not a PDF, convert it first
        if not source_pdf_path.lower().endswith('.pdf'):
            try:
                source_pdf_path = to_pdf(document_file_path)
            except ConversionError as e:
                if use_logging:
                    logging.warning(f"Could not convert {document_file_path} to PDF: {e}")
                else:
                    print(f"Warning: Could not convert {document_file_path} to PDF: {e}")
                return None
        
        # Create marked-up PDF with citations highlighted
        if source_pdf_path and os.path.exists(source_pdf_path):
            try:
                marked_pdf_path = highlight_pdf(
                    input_file=source_pdf_path,
                    strings=citations,
                    extractor_id=extractor_id
                )
                if use_logging:
                    logging.info(f"Created marked-up PDF: {marked_pdf_path}")
                else:
                    print(f"Created marked-up PDF: {marked_pdf_path}")
                return marked_pdf_path
            except Exception as e:
                if use_logging:
                    logging.error(f"Could not create marked-up PDF: {e}")
                else:
                    print(f"Warning: Could not create marked-up PDF: {e}")
                return None
    
    except Exception as e:
        if use_logging:
            logging.error(f"Error during PDF markup process: {e}")
        else:
            print(f"Warning: Error during PDF markup process: {e}")
        return None


def run_extractor_with_markup(
    document_text: str,
    document_file_path: str,
    extractor_prompt: str,
    extractor_fields: Dict[str, str],
    extractor_id: int,
    llm_config: Any,
    use_logging: bool = True
) -> ExtractorExecutionResult:
    """
    Run extractor and create marked-up PDF if citations are found.
    
    Args:
        document_text: The text content to extract from
        document_file_path: Path to the original document file
        extractor_prompt: The extraction prompt
        extractor_fields: Dictionary of field names to descriptions
        extractor_id: ID of the extractor for file naming
        llm_config: LLM configuration object
        use_logging: Whether to use logging module (True) or print statements (False)
        
    Returns:
        ExtractorExecutionResult containing extraction result and PDF markup info
    """
    # Execute the extractor
    extraction_result = execute_extractor(
        document_text=document_text,
        extractor_prompt=extractor_prompt,
        extractor_fields=extractor_fields,
        llm_config=llm_config
    )
    
    # Initialize result
    result = ExtractorExecutionResult(
        extraction_result=extraction_result,
        marked_pdf_path=None,
        marked_pdf_available=False
    )
    
    # Create marked-up PDF if extraction was successful and citations exist
    if extraction_result.found and extraction_result.extracted_data:
        citations = collect_citations_from_result(extraction_result)
        
        if citations:
            marked_pdf_path = create_marked_pdf(
                document_file_path=document_file_path,
                citations=citations,
                extractor_id=extractor_id,
                use_logging=use_logging
            )
            
            if marked_pdf_path:
                result.marked_pdf_path = marked_pdf_path
                result.marked_pdf_available = True
    
    return result