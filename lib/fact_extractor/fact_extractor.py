import json
import logging
import os
import time
from datetime import datetime
from typing import Optional, Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

try:
    from langchain_community.llms import DeepInfra
    DEEPINFRA_AVAILABLE = True
except ImportError:
    DEEPINFRA_AVAILABLE = False
    DeepInfra = None

from lib.fact_extractor.document_chunker import DocumentChunker, CHUNK_SIZE
from lib.fact_extractor.models import LLMConfig, ExtractionResult, ExtractionQuery
from lib.fact_extractor.prompt_builder import PromptBuilder

# Import vector utilities for semantic search
try:
    from api.util.embedder import DocumentEmbedder
    EMBEDDER_AVAILABLE = True
except ImportError:
    EMBEDDER_AVAILABLE = False
    DocumentEmbedder = None
    logger = logging.getLogger(__name__)
    logger.debug("DocumentEmbedder not available, will use chunking fallback")

logger = logging.getLogger(__name__)


class FactExtractor:
    """Main class for extracting facts from documents using LLM services."""

    def __init__(
        self,
        config: LLMConfig,
        db_session: Optional[Session] = None,
        use_vector_search: bool = True
    ):
        """
        Initialize FactExtractor.

        Args:
            config: LLM configuration
            db_session: Optional database session for vector search
            use_vector_search: Whether to use vector search when available (default True)
        """
        self.config = config
        self.db_session = db_session
        self.use_vector_search = use_vector_search
        self.chunker = DocumentChunker()
        self.prompt_builder = PromptBuilder()
        self.llm = self._initialize_llm()
        self.prompt_log_file = os.environ.get('PROMPT_LOG')

        # Initialize vector embedder if available and requested
        self.embedder = None
        if use_vector_search and EMBEDDER_AVAILABLE and db_session is not None:
            try:
                self.embedder = DocumentEmbedder(
                    openai_api_key=os.getenv("OPENAI_API_KEY"),
                    openai_base_url=os.getenv("OPENAI_BASE_URL"),
                    chunk_size=500,
                    chunk_overlap=50
                )
                logger.info("Vector search enabled for fact extraction")
            except Exception as e:
                logger.warning(f"Failed to initialize vector embedder: {e}. Falling back to chunking.")
                self.embedder = None
        elif use_vector_search and not EMBEDDER_AVAILABLE:
            logger.info("Vector search requested but embedder not available. Using chunking fallback.")
    
    def _initialize_llm(self) -> Union[ChatOpenAI, "DeepInfra"]:
        """Initialize the LangChain LLM with the provided configuration."""
        if self.config.provider == "deepinfra":
            if not DEEPINFRA_AVAILABLE:
                logger.warning("DeepInfra not available, falling back to OpenAI-compatible API")
                # Fallback to ChatOpenAI with DeepInfra-like configuration
                return ChatOpenAI(
                    base_url="https://api.deepinfra.com/v1/openai",
                    api_key=self.config.api_key,
                    model=self.config.model_name,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    timeout=self.config.timeout
                )
            else:
                logger.info(f"Initializing DeepInfra LLM with model: {self.config.model_name}")
                llm = DeepInfra(
                    model_id=self.config.model_name,
                    deepinfra_api_token=self.config.api_key,
                )
                llm.model_kwargs = self.config.model_kwargs or {}
                return llm
        else:
            # Use ChatOpenAI for both OpenAI and Ollama providers
            logger.info(f"Initializing {self.config.provider} LLM with model: {self.config.model_name}")
            return ChatOpenAI(
                base_url=self.config.base_url,
                api_key=self.config.api_key,
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
    
    def _log_to_prompt_file(self, log_type: str, content: str, chunk_num: Union[int, str, None] = None) -> None:
        """Log prompts, responses, and errors to the PROMPT_LOG file if configured."""
        if not self.prompt_log_file:
            return

        try:
            timestamp = datetime.now().isoformat()
            chunk_info = f" ({chunk_num})" if chunk_num is not None else ""
            log_entry = f"\n{'='*80}\n"
            log_entry += f"[{timestamp}] {log_type.upper()}{chunk_info}\n"
            log_entry += f"{'='*80}\n"
            log_entry += f"{content}\n"

            with open(self.prompt_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write to prompt log file {self.prompt_log_file}: {e}")
    
    def _is_response_complete(self, response_text: str) -> bool:
        """Check if the response appears to be complete by looking for JSON closure."""
        if not response_text.strip():
            return False
        
        # Look for complete JSON structure
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')
        
        if json_start == -1 or json_end == -1:
            return False
        
        # Check if the JSON looks complete (has closing brace)
        # and appears to have the expected fields
        json_part = response_text[json_start:json_end+1]
        
        # Basic completeness checks
        required_indicators = ['confidence', 'found', 'explanation']
        has_required = all(field in json_part for field in required_indicators)
        
        return has_required and json_part.count('{') <= json_part.count('}')
    
    def _invoke_deepinfra_with_retry(self, prompt: str, chunk_num: Union[int, str], max_retries: int = 3) -> str:
        """
        Invoke DeepInfra with retry logic for handling partial responses.

        Args:
            prompt: The prompt to send
            chunk_num: Chunk identifier for logging (int or string)
            max_retries: Maximum number of retry attempts

        Returns:
            Complete response text
        """
        last_response = ""
        
        for attempt in range(max_retries):
            try:
                logger.debug(f"DeepInfra attempt {attempt + 1}/{max_retries} for chunk {chunk_num}")
                
                # Adjust parameters for better completion on retries
                if attempt > 0:
                    # Increase max_tokens and reduce temperature for better completion
                    original_max_tokens = self.llm.model_kwargs.get('max_new_tokens', 250)
                    original_temp = self.llm.model_kwargs.get('temperature', 0.0)
                    
                    # Increase tokens and make more deterministic
                    self.llm.model_kwargs['max_new_tokens'] = min(original_max_tokens * 2, 4096)
                    self.llm.model_kwargs['temperature'] = max(original_temp * 0.5, 0.0)
                    
                    # Add explicit instruction for completion
                    enhanced_prompt = f"{prompt}\n\nIMPORTANT: Please provide a complete response with fully closed JSON. Do not truncate the response."
                    response_text = self.llm.invoke(enhanced_prompt)
                    
                    # Restore original parameters
                    self.llm.model_kwargs['max_new_tokens'] = original_max_tokens
                    self.llm.model_kwargs['temperature'] = original_temp
                else:
                    response_text = self.llm.invoke(prompt)
                
                # Log the attempt
                self._log_to_prompt_file(
                    "deepinfra_attempt", 
                    f"Attempt {attempt + 1}/{max_retries}\nResponse length: {len(response_text)}\nResponse: {response_text}",
                    chunk_num
                )
                
                # Check if response is complete
                if self._is_response_complete(response_text):
                    if attempt > 0:
                        logger.info(f"DeepInfra completed successfully on attempt {attempt + 1} for chunk {chunk_num}")
                    return response_text
                
                # Store the response for potential use if all retries fail
                if len(response_text) > len(last_response):
                    last_response = response_text
                
                logger.warning(f"DeepInfra response appears incomplete on attempt {attempt + 1} for chunk {chunk_num} (length: {len(response_text)})")
                
                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                
            except Exception as e:
                error_msg = f"DeepInfra attempt {attempt + 1} failed for chunk {chunk_num}: {e}"
                logger.error(error_msg)
                self._log_to_prompt_file("deepinfra_error", f"{error_msg}\nLast response: {last_response}", chunk_num)
                
                if attempt == max_retries - 1:
                    # On final attempt failure, return the best response we have
                    if last_response:
                        logger.warning(f"Using partial response from DeepInfra for chunk {chunk_num}")
                        return last_response
                    raise e
                
                # Wait before retry
                wait_time = 2 ** attempt
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        # If we get here, all retries failed but we have a partial response
        if last_response:
            logger.warning(f"DeepInfra all retries failed for chunk {chunk_num}, using best partial response")
            return last_response
        
        # No response at all
        raise Exception(f"DeepInfra failed to generate any response after {max_retries} attempts")
    
    def _parse_llm_response(self, response_text: str, fields: dict[str, str]) -> Optional[ExtractionResult]:
        """Parse the LLM response and extract JSON data."""
        try:
            # Try to find JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                error_msg = "No JSON found in LLM response"
                logger.error(error_msg)
                self._log_to_prompt_file("json_parse_error", f"{error_msg}\nResponse text: {response_text}")
                return None
            
            json_str = response_text[json_start:json_end]
            parsed_data = json.loads(json_str)
            
            # Extract required fields
            confidence = parsed_data.get('confidence', 0.0)
            found = parsed_data.get('found', False)
            explanation = parsed_data.get('explanation', '')
            
            # Extract field data
            extracted_data = {}
            for field in fields.keys():
                if "fields" in parsed_data:
                    extracted_data[field] = parsed_data.get("fields", {}).get(field)
                elif field in parsed_data:
                    extracted_data[field] = parsed_data[field]
            
            return ExtractionResult(
                confidence=confidence,
                found=found,
                explanation=explanation,
                extracted_data=extracted_data
            )
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON from LLM response: {e}"
            logger.error(error_msg)
            
            # Create detailed error log with exact parsing failure reason
            detailed_error = f"{error_msg}\n"
            detailed_error += f"JSON Parse Error Details:\n"
            detailed_error += f"- Error Type: {type(e).__name__}\n"
            detailed_error += f"- Error Message: {str(e)}\n"
            detailed_error += f"- Error Position: {getattr(e, 'pos', 'Unknown')}\n"
            detailed_error += f"- Error Line Number: {getattr(e, 'lineno', 'Unknown')}\n"
            detailed_error += f"- Error Column: {getattr(e, 'colno', 'Unknown')}\n"
            detailed_error += f"JSON string attempted to parse ({len(json_str) if 'json_str' in locals() else 0} characters):\n"
            detailed_error += f"{'='*40}\n"
            detailed_error += f"{json_str if 'json_str' in locals() else 'N/A'}\n"
            detailed_error += f"{'='*40}\n"
            detailed_error += f"Full response text ({len(response_text)} characters):\n"
            detailed_error += f"{'='*40}\n"
            detailed_error += f"{response_text}\n"
            detailed_error += f"{'='*40}"
            
            self._log_to_prompt_file("json_parse_error", detailed_error)
            return None
        except Exception as e:
            error_msg = f"Error parsing LLM response: {e}"
            logger.error(error_msg)
            
            # Create detailed error log for non-JSON parsing errors
            detailed_error = f"{error_msg}\n"
            detailed_error += f"General Error Details:\n"
            detailed_error += f"- Error Type: {type(e).__name__}\n"
            detailed_error += f"- Error Message: {str(e)}\n"
            detailed_error += f"Response text ({len(response_text)} characters):\n"
            detailed_error += f"{'='*40}\n"
            detailed_error += f"{response_text}\n"
            detailed_error += f"{'='*40}"
            
            self._log_to_prompt_file("json_parse_error", detailed_error)
            return None
    
    def extract_facts(
        self,
        document_text: str,
        extraction_query: ExtractionQuery,
        document_id: Optional[int] = None
    ) -> Optional[ExtractionResult]:
        """
        Main method to extract facts from a document.

        Uses vector search when available for more efficient context retrieval,
        falls back to chunking approach if vector search is unavailable.

        Args:
            document_text: The text content to analyze
            extraction_query: The query containing question and fields to extract
            document_id: Optional document ID for vector search

        Returns:
            ExtractionResult if successful, None if extraction fails
        """
        logger.info(f"Starting fact extraction with query: {extraction_query.query}")

        # Try vector search approach first if available
        if self.embedder and self.db_session and document_id:
            try:
                logger.info("Using vector search for context retrieval")
                relevant_context = self.embedder.get_relevant_context(
                    db=self.db_session,
                    query=extraction_query.query,
                    document_id=document_id,
                    max_tokens=2048
                )

                if relevant_context and relevant_context.strip():
                    logger.info(f"Retrieved relevant context ({len(relevant_context.split())} words)")
                    # Process the relevant context as a single chunk
                    result = self._process_text_chunk(
                        text=relevant_context,
                        extraction_query=extraction_query,
                        chunk_label="vector_search"
                    )
                    if result:
                        return result
                else:
                    logger.warning("Vector search returned empty context, falling back to chunking")
            except Exception as e:
                logger.warning(f"Vector search failed: {e}. Falling back to chunking approach.")

        # Fallback to traditional chunking approach
        logger.info("Using traditional chunking approach")
        return self._extract_with_chunking(document_text, extraction_query)

    def _process_text_chunk(
        self,
        text: str,
        extraction_query: ExtractionQuery,
        chunk_label: str = "chunk"
    ) -> Optional[ExtractionResult]:
        """
        Process a single text chunk with the LLM.

        Args:
            text: Text to process
            extraction_query: Extraction query
            chunk_label: Label for logging (e.g., "chunk_1", "vector_search")

        Returns:
            ExtractionResult if successful and found, None otherwise
        """
        # Build prompt
        prompt = self.prompt_builder.build_prompt(
            text,
            extraction_query.query,
            extraction_query.fields
        )

        try:
            # Log the prompt if PROMPT_LOG is configured
            self._log_to_prompt_file("prompt", prompt, chunk_label)

            # Send to LLM - handle different provider response formats
            if self.config.provider == "deepinfra" and DEEPINFRA_AVAILABLE:
                logger.info(f"Sending prompt to DeepInfra ({chunk_label})")
                response_text = self._invoke_deepinfra_with_retry(prompt, chunk_label)
                logger.info(f"DeepInfra response received ({len(response_text)} characters)")
            else:
                # Use ChatOpenAI interface for OpenAI, Ollama, and DeepInfra fallback
                message = HumanMessage(content=prompt)
                response = self.llm.invoke([message])
                response_text = response.content

            # Log the response if PROMPT_LOG is configured
            self._log_to_prompt_file("response", response_text, chunk_label)

            # Parse response
            result = self._parse_llm_response(response_text, extraction_query.fields)

            if result is None:
                logger.warning(f"Failed to parse response for {chunk_label}")
                return None

            # Return result if information was found
            if result.found:
                logger.info(f"Information found in {chunk_label}")
                return result
            else:
                logger.info(f"Information not found in {chunk_label}")
                return None

        except Exception as e:
            logger.error(f"Error processing {chunk_label}: {e}")
            return None

    def _extract_with_chunking(
        self,
        document_text: str,
        extraction_query: ExtractionQuery
    ) -> ExtractionResult:
        """
        Traditional chunking-based extraction approach.
        Used as fallback when vector search is unavailable.

        Args:
            document_text: Full document text
            extraction_query: Extraction query

        Returns:
            ExtractionResult
        """
        # Step 1: Get word count and determine if chunking is needed
        word_count = self.chunker.count_words(document_text)
        logger.info(f"Document word count: {word_count}")

        # Step 2: Split document if necessary
        if word_count > CHUNK_SIZE:
            chunks = self.chunker.chunk_document(document_text)
            logger.info(f"Document split into {len(chunks)} chunks")
        else:
            chunks = [document_text]
            logger.info("Document processed as single chunk")

        # Step 3: Process each chunk
        for i, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {i}/{len(chunks)}")

            result = self._process_text_chunk(
                text=chunk,
                extraction_query=extraction_query,
                chunk_label=f"chunk_{i}"
            )

            if result and result.found:
                return result

        # If no chunks yielded results, return a default "not found" result
        logger.info("Information not found in any chunk")
        return ExtractionResult(
            confidence=0.0,
            found=False,
            explanation="The requested information could not be found in the provided document.",
            extracted_data={}
        )
