from typing import Dict, Any, Optional, Union
from pydantic import BaseModel, Field, validator


class ExtractionQuery(BaseModel):
    """Input data structure for fact extraction queries."""
    query: str = Field(..., description="Query question for data extraction")
    fields: Dict[str, str] = Field(..., description="Dictionary mapping field names to descriptions")
    
    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()
    
    @validator('fields')
    def fields_not_empty(cls, v):
        if not v:
            raise ValueError('Fields dictionary cannot be empty')
        return v


class ExtractionResult(BaseModel):
    """Output data structure for extraction results."""
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    found: bool = Field(..., description="Whether the information was found in the document")
    explanation: str = Field(..., description="Explanation for the answer")
    extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Extracted field data")
    
    @validator('confidence')
    def validate_confidence(cls, v):
        return round(v, 3)  # Round to 3 decimal places


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""
    base_url: str = Field(default="https://api.openai.com/v1", description="Base URL for the API")
    api_key: str = Field(..., description="API key for authentication")
    model_name: str = Field(default="gpt-3.5-turbo", description="Model name to use")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="Temperature for generation")
    max_tokens: Optional[int] = Field(default=2000, description="Maximum tokens to generate")
    timeout: int = Field(default=60, description="Request timeout in seconds")
