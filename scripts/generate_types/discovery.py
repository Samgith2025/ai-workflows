"""Workflow and schema discovery using existing app/temporal/registry.py.

This module wraps the existing discovery functions and extracts additional
metadata needed for TypeScript generation.
"""

import inspect
from typing import Any

from pydantic import BaseModel, Field

from app.temporal.registry import discover_generation_workflows


class FieldDefinition(BaseModel):
    """Definition of a form field for frontend rendering."""

    model_config = {'arbitrary_types_allowed': True}

    name: str = Field(..., description='Field name')
    type: str = Field(..., description='Field type: text, number, select, textarea, checkbox, json')
    label: str = Field(..., description='Human-readable label')
    description: str = Field('', description='Field description')
    required: bool = Field(False, description='Whether field is required')
    default: Any = Field(None, description='Default value')
    options: list[dict[str, str]] | None = Field(None, description='Options for select fields')
    validation: dict[str, Any] | None = Field(None, description='Validation constraints')
    hidden: bool = Field(False, description='Whether to hide from default forms')


class WorkflowInfo(BaseModel):
    """Complete workflow information for TypeScript generation."""

    model_config = {'arbitrary_types_allowed': True}

    id: str = Field(..., description='Workflow ID (e.g., ruby)')
    name: str = Field(..., description='Human-readable name (e.g., Ruby)')
    description: str = Field('', description='Workflow description')
    workflow_class: str = Field(..., description='Workflow class name (e.g., RubyWorkflow)')
    input_type: str = Field(..., description='Input type name (e.g., RubyInput)')
    output_type: str = Field(..., description='Output type name (e.g., RubyOutput)')
    input_model: type[BaseModel] = Field(..., description='Input Pydantic model class')
    output_model: type[BaseModel] | None = Field(None, description='Output Pydantic model class')
    fields: list[FieldDefinition] = Field(default_factory=list, description='Form field definitions')


def discover_all_workflows() -> list[WorkflowInfo]:
    """Discover all workflows using existing registry and extract metadata.

    Uses app/temporal/registry.discover_generation_workflows() and adds:
    - Input/Output model classes
    - Field definitions for form generation
    - Human-readable names and descriptions
    """
    # Use existing discovery function
    workflow_map = discover_generation_workflows()
    workflows: list[WorkflowInfo] = []

    for workflow_id, workflow_class in workflow_map.items():
        # Get the module where the workflow is defined
        module = inspect.getmodule(workflow_class)
        if not module:
            continue

        # Find Input/Output classes in the same module
        input_model = None
        output_model = None

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__:
                continue

            if issubclass(obj, BaseModel):
                if name.endswith('Input') and 'Input' in name:
                    # Prefer the main input class (e.g., RubyInput, not some nested one)
                    if input_model is None or len(name) < len(input_model.__name__):
                        input_model = obj
                elif (
                    name.endswith('Output')
                    and 'Output' in name
                    and (output_model is None or len(name) < len(output_model.__name__))
                ):
                    output_model = obj

        if not input_model:
            continue

        # Get description from module or class docstring
        description = ''
        if module.__doc__:
            description = module.__doc__.strip().split('\n\n')[0].strip()
        elif workflow_class.__doc__:
            description = workflow_class.__doc__.strip().split('\n\n')[0].strip()

        # Generate human-readable name from workflow ID
        human_name = workflow_id.replace('_', ' ').title()

        # Extract field definitions
        fields = extract_field_definitions(input_model)

        workflows.append(
            WorkflowInfo(
                id=workflow_id,
                name=human_name,
                description=description,
                workflow_class=workflow_class.__name__,
                input_type=input_model.__name__,
                output_type=output_model.__name__
                if output_model
                else f'{input_model.__name__.replace("Input", "Output")}',
                input_model=input_model,
                output_model=output_model,
                fields=fields,
            )
        )

    # Sort by ID for consistent output
    workflows.sort(key=lambda w: w.id)
    return workflows


