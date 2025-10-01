#!/usr/bin/env python3

import json
import os
from pathlib import Path
from typing import Any

from openhands.agent_server.api import api


def generate_openapi_schema() -> dict[str, Any]:
    """Generate an OpenAPI schema with AsyncAPI reference"""
    openapi = api.openapi()

    # Add reference to AsyncAPI documentation for WebSocket endpoints
    if "info" not in openapi:
        openapi["info"] = {}

    # Add AsyncAPI reference to the description
    current_description = openapi["info"].get("description", "")
    asyncapi_note = (
        "\n\n**WebSocket Documentation**: This API also provides WebSocket endpoints "
        "for real-time communication. See the AsyncAPI documentation at "
        "`/asyncapi/` for detailed WebSocket endpoint documentation."
    )

    if "AsyncAPI" not in current_description:
        openapi["info"]["description"] = current_description + asyncapi_note

    # Add external documentation link to AsyncAPI
    if "externalDocs" not in openapi:
        openapi["externalDocs"] = []
    elif not isinstance(openapi["externalDocs"], list):
        openapi["externalDocs"] = [openapi["externalDocs"]]

    # Add AsyncAPI documentation link
    asyncapi_docs = {
        "description": "AsyncAPI Documentation for WebSocket Endpoints",
        "url": "/asyncapi/",
    }

    # Check if AsyncAPI docs already exist
    existing_asyncapi = any(
        doc.get("description", "").startswith("AsyncAPI")
        for doc in openapi["externalDocs"]
    )

    if not existing_asyncapi:
        openapi["externalDocs"].append(asyncapi_docs)

    return openapi


if __name__ == "__main__":
    schema_path = Path(os.environ["SCHEMA_PATH"])
    schema = generate_openapi_schema()
    schema_path.write_text(json.dumps(schema, indent=2))
    print(f"Wrote {schema_path}")
