import json


class PromptBuilder:
    """Handles prompt template construction and formatting."""
    
    TEMPLATE = """# Context:
$document_text

# Prompt:
$query_question

Provide a confidence for your answer on a scale between 0 and 1.

Provide an explanation for the answer. Specifically quote text from the document supporting the explanation.
Watch out for non-text characters indicating a checkbox in close proximity to text that contributes to the answer.
There may be cases where text that would be an affirmative answer is next to a character that indicates an unchecked box,
hence a negative answer.  

If the information relating to the question cannot be found,
return 'found' as false, else true indicating that enough information found to answer the question.

For each field, return an object with the property 'value' for the extracted value.

A property for 'citation' must contain a list of exact verbatim quotes from the source document
that the value was extracted from or the answer based off of. This is not an explanation, it is the exact text.
Do not add any extra characters to the  citation, do not add an ellipsis. Each citation needs to be a 
list item in the output JSON.

Where field values are complex data, use JSON format and don't wrap in a string.
Simple data is text, number, or boolean so encode those normally.
You must provide an answer to every field defined below, if unknown return "unknown" for the value.

Example JSON structure to return:
{
"confidence": <number>,
"found": true|false,
"explanation": "...",
$field_examples
}
You must use the same field names as in the example JSON structure.

Return ONLY the JSON object, no additional text.
Return only ONE JSON block, no duplicate JSON blocks.
Be very careful with data encoding, make sure no stray double quotes are in strings, and make sure string
delimiters are one double quote character. 
"""
    
    def build_prompt(self, document_text: str, query: str, fields: dict[str, str]) -> str:
        """Build the complete prompt for the LLM."""
        # Generate field examples for the JSON structure
        field_examples = {}
        for field_name in fields:
            field_examples[field_name] = {
                'value': fields[field_name],
                'citation': ['citation 1', 'citation 2', ]
            }

        prompt = self.TEMPLATE.replace("$document_text", document_text)
        prompt = prompt.replace("$query", query)
        prompt = prompt.replace("$field_examples", json.dumps(field_examples))
        return prompt

