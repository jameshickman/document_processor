# New feature: Select model per extraction prompt

## Model manager:

Between the `Extractors` and the `Service API Settings`, add
a new tab and interface to manage avaliable models. Implement
a CRUD interface for the user to manage a list of available 
model identifier strings to use with the inference API.

Add a table to the database to save the list of available models.

## Extractors

In the `Extractor Editor` add a drop-down to specify the model
to use, defaulting to the one sepcifid in the configuration.

The extraction runner needs to use the specified model,
and if unspecified, use the default from the configuration.