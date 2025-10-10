from genson import SchemaBuilder
import json

# Load JSON data
with open("version_template.json", "r") as f:
    data = json.load(f)

# Fill examples
data['name'] = "Example Bible"
data['initials'] = "EB"
data['version'] = "2025"
data['citation'] = "Example Bible Citation"
data['books'][0]['chapters'][0]['verses'][0]['heading'] = "example heading"
data['books'][0]['chapters'][0]['verses'][0]['text'] = "example verse text"
data['books'][0]['chapters'][0]['verses'][0]['cross_references']['refers_me'].append({"book": "book", "chapter": 1, "verse": 1})
data['books'][0]['chapters'][0]['verses'][0]['cross_references']['refers_to'].append({"book": "book", "chapter": 1, "verse": 1})
data['books'][0]['chapters'][0]['verses'][0]['footnote'] = "footnote text"

# Build schema
builder = SchemaBuilder(schema_uri="http://json-schema.org/draft-07/schema#")
builder.add_object(data)

# Get schema as dictionary
schema = builder.to_schema()

# Tweak schema
schema["properties"]["citation"]["type"] = ["null","string"]

# Print or save schema
with open("version_template_schema.json", "w") as f:
    json.dump(schema, f, indent=4)

