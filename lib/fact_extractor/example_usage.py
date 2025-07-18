import logging

from lib.fact_extractor.fact_extractor import FactExtractor
from lib.fact_extractor.models import LLMConfig, ExtractionQuery


def main():
    """Example usage of the fact extractor."""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Example configuration for OpenAI
    config = LLMConfig(
        base_url="http://localhost:11434/v1",  # for Ollama, OpenAPI "https://api.openai.com/v1"
        api_key="openai_api_key",
        model_name="gemma3n",  # or "llama2" for Ollama, OpenAPI "gpt-3.5-turbo"
        temperature=0.1
    )
    
    # Initialize extractor
    extractor = FactExtractor(config)
    
    # Example document
    document = """
    John Smith is a 35-year-old software engineer who works at Tech Corp. 
    He graduated from MIT in 2010 with a degree in Computer Science. 
    John has been working on artificial intelligence projects for the past 5 years.
    His current salary is $120,000 per year. He lives in San Francisco, California.
    """
    
    # Example extraction query
    query = ExtractionQuery(
        query="What is John Smith's professional background and personal details?",
        fields={
            "name": "Full name of the person",
            "age": "Age in years",
            "occupation": "Job title or profession",
            "company": "Name of the company they work for",
            "education": "Educational background",
            "salary": "Annual salary if mentioned",
            "location": "City and state where they live"
        }
    )
    
    # Extract facts
    result = extractor.extract_facts(document, query)
    
    if result:
        print("Extraction Result:")
        print(f"Found: {result.found}")
        print(f"Confidence: {result.confidence}")
        print(f"Explanation: {result.explanation}")
        print("Extracted Data:")
        for field, value in result.extracted_data.items():
            print(f"  {field}: {value}")
    else:
        print("Extraction failed")


if __name__ == "__main__":
    main()
