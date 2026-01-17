#!/usr/bin/env python3
"""CLI entry point for TypeScript type generation.

Generates a single NPM package with subpath exports:
- @gptmarket/temporal-types → Types + Registry (client-safe, zero deps pulled in)
- @gptmarket/temporal-types/client → Temporal client utilities (server-only)

Usage:
    python -m scripts.generate_types
    python -m scripts.generate_types --bump patch
    make types
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from pydantic import BaseModel

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / 'generated'
SCHEMAS_DIR = OUTPUT_DIR / 'schemas'
TEMPLATES_DIR = Path(__file__).parent / 'templates'

PACKAGE_NAME = '@gptmarket/temporal-types'


def get_current_version() -> str:
    """Get current version from NPM registry or local package.json.

    Priority:
    1. NPM registry (for CI - always gets the latest published version)
    2. Local package.json (for local development)
    3. Default to 0.0.0
    """
    # Try NPM registry first (works in CI)
    try:
        result = subprocess.run(  # noqa: S603
            ['npm', 'view', PACKAGE_NAME, 'version'],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fall back to local package.json
    package_path = OUTPUT_DIR / 'package.json'
    if package_path.exists():
        data = json.loads(package_path.read_text())
        return data.get('version', '0.0.0')

    return '0.0.0'


def bump_version(version: str, bump_type: str) -> str:
    """Bump version string."""
    parts = [int(p) for p in version.split('.')]
    if bump_type == 'major':
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    elif bump_type == 'minor':
        parts[1] += 1
        parts[2] = 0
    elif bump_type == 'patch':
        parts[2] += 1
    return '.'.join(str(p) for p in parts)


def generate_package_json(version: str) -> dict:
    """Generate package.json with subpath exports."""
    return {
        'name': PACKAGE_NAME,
        'version': version,
        'description': 'TypeScript types and workflow registry for GPTMarket Temporal workflows',
        'main': 'index.ts',
        'types': 'index.ts',
        'sideEffects': False,
        'exports': {
            '.': './index.ts',
            './types': './types.ts',
            './registry': './registry.ts',
            './server': './server.ts',
        },
        'files': [
            'index.ts',
            'types.ts',
            'registry.ts',
            'server.ts',
            'schemas/',
        ],
        'peerDependencies': {
            '@temporalio/client': '>=1.0.0',
        },
        'peerDependenciesMeta': {
            '@temporalio/client': {
                'optional': True,
            },
        },
        'keywords': [
            'temporal',
            'gptmarket',
            'types',
            'typescript',
            'workflows',
            'registry',
        ],
        'license': 'MIT',
        'repository': {
            'type': 'git',
            'url': 'git+https://github.com/gptmarket/gptmarket-generator.git',
        },
    }


def generate_index_ts() -> str:
    """Generate index.ts that exports ONLY types and registry (browser-safe).

    IMPORTANT: Server utilities are NOT exported here to prevent bundlers
    from pulling in @temporalio/client (which has Node.js dependencies).
    """
    return """/**
 * @gptmarket/temporal-types
 *
 * TypeScript types and workflow registry for GPTMarket Temporal workflows.
 * This entry point is browser-safe - no Node.js dependencies.
 *
 * @example Client-side (React components, dynamic forms)
 * ```ts
 * import { workflowRegistry, ruby } from '@gptmarket/temporal-types';
 * import type { RubyInput, RubyOutput } from '@gptmarket/temporal-types';
 *
 * // Build dynamic UI from workflow definitions
 * ruby.fields.forEach(field => {
 *   console.log(field.name, field.type, field.options);
 * });
 * ```
 *
 * @example Server-side (API routes, server actions)
 * ```ts
 * import { startWorkflow, waitForWorkflow } from '@gptmarket/temporal-types/server';
 * import type { RubyInput, RubyOutput } from '@gptmarket/temporal-types';
 *
 * const { workflowId } = await startWorkflow('RubyWorkflow', { topic: 'AI news' });
 * const { result } = await waitForWorkflow<RubyOutput>(workflowId);
 * ```
 */

// Types (browser-safe)
export * from './types';

// Workflow registry and definitions (browser-safe)
export * from './registry';

