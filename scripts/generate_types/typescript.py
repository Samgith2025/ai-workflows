"""TypeScript code generation from Pydantic schemas.

Generates:
- types.ts: TypeScript interfaces from Pydantic models
- registry.ts: Workflow registry with field definitions for form generation
"""

import json
from typing import Any

from pydantic import BaseModel

from scripts.generate_types.discovery import WorkflowInfo

# =============================================================================
# JSON Schema to TypeScript Conversion
# =============================================================================


def json_schema_to_typescript(schema: dict[str, Any], name: str) -> str:
    """Convert a JSON Schema to TypeScript interface."""
    lines = []

    if 'enum' in schema:
        values = ' | '.join(f"'{v}'" for v in schema['enum'])
        return f'export type {name} = {values};'

    if schema.get('type') == 'object' or 'properties' in schema:
        lines.append(f'export interface {name} {{')

        properties = schema.get('properties', {})
        required = set(schema.get('required', []))
        defs = schema.get('$defs', {})

        for prop_name, prop_schema in properties.items():
            ts_type = _json_type_to_ts(prop_schema, defs)
            optional = '?' if prop_name not in required else ''
            description = prop_schema.get('description', '')
            if description:
                lines.append(f'  /** {description} */')
            lines.append(f'  {prop_name}{optional}: {ts_type};')

        lines.append('}')
        return '\n'.join(lines)

    return f'export type {name} = unknown;'


def _json_type_to_ts(schema: dict[str, Any] | bool, defs: dict[str, Any] | None = None) -> str:
    """Convert JSON Schema type to TypeScript type."""
    if isinstance(schema, bool):
        return 'unknown' if schema else 'never'

    defs = defs or {}

    if '$ref' in schema:
        ref = schema['$ref']
        if ref.startswith('#/$defs/'):
            ref_name = ref.split('/')[-1]
            if ref_name in defs:
                return _json_type_to_ts(defs[ref_name], defs)
            return ref_name
        return 'unknown'

    if 'anyOf' in schema:
        types = []
        for option in schema['anyOf']:
            if option.get('type') == 'null':
                types.append('null')
            else:
                types.append(_json_type_to_ts(option, defs))
        return ' | '.join(types)

    if 'allOf' in schema:
        return _json_type_to_ts(schema['allOf'][0], defs)

    if 'const' in schema:
        const = schema['const']
        if isinstance(const, str):
            return f"'{const}'"
        return str(const)

    if 'enum' in schema:
        return ' | '.join(f"'{v}'" if isinstance(v, str) else str(v) for v in schema['enum'])

    json_type = schema.get('type')

    if json_type == 'string':
        return 'string'
    if json_type in {'integer', 'number'}:
        return 'number'
    if json_type == 'boolean':
        return 'boolean'
    if json_type == 'null':
        return 'null'
    if json_type == 'array':
        items = schema.get('items', {})
        item_type = _json_type_to_ts(items, defs)
        return f'{item_type}[]'
    if json_type == 'object':
        if 'additionalProperties' in schema:
            value_type = _json_type_to_ts(schema['additionalProperties'], defs)
            return f'Record<string, {value_type}>'
        if 'properties' in schema:
            props = []
            for prop_name, prop_schema in schema['properties'].items():
                prop_type = _json_type_to_ts(prop_schema, defs)
                req = prop_name in schema.get('required', [])
                opt = '' if req else '?'
                props.append(f'{prop_name}{opt}: {prop_type}')
            return '{ ' + '; '.join(props) + ' }'
        return 'Record<string, unknown>'

    return 'unknown'


# =============================================================================
# types.ts Generation
# =============================================================================


def generate_types_ts(models: list[tuple[str, type[BaseModel]]]) -> str:
    """Generate types.ts with all TypeScript interfaces."""
    lines = [
        '/**',
        ' * Auto-generated TypeScript types from Pydantic schemas.',
        ' * DO NOT EDIT MANUALLY - run `make types`',
        ' */',
        '',
        '// =============================================================================',
        '// Common Types',
        '// =============================================================================',
        '',
        "export type WorkflowStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';",
        '',
        'export interface StepProgress {',
        '  step_id: string;',
        '  step_name: string;',
        '  status: WorkflowStatus;',
        '  progress_pct: number;',
        '  message: string | null;',
        '}',
        '',
        'export interface WorkflowProgress<TResult = unknown> {',
        '  workflowId: string;',
        '  status: WorkflowStatus;',
        '  executionStatus: string;',
        '  currentStep: StepProgress | null;',
        '  result?: TResult;',
        '  error?: string;',
        '}',
        '',
        '// =============================================================================',
        '// Workflow Schemas',
        '// =============================================================================',
        '',
    ]

    for name, model in models:
        schema = model.model_json_schema()
        ts_code = json_schema_to_typescript(schema, name)
        lines.append(ts_code)
        lines.append('')

    return '\n'.join(lines)


