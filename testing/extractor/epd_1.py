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
        model_name="gemma3n",  # or "llama2" for Ollama, OpenAPI "gpt-3.5-turbo"
        temperature=0
    )

    # Initialize extractor
    extractor = FactExtractor(config)

    # Example document
    document = EPD_TEXT

    # Example extraction query
    query = ExtractionQuery(
        query="""
            Does the above state that the product has a Product-specific Type III EPD, Externally Reviewed (ISO 14025 and EN 15804)?
            Does the above state that the product has a Product-specific Type 3 EPD, Internally Reviewed? If it is Externally Reviewed then it cannot be  Internally Reviewed.
            Does the above state that the product has a Industry-wide Type 3 EPD?
            Additional instructions: It can only be one of these types, if information indicating one if the best match the other two are false.
            """,
        fields={
            "internal": "Answer with yes or no if it is Internally Reviewed",
            "external": "Answer with yes or no if it is Internally Reviewed",
            "industry": "Answer with yes or no if it is Industry-wide Type 3",
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
