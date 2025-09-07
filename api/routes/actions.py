"""
End-points for the Actions Chains macro system

End point:
GET /
Return the action chain record names and IDs

POST /<id>
Post JSON to create or update a Chain, if ID is 0 creating a new record. Return the ID.

GET /<id>
Get the entire specification for the Chain.

DELETE /<id>
Remove a Chain

GET /run/<document_ID>/<Classifier_ID>
Run a Classifier against a document. Where a Classification score is high enough,
run the Action Chain against it. Return a status object with the results and reporting any
failures
"""