def extract_field_definitions(model: type[BaseModel]) -> list[FieldDefinition]:
    """Extract field definitions from a Pydantic model for form generation."""
    fields: list[FieldDefinition] = []

    for field_name, field_info in model.model_fields.items():
        field_type = _infer_form_field_type(field_name, field_info)
        description = field_info.description or ''
        label = field_name.replace('_', ' ').title()
        required = field_info.is_required()

        # Get default value
        default = None
        if not field_info.is_required():
            raw_default = field_info.default
            # Handle PydanticUndefined and callable defaults
            if raw_default is not None and not callable(raw_default):
                try:
                    # Test if it's JSON serializable
                    import json

                    json.dumps(raw_default)
                    default = raw_default
                except (TypeError, ValueError):
                    default = None

        # Extract options from Literal type
        options = _extract_options_from_literal(field_info.annotation)

        # Extract validation constraints
        validation = _extract_validation(field_info)

        # Determine if field should be hidden by default
        hidden = field_name.endswith(('_params', '_model'))

        fields.append(
            FieldDefinition(
                name=field_name,
                type=field_type,
                label=label,
                description=description,
                required=required,
                default=default,
                options=options,
                validation=validation,
                hidden=hidden,
            )
        )

    return fields


def _infer_form_field_type(field_name: str, field_info: Any) -> str:
    """Infer the form field type from Pydantic field info."""
    from typing import Literal, get_args, get_origin

    annotation = field_info.annotation

    # Handle Optional types (Union with None)
    origin = get_origin(annotation)
    if origin is type(None) or str(origin) == 'typing.Union':
        args = get_args(annotation)
        # Find the non-None type
        for arg in args:
            if arg is not type(None):
                annotation = arg
                origin = get_origin(annotation)
                break

    # Check for Literal types (select field)
    if get_origin(annotation) is Literal:
        return 'select'

    # Check for dict types (JSON editor)
    if origin is dict or str(annotation).startswith('dict'):
        return 'json'

    # Check for list types
    if origin is list or str(annotation).startswith('list'):
        return 'json'

    # Check basic types
    if annotation is bool:
        return 'checkbox'
    if annotation is int:
        return 'number'
    if annotation is float:
        return 'number'

    # Check for long text fields
    if 'prompt' in field_name or 'description' in field_name or 'text' in field_name:
        return 'textarea'

    return 'text'


def _extract_options_from_literal(annotation: Any) -> list[dict[str, str]] | None:
    """Extract select options from a Literal type annotation.

    Handles:
    - Literal['a', 'b', 'c']
    - Literal['a', 'b'] | None (Optional Literal)
    """
    from typing import Literal, get_args, get_origin

    # Handle Optional types (Union with None)
    origin = get_origin(annotation)
    if str(origin) == 'typing.Union':
        args = get_args(annotation)
        for arg in args:
            if arg is not type(None):
                annotation = arg
                break

    # Check if it's a Literal type
    if get_origin(annotation) is not Literal:
        return None

    # Get the literal values
    values = get_args(annotation)
    if not values:
        return None

    # Convert to options format
    return [{'value': str(v), 'label': str(v).replace('_', ' ').title()} for v in values]


def _extract_validation(field_info: Any) -> dict[str, Any] | None:
    """Extract validation constraints from Pydantic field info."""
    validation: dict[str, Any] = {}

    for meta in field_info.metadata:
        if hasattr(meta, 'ge'):
            validation['min'] = meta.ge
        if hasattr(meta, 'gt'):
            validation['min'] = meta.gt + 1
        if hasattr(meta, 'le'):
            validation['max'] = meta.le
        if hasattr(meta, 'lt'):
            validation['max'] = meta.lt - 1
        if hasattr(meta, 'min_length'):
            validation['minLength'] = meta.min_length
        if hasattr(meta, 'max_length'):
            validation['maxLength'] = meta.max_length
        if hasattr(meta, 'pattern'):
            validation['pattern'] = meta.pattern

    return validation if validation else None
