from string import Template


class PromptBuilder:
    """Handles prompt template construction and formatting."""
    
    TEMPLATE = """# Context:
$document_text

# Prompt:
$query_question

Provide a confidence for your answer on a scale between 0 and 1.
Provide an explanation for the answer. 
If the information relating to the question cannot be found, return 'found' as false, else true indicating that enough information found to answer the question.

Example JSON structure to return:
{
"confidence": <number>,
"found": true|false,
"explanation": "...",
$field_examples
}

Return ONLY the JSON object, no additional text."""
    
    def build_prompt(self, document_text: str, query: str, fields: dict[str, str]) -> str:
        """Build the complete prompt for the LLM."""
        # Generate field examples for the JSON structure
        field_examples = ',\n'.join([f'"{field}": "{description}"' for field, description in fields.items()])

        prompt = self.TEMPLATE.replace("$document_text", document_text)
        prompt = prompt.replace("$query", query)
        prompt = prompt.replace("$field_examples", field_examples)
        return prompt

