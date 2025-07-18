import logging

from lib.fact_extractor.fact_extractor import FactExtractor
from lib.fact_extractor.models import LLMConfig, ExtractionQuery
from testing.extractor.epd import EPD_TEXT

def main():
    """Example usage of the fact extractor."""
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Example configuration for OpenAI
    config = LLMConfig(
        base_url="http://localhost:11434/v1",  # for Ollama, OpenAPI "https://api.openai.com/v1"
        api_key="openai_api_key",
        model_name="gemma3n",  # or "llama2". "gemma3n" for Ollama, OpenAPI "gpt-3.5-turbo"
        temperature=0
    )

    # Initialize extractor
    extractor = FactExtractor(config)

    # Example document
    document = EPD_TEXT

    # Example extraction query
    query = ExtractionQuery(
        query="""
        Does the above state that the product have Life-cycle Assessment publicly available, critically reviewed, and ISO 14044?
        """,
        fields={
            "answer": "Answer with yes or no"
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