# =============================================================================
# registry.ts Generation
# =============================================================================


def generate_registry_ts(workflows: list[WorkflowInfo]) -> str:
    """Generate registry.ts with workflow definitions and field metadata."""
    lines = [
        '/**',
        ' * Auto-generated workflow registry for dynamic form generation.',
        ' * DO NOT EDIT MANUALLY - run `make types`',
        ' */',
        '',
        "import type * as Types from './types';",
        '',
        '// =============================================================================',
        '// Field Types',
        '// =============================================================================',
        '',
        "export type FieldType = 'text' | 'textarea' | 'number' | 'select' | 'checkbox' | 'json';",
        '',
        'export interface SelectOption {',
        '  value: string;',
        '  label: string;',
        '}',
        '',
        'export interface FieldValidation {',
        '  min?: number;',
        '  max?: number;',
        '  minLength?: number;',
        '  maxLength?: number;',
        '  pattern?: string;',
        '}',
        '',
        'export interface FieldDefinition {',
        '  name: string;',
        '  type: FieldType;',
        '  label: string;',
        '  description: string;',
        '  required: boolean;',
        '  default: unknown;',
        '  options?: SelectOption[];',
        '  validation?: FieldValidation;',
        '  hidden?: boolean;',
        '}',
        '',
        '// =============================================================================',
        '// Workflow Definition',
        '// =============================================================================',
        '',
        'export interface WorkflowDefinition<TInput = unknown, TOutput = unknown> {',
        '  id: string;',
        '  name: string;',
        '  description: string;',
        '  workflowClass: string;',
        '  inputType: string;',
        '  outputType: string;',
        '  fields: FieldDefinition[];',
        '}',
        '',
        '// =============================================================================',
        '// Workflow Definitions',
        '// =============================================================================',
        '',
    ]

    # Generate individual workflow definitions
    for wf in workflows:
        lines.append(f'export const {wf.id}: WorkflowDefinition<Types.{wf.input_type}, Types.{wf.output_type}> = {{')
        lines.append(f"  id: '{wf.id}',")
        lines.append(f"  name: '{wf.name}',")
        lines.append(f"  description: '{_escape_string(wf.description)}',")
        lines.append(f"  workflowClass: '{wf.workflow_class}',")
        lines.append(f"  inputType: '{wf.input_type}',")
        lines.append(f"  outputType: '{wf.output_type}',")
        lines.append('  fields: [')

        for field in wf.fields:
            lines.append('    {')
            lines.append(f"      name: '{field.name}',")
            lines.append(f"      type: '{field.type}',")
            lines.append(f"      label: '{field.label}',")
            lines.append(f"      description: '{_escape_string(field.description)}',")
            lines.append(f'      required: {str(field.required).lower()},')
            lines.append(f'      default: {json.dumps(field.default)},')
            if field.options:
                lines.append(f'      options: {json.dumps(field.options)},')
            if field.validation:
                lines.append(f'      validation: {json.dumps(field.validation)},')
            if field.hidden:
                lines.append('      hidden: true,')
            lines.append('    },')

        lines.append('  ],')
        lines.append('};')
        lines.append('')

    # Generate the registry object
    lines.append('// =============================================================================')
    lines.append('// Registry')
    lines.append('// =============================================================================')
    lines.append('')
    lines.append('export const workflowRegistry = {')
    for wf in workflows:
        lines.append(f'  {wf.id},')
    lines.append('} as const;')
    lines.append('')
    lines.append('export type WorkflowId = keyof typeof workflowRegistry;')
    lines.append('')

    # Generate helper functions
    lines.append('// =============================================================================')
    lines.append('// Helpers')
    lines.append('// =============================================================================')
    lines.append('')
    lines.append('export function getWorkflow<T extends WorkflowId>(id: T): typeof workflowRegistry[T] {')
    lines.append('  return workflowRegistry[id];')
    lines.append('}')
    lines.append('')
    lines.append('export function getAllWorkflows(): WorkflowDefinition[] {')
    lines.append('  return Object.values(workflowRegistry);')
    lines.append('}')
    lines.append('')
    lines.append('export function getWorkflowIds(): WorkflowId[] {')
    lines.append('  return Object.keys(workflowRegistry) as WorkflowId[];')
    lines.append('}')
    lines.append('')

    # Generate type mappings
    lines.append('// Type mappings')
    lines.append('export type WorkflowInputMap = {')
    for wf in workflows:
        lines.append(f'  {wf.id}: Types.{wf.input_type};')
    lines.append('};')
    lines.append('')
    lines.append('export type WorkflowOutputMap = {')
    for wf in workflows:
        lines.append(f'  {wf.id}: Types.{wf.output_type};')
    lines.append('};')
    lines.append('')

    return '\n'.join(lines)


def _escape_string(s: str) -> str:
    """Escape string for JavaScript."""
    return s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
