# Classifier Editor 

Editor widget using LitJS, and the local libraries in lib.

For the layout of the widget, see classifier_editor.svg

REST API described at: https://docprocesor-smolminds.ngrok.io/docs

You may call the API as needed at https://docprocesor-smolminds.ngrok.io

## Specification

Loads the list of Classifier Sets from GET:/classifiers/
And saves to POST:/classifiers/{classifiers_id} where the ID is 0
when creating a new classifier set. CRUD interface needed to edit Classifier Sets.

Within each Classifier Set is a list of Classifiers. CRUD interface needed to manage Classifiers.

Within each Classifier is a list of Terms. CRUD interface needed to manage Terms.

The "Run against Files" button needs to communicate with the widget provided in files_list.js.
The CSS selector for the files-list widget is "[jsum='files_list']"
Use the JSUM multicall() to retrieve the IDs of selected files
via public method get_selected_files(). The call the endpoint GET:/classifiers/run/{classifier_set_id}/{document_id}

## Below are example payloads for the end-points:

/classifiers/1
```
{
    "id": 1,
    "name": "LEED Document Type",
    "classifiers": [
        {
            "id": 1,
            "name": "Environmental Product Declaration",
            "terms": [
                {
                    "term": "Type III EPD",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Type 3 EPD",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "ISO 14025",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "EN 15804",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Externally Reviewed",
                    "distance": 1,
                    "weight": 0.5
                },
                {
                    "term": "Internally Reviewed",
                    "distance": 1,
                    "weight": 0.5
                },
                {
                    "term": "Lifecycle Assessment",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Life-cycle Assessment",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Life cycle Assessment",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "ISO 14044",
                    "distance": 1,
                    "weight": 1.0
                }
            ]
        },
        {
            "id": 2,
            "name": "Embodied Carbon/LCA Optimization",
            "terms": [
                {
                    "term": "Embodied Carbon",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "LCA Action Plan",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Reduction ? Embodied Carbon",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "reduction ? GWP",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Third party verified",
                    "distance": 1,
                    "weight": 0.5
                }
            ]
        },
        {
            "id": 3,
            "name": "Responsible Sourcing of Raw Materials",
            "terms": [
                {
                    "term": "Reused ? ? material",
                    "distance": 1,
                    "weight": 0.5
                },
                {
                    "term": "reused material",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "salvaged material",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "salvaged ? ? material",
                    "distance": 1,
                    "weight": 0.5
                },
                {
                    "term": "Post-consumer Recycled",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Post consumer Recycled",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Pre-consumer Recycled",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Pre consumer Recycled",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Sustainable Agriculture Network's Compliant",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "SANS",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Closed Loop",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Take Back Program",
                    "distance": 1,
                    "weight": 1.0
                }
            ]
        },
        {
            "id": 4,
            "name": "Material Ingredient Reporting",
            "terms": [
                {
                    "term": "Material Ingredient Screening",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Optimization Action Plan",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Advanced Inventory Assessment",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "International Alternative Compliant Path",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Global Green Tag PhD",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Global Green Tag",
                    "distance": 1,
                    "weight": 1.0
                }
            ]
        },
        {
            "id": 5,
            "name": "Low Emitting Materials",
            "terms": [
                {
                    "term": "VOC",
                    "distance": 0,
                    "weight": 1.0
                },
                {
                    "term": "Volatile organic compounds",
                    "distance": 2,
                    "weight": 1.0
                },
                {
                    "term": "California Department of Public Health Standard Method Evaluation of Volatile Organic Chemical Emissions",
                    "distance": 4,
                    "weight": 1.0
                },
                {
                    "term": "CDPH Standard Method v1.2",
                    "distance": 2,
                    "weight": 1.0
                },
                {
                    "term": "EN 16516:2017",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "Green Seal GS-11",
                    "distance": 2,
                    "weight": 1.0
                },
                {
                    "term": "SCS Indoor Advantage Gold",
                    "distance": 3,
                    "weight": 1.0
                },
                {
                    "term": "ULEF product under EPA TSCA Title VI",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "NAF product under EPA TSCA Title VI",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "ULEF product under CARB ATCM",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "NAF product under CARB ATCM",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "emissions class E1 tested per EN 717-2014",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "plywood PS 1-09 or PS 2-10",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "OSB Exposure 1 ? Exterior bond classification per PS 2-10",
                    "distance": 4,
                    "weight": 1.0
                },
                {
                    "term": "plywood PS 1-09 ? PS 2-10",
                    "distance": 2,
                    "weight": 1.0
                },
                {
                    "term": "OSB Exposure 1 ? Exterior bond classification per PS 2-10",
                    "distance": 4,
                    "weight": 1.0
                },
                {
                    "term": "ASTM D 5456-13",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "ANSI A190.1-2012",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "ASTM D 5055-13",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "PRG 320-15",
                    "distance": 1,
                    "weight": 1.0
                },
                {
                    "term": "e3-2014e section 7.6.1",
                    "distance": 2,
                    "weight": 1.0
                },
                {
                    "term": "e3-2014e section 7.6.2",
                    "distance": 2,
                    "weight": 1.0
                },
                {
                    "term": "UL Greenguard Certified",
                    "distance": 2,
                    "weight": 1.0
                },
                {
                    "term": "SCS Indoor Advantage",
                    "distance": 2,
                    "weight": 1.0
                },
                {
                    "term": "Intertek Clean Air Silver",
                    "distance": 2,
                    "weight": 1.0
                },
                {
                    "term": "Intertek Clean Air Gold",
                    "distance": 2,
                    "weight": 1.0
                },
                {
                    "term": "MAS Certified Green",
                    "distance": 2,
                    "weight": 1.0
                }
            ]
        }
    ]
}
```

/classifiers/
```
[
    {
        "id": 1,
        "name": "LEED Document Type"
    }
]
```

/classifiers/run/1/1
```
{
    "Environmental Product Declaration": 5.0,
    "Embodied Carbon/LCA Optimization": 0.5,
    "Responsible Sourcing of Raw Materials": 0.0,
    "Material Ingredient Reporting": 0.0,
    "Low Emitting Materials": 1.0
}
```