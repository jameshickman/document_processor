# Extractor Editor and tester

AI based fact extractor from document text.

Implement as a Custom-element in extractor_editor.js.

## Uses the API endpoints:

### List Extractor configurations:
GET:/extractors
Example return values:
```json
[
    {
        "id": 1,
        "name": "EPD Type"
    }
]
```

### Retrieve one Extractor:
GET:/extractors/{extractor_id}
Example return value:
```json
{
    "name": "EPD Type",
    "id": 1,
    "prompt": "Does the above state that the product is Product-specific Type III EPD, Externally Reviewed (ISO 14025 and EN 15804)? Does the above state that the product is Product-specific Type 3 EPD, Internally Reviewed? Does the above state that the product is an Industry-wide Type 3 EPD? Additional instructions: It can only be one of these types, if information indicating one being the best match the other two are false. Only one field can be yes, others must be no.",
    "fields": [
        {
            "name": "internal",
            "description": "Answer with yes or no for Internally Reviewed"
        },
        {
            "name": "external",
            "description": "Answer with yes or no for Externally Reviewed"
        },
        {
            "name": "industry",
            "description": "Answer with yes or no for Industry-wide Type 3"
        }
    ]
}

```

### Crate and update
If the ID is 0 a new record created, otherwise update a record.
POST:/extractors/{extractor_id}
Example payload:
```json
{
  "name": "EPD Type",
  "prompt": "Does the above state that the product is Product-specific Type III EPD, Externally Reviewed (ISO 14025 and EN 15804)? Does the above state that the product is Product-specific Type 3 EPD, Internally Reviewed? Does the above state that the product is an Industry-wide Type 3 EPD? Additional instructions: It can only be one of these types, if information indicating one being the best match the other two are false. Only one field can be yes, others must be no.",
  "fields": [
    {
      "name": "internal",
      "description": "Answer with yes or no for Internally Reviewed"
    },
    {
      "name": "external",
      "description": "Answer with yes or no for Externally Reviewed"
    },
    {
      "name": "industry",
      "description": "Answer with yes or no for Industry-wide Type 3"
    }
  ]
}
```

Return value:
```json
{
  "id": 123
}
```

### Run an Extractor:
GET:/extractors/run/{extractor_id}/{document_id}
Return values:
```json
{
    "id": 1,
    "document_id": 1,
    "result": {
        "confidence": 1.0,
        "found": true,
        "explanation": "The form asks specifically about 'Product-specific Type III EPD - Products with third-party certification (Type III), including external verification, in which the manufacturer is explicitly recognized as the participant by the program operator.' This directly addresses the question about an externally reviewed Type III EPD. It also asks about 'Product-specific Type III EPD - Products with third-party certification (Type III), including external verification and external critical review in which the manufacturer is explicitly recognized as the participant by the program operator', which is a more stringent version of the above. The form does not ask about an Industry-wide Type 3 EPD.",
        "extracted_data": {
            "internal": "no",
            "external": "yes",
            "industry": "no"
        }
    }
}

```

### Retrieve the list of selected files:
See the JSUM based implementation in classifier_editor.js

## UI/UX design:

Three columns of functionality.

First to the left, list of Extractor records. Below the list is a button to create new, and a button to rename the selected record.

The second column is an editor for the selected Extractor record. The top fields is a text area to edit the prompt. Below that is a liwt for the Fields with full CRUD operations. At the bottom are buttons to add a new Fields and save the Extractor.

The third column is the testing area, button at top to run the Extractor against the selected files. Review the implementation in classifier_editor.js.