// NOTE: Server utilities are intentionally NOT exported from this entry point.
// Import from '@gptmarket/temporal-types/server' for server-side code.
// This prevents bundlers from pulling in @temporalio/client dependencies.
"""


def collect_all_models(workflows: list) -> list[tuple[str, type[BaseModel]]]:
    """Collect all unique Pydantic models from workflows."""
    seen = set()
    models: list[tuple[str, type[BaseModel]]] = []

    for wf in workflows:
        if wf.input_type not in seen:
            seen.add(wf.input_type)
            models.append((wf.input_type, wf.input_model))

        if wf.output_model and wf.output_type not in seen:
            seen.add(wf.output_type)
            models.append((wf.output_type, wf.output_model))

    models.sort(key=lambda x: x[0])
    return models


def main():
    """Main entry point."""
    # Import here to avoid circular imports and ensure project is in path
    sys.path.insert(0, str(PROJECT_ROOT))

    from scripts.generate_types.discovery import discover_all_workflows
    from scripts.generate_types.typescript import generate_registry_ts, generate_types_ts

    parser = argparse.ArgumentParser(description='Generate TypeScript types from Pydantic schemas')
    parser.add_argument(
        '--bump',
        choices=['major', 'minor', 'patch'],
        help='Bump version (major, minor, or patch)',
    )
    args = parser.parse_args()

    print('🔄 Generating TypeScript types and registry...\n')

    # Create output directories
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)

    # Handle versioning
    current_version = get_current_version()
    if args.bump:
        version = bump_version(current_version, args.bump)
        print(f'📌 Version: {current_version} → {version}\n')
    else:
        version = current_version if current_version != '0.0.0' else '0.0.1'
        print(f'📌 Version: {version}\n')

    # Discover workflows
    print('🔍 Discovering workflows...')
    workflows = discover_all_workflows()
    for wf in workflows:
        print(f'  ✓ {wf.id} ({wf.workflow_class}) - {len(wf.fields)} fields')
    print(f'   Found {len(workflows)} workflows\n')

    # Collect all models
    models = collect_all_models(workflows)

    # Export JSON schemas
    print('📄 Exporting JSON schemas:')
    for name, model in models:
        schema = model.model_json_schema()
        schema_path = SCHEMAS_DIR / f'{name}.json'
        schema_path.write_text(json.dumps(schema, indent=2))
        print(f'  ✓ {name}')
    print()

    # Generate TypeScript files
    print('📝 Generating TypeScript files:')

    types_content = generate_types_ts(models)
    types_path = OUTPUT_DIR / 'types.ts'
    types_path.write_text(types_content)
    print('  ✓ types.ts')

    registry_content = generate_registry_ts(workflows)
    registry_path = OUTPUT_DIR / 'registry.ts'
    registry_path.write_text(registry_content)
    print('  ✓ registry.ts')

    # Copy server template
    server_src = TEMPLATES_DIR / 'server.ts'
    server_dst = OUTPUT_DIR / 'server.ts'
    if server_src.exists():
        shutil.copy(server_src, server_dst)
        print('  ✓ server.ts')

    index_content = generate_index_ts()
    index_path = OUTPUT_DIR / 'index.ts'
    index_path.write_text(index_content)
    print('  ✓ index.ts')

    # Generate package.json
    print('\n📦 Generating package.json...')
    package_json = generate_package_json(version)
    package_path = OUTPUT_DIR / 'package.json'
    package_path.write_text(json.dumps(package_json, indent=2))
    print('  ✓ package.json')

    # Try to format with prettier
    try:
        subprocess.run(
            ['npx', 'prettier', '--write', '*.ts'],  # noqa: S607
            capture_output=True,
            timeout=30,
            cwd=OUTPUT_DIR,
            check=False,
        )
        print('\n✨ Formatted with Prettier')
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    print(f'\n✅ Done! Generated in: {OUTPUT_DIR}')
    print('\n📋 Generated files:')
    print('   • types.ts     - TypeScript interfaces')
    print('   • registry.ts  - Workflow definitions for dynamic UI')
    print('   • server.ts    - Temporal server utilities')
    print('   • index.ts     - Re-exports types + registry (browser-safe)')
    print('   • schemas/     - JSON Schema files')
    print('\n🚀 Usage:')
    print(f'   npm install {PACKAGE_NAME}')
    print()
    print('   // Browser/React (dynamic forms, UI generation)')
    print(f"   import {{ workflowRegistry, ruby }} from '{PACKAGE_NAME}';")
    print(f"   import type {{ RubyInput }} from '{PACKAGE_NAME}';")
    print()
    print('   // Server-side (API routes, server actions)')
    print(f"   import {{ startWorkflow }} from '{PACKAGE_NAME}/server';")
    print("   const { workflowId } = await startWorkflow('RubyWorkflow', input);")
    print(f'\n📦 Package: {PACKAGE_NAME}@{version}')


if __name__ == '__main__':
    main()
