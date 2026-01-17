"""TypeScript types and workflow registry generator.

Generates TypeScript types from Pydantic schemas and creates a workflow
registry for dynamic form generation in Next.js.

Usage:
    python -m scripts.generate_types
    python -m scripts.generate_types --bump patch
"""

from scripts.generate_types.discovery import (
    WorkflowInfo,
    discover_all_workflows,
    extract_field_definitions,
)
from scripts.generate_types.typescript import (
    generate_registry_ts,
    generate_types_ts,
    json_schema_to_typescript,
)

__all__ = [
    'WorkflowInfo',
    'discover_all_workflows',
    'extract_field_definitions',
    'generate_types_ts',
    'generate_registry_ts',
    'json_schema_to_typescript',
]
