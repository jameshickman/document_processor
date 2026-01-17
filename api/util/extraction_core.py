"""
Core extraction utilities shared between routes and background processes.
Consolidates duplicate code for extractor execution and PDF markup operations.
"""
import os
import logging
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session

from lib.fact_extractor.fact_extractor import FactExtractor
from lib.fact_extractor.models import ExtractionQuery, ExtractionResult
from api.util.files_abstraction import get_filesystem
from api.services.usage_tracker import UsageTracker


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
    llm_config: Any,
    db: Optional[Session] = None,
    document_id: Optional[int] = None,
    use_vector_search: bool = True
) -> ExtractionResult:
    """
    Execute the fact extractor with given parameters.

    Args:
        document_text: The text content to extract from
        extractor_prompt: The extraction prompt/query
        extractor_fields: Dictionary of field names to descriptions
        llm_config: LLM configuration object
        db: Optional database session for vector search
        document_id: Optional document ID for vector search
        use_vector_search: Whether to use vector search (default True)

    Returns:
        ExtractionResult containing extracted information
    """
    fact_extractor = FactExtractor(
        config=llm_config,
        db_session=db,
        use_vector_search=use_vector_search
    )
    extraction_query = ExtractionQuery(
        query=extractor_prompt,
        fields=extractor_fields,
    )
    return fact_extractor.extract_facts(
        document_text,
        extraction_query,
        document_id=document_id
    )


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
        fs = get_filesystem()
        if source_pdf_path and fs.exists(source_pdf_path):
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
    use_logging: bool = True,
    db: Optional[Session] = None,
    document_id: Optional[int] = None,
    use_vector_search: bool = True,
    llm_model_id: Optional[int] = None,
    account_id: Optional[int] = None,
    source_type: str = 'workbench',
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None
) -> ExtractorExecutionResult:
    """
    Run extractor and create marked-up PDF if citations are found.

    Args:
        document_text: The text content to extract from
        document_file_path: Path to the original document file
        extractor_prompt: The extraction prompt
        extractor_fields: Dictionary of field names to descriptions
        extractor_id: ID of the extractor for file naming
        llm_config: LLM configuration object (global default)
        use_logging: Whether to use logging module (True) or print statements (False)
        db: Optional database session for vector search
        document_id: Optional document ID for vector search
        use_vector_search: Whether to use vector search (default True)
        llm_model_id: Optional LLM model ID to override global config
        account_id: Account ID for usage tracking
        source_type: Source type for usage tracking ('workbench' or 'api')
        user_agent: User agent string for usage tracking
        ip_address: IP address for usage tracking

    Returns:
        ExtractorExecutionResult containing extraction result and PDF markup info
    """
    start_time = time.time()

    # Override config if model_id provided
    if llm_model_id and db:
        from api.models import LLMModel
        from api.util.llm_config import build_llm_config_from_db_model, get_api_key_for_provider

        db_model = db.query(LLMModel).filter(LLMModel.id == llm_model_id).first()
        if db_model:
            api_key = get_api_key_for_provider(db_model.provider)
            if api_key:
                llm_config = build_llm_config_from_db_model(db_model, api_key)
                if use_logging:
                    logging.info(f"Using custom LLM model: {db_model.name} ({db_model.provider}/{db_model.model_identifier})")
                else:
                    print(f"Using custom LLM model: {db_model.name} ({db_model.provider}/{db_model.model_identifier})")
            else:
                if use_logging:
                    logging.warning(f"API key not found for provider {db_model.provider}, falling back to global config")
                else:
                    print(f"Warning: API key not found for provider {db_model.provider}, falling back to global config")
        else:
            if use_logging:
                logging.warning(f"LLM model with ID {llm_model_id} not found, falling back to global config")
            else:
                print(f"Warning: LLM model with ID {llm_model_id} not found, falling back to global config")

    try:
        # Execute the extractor
        extraction_result = execute_extractor(
            document_text=document_text,
            extractor_prompt=extractor_prompt,
            extractor_fields=extractor_fields,
            llm_config=llm_config,
            db=db,
            document_id=document_id,
            use_vector_search=use_vector_search
        )

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

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

        # Log successful extraction if account_id is provided
        if account_id and db:
            try:
                from api.services.usage_tracker import UsageTracker
                tracker = UsageTracker(db)
                tracker.log_extraction_sync(
                    account_id=account_id,
                    document_id=document_id,
                    extractor_id=extractor_id,
                    llm_model_id=llm_model_id,
                    provider=getattr(llm_config, 'provider', None),
                    model_name=getattr(llm_config, 'model_name', None),
                    input_tokens=getattr(extraction_result, 'input_tokens', None),
                    output_tokens=getattr(extraction_result, 'output_tokens', None),
                    duration_ms=duration_ms,
                    status='success',
                    source_type=source_type,
                    user_agent=user_agent,
                    ip_address=ip_address
                )
            except Exception as e:
                # Log the error but don't crash the main operation
                import logging
                logging.error(f"Failed to log extraction: {str(e)}")

        return result

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        # Log failed extraction if account_id is provided
        if account_id and db:
            try:
                from api.services.usage_tracker import UsageTracker
                tracker = UsageTracker(db)
                tracker.log_extraction_sync(
                    account_id=account_id,
                    document_id=document_id,
                    extractor_id=extractor_id,
                    duration_ms=duration_ms,
                    status='failure',
                    error_message=str(e),
                    source_type=source_type,
                    user_agent=user_agent,
                    ip_address=ip_address
                )
            except Exception as e_log:
                # Log the error but don't crash the main operation
                import logging
                logging.error(f"Failed to log extraction error: {str(e_log)}")

        raise