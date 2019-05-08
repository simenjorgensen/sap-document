Microservice for getting sap-documents into Sesam from HTTP source.

Sample system in Sesam:
```
{
  "_id": "service",
  "type": "system:microservice",
  "docker": {
    "environment": {
      "PORT": 5000,
      "element_key": "<element_key>",
      "key": "$SECRET(key)",
      "root_key": "<root_key>",
      "url": "$ENV(baseurl)",
      "username": "$ENV(username)"
    },
    "hosts": {
      "<host>": "<IP_address>"
    },
    "image": "<docker_username>/<docker_repo>:<verison>",
    "port": 5000
  }
}
```

Sample input pipe:

```
{
  "_id": "sap-document",
  "type": "pipe",
  "source": {
    "type": "conditional",
    "alternatives": {
      "prod": {
        "type": "json",
        "system": "service",
        "url": "/<path>"
      },
      "test": {
        "type": "embedded",
        "entities": [{<test_data>}]
      }
    },
    "condition": "$ENV(current-env)"
  },
  "transform": {
    "type": "dtl",
    "rules": {
      "default": [
        ["add", "_id", "ID"],
        ["add", "composite_id", "_id"],
        ["copy", "*"],
        ["add", "rdf:type",
          ["ni", "sap", "document"]
        ],
        ["add", "system_name", "sap"],
        ["add", "view", "doc_view"],
        ["add", "type_key", "_S.type_key"]
      ]
    }
  }
}
```
