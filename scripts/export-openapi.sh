#!/usr/bin/env bash
set -e

# Create shared directory if it doesn't exist
mkdir -p ../shared

# Export OpenAPI schema
echo "Exporting OpenAPI schema..."
curl -f http://localhost:8000/openapi.json > ../shared/openapi.json
echo "Done. Schema exported to ../shared/openapi.json"