import json
import logging
import os
from datetime import datetime
from typing import Optional, Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

try:
    from langchain_community.llms import DeepInfra
    DEEPINFRA_AVAILABLE = True
except ImportError:
    DEEPINFRA_AVAILABLE = False
    DeepInfra = None

from lib.fact_extractor.document_chunker import DocumentChunker,CHUNK_SIZE
from lib.fact_extractor.models import LLMConfig, ExtractionResult, ExtractionQuery
from lib.fact_extractor.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class FactExtractor:
    """Main class for extracting facts from documents using LLM services."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.chunker = DocumentChunker()
        self.prompt_builder = PromptBuilder()
        self.llm = self._initialize_llm()
        self.prompt_log_file = os.environ.get('PROMPT_LOG')
    
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
    
    def _log_to_prompt_file(self, log_type: str, content: str, chunk_num: int = None) -> None:
        """Log prompts, responses, and errors to the PROMPT_LOG file if configured."""
        if not self.prompt_log_file:
            return
        
        try:
            timestamp = datetime.now().isoformat()
            chunk_info = f" (chunk {chunk_num})" if chunk_num is not None else ""
            log_entry = f"\n{'='*80}\n"
            log_entry += f"[{timestamp}] {log_type.upper()}{chunk_info}\n"
            log_entry += f"{'='*80}\n"
            log_entry += f"{content}\n"
            
            with open(self.prompt_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write to prompt log file {self.prompt_log_file}: {e}")
    
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
    
    def extract_facts(self, document_text: str, extraction_query: ExtractionQuery) -> Optional[ExtractionResult]:
        """
        Main method to extract facts from a document.
        
        Args:
            document_text: The text content to analyze
            extraction_query: The query containing question and fields to extract
            
        Returns:
            ExtractionResult if successful, None if extraction fails
        """
        logger.info(f"Starting fact extraction with query: {extraction_query.query}")
        
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

            # Build prompt
            prompt = self.prompt_builder.build_prompt(
                chunk,
                extraction_query.query,
                extraction_query.fields
            )

            try:
                # Log the prompt if PROMPT_LOG is configured
                self._log_to_prompt_file("prompt", prompt, i)
                
                # Send to LLM - handle different provider response formats
                if self.config.provider == "deepinfra" and DEEPINFRA_AVAILABLE:
                    logger.info(f"Extracting DeepInfra DeepInfra facts: {prompt}")
                    response_text = self.llm.invoke(prompt)
                    logger.info(f"DeepInfra DeepInfra facts extracted: {response_text}")
                else:
                    # Use ChatOpenAI interface for OpenAI, Ollama, and DeepInfra fallback
                    message = HumanMessage(content=prompt)
                    response = self.llm.invoke([message])
                    response_text = response.content
                
                # Log the response if PROMPT_LOG is configured
                self._log_to_prompt_file("response", response_text, i)
                
                # Step 4: Parse response
                result = self._parse_llm_response(response_text, extraction_query.fields)
                
                if result is None:
                    logger.warning(f"Failed to parse response for chunk {i}")
                    continue
                
                # Step 5: Check if information was found
                if result.found:
                    logger.info(f"Information found in chunk {i}")
                    return result
                else:
                    logger.info(f"Information not found in chunk {i}, continuing to next chunk")
            
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}")
                continue
        
        # If no chunks yielded results, return a default "not found" result
        logger.info("Information not found in any chunk")
        return ExtractionResult(
            confidence=0.0,
            found=False,
            explanation="The requested information could not be found in the provided document.",
            extracted_data={}
        )
