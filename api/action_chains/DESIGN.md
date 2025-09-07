# Action Achain macro support

This is a basic macro support feature associated with a Document Classification.
When run, a document that clears the threshold defined for a classification the chan is run.
Each extractor is run to find information in the document. Then the list of action criteria, these consist of tests for
the extraction results chained together with AND and OR logic.

Where a criteria evalulates for an Action is true, load an implementation
derived from the action.Action class, pass it the data from the extractors
and custom fields stored in the action_chain_fields table.

## Test object

The results of the Extraction against the document are tested against a list of
criteria.

### Structure for each test in criteria:

- Operation: AND|OR
- Extractor ID
- Filed ID
- Test: ==, !=, <, >, contains

Tests are appropriate as per the result being a number or string.

The list of criteria are evaluated down the list, AND has a higher precedence than OR.

### Example Action Chain as JSON:

```json
{
  "name": "Action chain name",
  "classification": <ID_in_classifiers>,
  "threshold": <score_threshold>,
  "actions": [
        {
          "action_type": "implementation_class",
          "params": {
            "key": "value", ...
          },
          "criteria": [
            {
              "operation": "AND|OR",
              "extractor_id": <extractor_id>,
              "field_id": <field_id>,
              "test": "==|!=|>|<|contains"
            }, ...
          ]
      }, ...
  ]
}
```

# Run pprocess:

Where a Classifier classification for the document being processes
is above the threshold, run the extractors cited in the criteria list.
Collate the extracted dat together to pass to te action. Run the criteria
tests. If results are True, load the specified action_type and pass the
extractor data and the param dict.