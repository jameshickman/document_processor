import json
import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

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
    
    def _initialize_llm(self) -> ChatOpenAI:
        """Initialize the LangChain LLM with the provided configuration."""
        return ChatOpenAI(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            model=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            timeout=self.config.timeout
        )
    
    def _parse_llm_response(self, response_text: str, fields: dict[str, str]) -> Optional[ExtractionResult]:
        """Parse the LLM response and extract JSON data."""
        try:
            # Try to find JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.error("No JSON found in LLM response")
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
                if field in parsed_data:
                    extracted_data[field] = parsed_data[field]
            
            return ExtractionResult(
                confidence=confidence,
                found=found,
                explanation=explanation,
                extracted_data=extracted_data
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
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
                # Send to LLM
                message = HumanMessage(content=prompt)
                response = self.llm.invoke([message])
                response_text = response.content
                
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
