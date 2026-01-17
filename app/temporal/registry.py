"""Auto-discovery of Temporal workflows, activities, and tools.

Scans the workflows and activities modules for decorated functions/classes.
All workflows, activities, and tools are automatically discovered - no manual registration needed.
"""

import importlib
import inspect
import logging
import pkgutil
import sys
from typing import Any

logger = logging.getLogger(__name__)


def discover_workflows(package_name: str = 'app.temporal.workflows') -> list[type]:
    """Discover all @workflow.defn decorated classes in a package.

    Recursively scans subpackages (e.g., generations/).
    Classes with `__temporal_workflow_definition` attribute are discovered.
    """
    workflows: list[type] = []

    try:
        package = importlib.import_module(package_name)
    except ImportError:
        logger.exception(f'Failed to import workflow package {package_name}')
        return workflows

    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if module_name.startswith('_') or module_name == 'base':
            continue

        full_module_name = f'{package_name}.{module_name}'

        # Recursively discover workflows in subpackages (like generations/)
        if is_pkg:
            workflows.extend(discover_workflows(full_module_name))
            continue

        try:
            module = importlib.import_module(full_module_name)
        except ImportError:
            logger.exception(f'Failed to import workflow module {full_module_name}')
            continue

        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if hasattr(obj, '__temporal_workflow_definition'):
                workflows.append(obj)
                logger.debug(f'Discovered workflow: {obj.__name__}')

    return workflows


def discover_activities(package_name: str = 'app.temporal.activities') -> list[Any]:
    """Discover all @activity.defn decorated functions in a package.

    Scans all Python files in the package for functions with
    `__temporal_activity_definition` attribute.

    Import errors are logged AND printed to stderr for visibility.
    """
    activities: list[Any] = []

    try:
        package = importlib.import_module(package_name)
    except ImportError:
        msg = f'Failed to import activities package {package_name}'
        logger.exception(msg)
        print(f'ERROR: {msg}', file=sys.stderr)
        return activities

    modules_found: list[str] = []
    modules_failed: list[str] = []

    for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
        if module_name.startswith('_'):
            continue

        # Skip subpackages for activities (they're flat)
        if is_pkg:
            continue

        full_module_name = f'{package_name}.{module_name}'

        try:
            module = importlib.import_module(full_module_name)
            modules_found.append(module_name)
        except Exception:
            modules_failed.append(module_name)
            msg = f'Failed to import activity module {full_module_name}'
            logger.exception(msg)
            print(f'ERROR: {msg}', file=sys.stderr)
            continue

        # Find all activity-decorated functions
        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if hasattr(obj, '__temporal_activity_definition'):
                activities.append(obj)
                logger.debug(f'Discovered activity: {name} from {module_name}')

    if modules_failed:
        print(f'WARNING: Failed to import {len(modules_failed)} activity modules: {modules_failed}', file=sys.stderr)

    logger.info(f'Activity discovery: {len(modules_found)} modules loaded, {len(activities)} activities found')

    return activities


def discover_generation_workflows() -> dict[str, type]:
    """Discover all generation workflows and return as a name -> class mapping.

    Each workflow class should have a class name ending with 'Workflow'.
    The key is derived from the class name: RubyWorkflow -> 'ruby'

    Returns:
        Dict mapping generation names to workflow classes.
        Example: {'ruby': RubyWorkflow, 'saas_showcase': SaaSShowcaseWorkflow}
    """
    workflows = discover_workflows('app.temporal.workflows.generations')
    result = {}

    for workflow_class in workflows:
        # Convert class name to generation key
        # RubyWorkflow -> ruby
        # SaaSShowcaseWorkflow -> saas_showcase
        name = workflow_class.__name__
        name = name.removesuffix('Workflow')  # Remove 'Workflow' suffix

        # Convert CamelCase to snake_case
        key = ''
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                key += '_'
            key += char.lower()

        result[key] = workflow_class

    return result


def discover_tools(base_package: str = 'app.core.tools') -> list[str]:
    """Discover and register all tools by scanning subdirectories dynamically.

    Scans all subpackages of app/core/tools/ for tool files.
    Each tool file should call `tool_registry.register()` at module level.

    Args:
        base_package: Base package path to scan

    Returns:
        List of registered tool IDs.
    """
    from app.core.tools.registry import tool_registry

    modules_loaded = 0
    modules_failed: list[str] = []

    # Track tools before discovery to see what was added
    tools_before = set(tool_registry.list_ids())

    # Import base package to scan its subpackages
    try:
        base = importlib.import_module(base_package)
    except ImportError:
        logger.exception(f'Failed to import tools base package {base_package}')
        return []

    if not hasattr(base, '__path__'):
        return []

    # Dynamically find all subpackages (categories)
    for _, category_name, is_category_pkg in pkgutil.iter_modules(base.__path__):
        # Only scan subpackages, skip modules like base.py, registry.py
        if not is_category_pkg or category_name.startswith('_'):
            continue

        category_package = f'{base_package}.{category_name}'

        try:
            package = importlib.import_module(category_package)
        except ImportError:
            logger.debug(f'Tool category package {category_package} not found, skipping')
            continue

        if not hasattr(package, '__path__'):
            continue

        # Scan modules in this category
        for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
            # Skip __init__, common, and subpackages
            if module_name.startswith('_') or module_name == 'common' or is_pkg:
                continue

            full_module_name = f'{category_package}.{module_name}'

            try:
                importlib.import_module(full_module_name)
                modules_loaded += 1
                logger.debug(f'Loaded tool module: {full_module_name}')
            except Exception:
                modules_failed.append(full_module_name)
                msg = f'Failed to import tool module {full_module_name}'
                logger.exception(msg)
                print(f'ERROR: {msg}', file=sys.stderr)

    # Determine which tools were added
    tools_after = set(tool_registry.list_ids())
    new_tools = tools_after - tools_before

    # Log summary
    total = len(tool_registry)
    logger.info(f'Tool discovery: {modules_loaded} modules loaded, {total} tools registered')

    if new_tools:
        logger.debug(f'Newly registered tools: {sorted(new_tools)}')

    if modules_failed:
        print(
            f'WARNING: Failed to import {len(modules_failed)} tool modules: {modules_failed}',
            file=sys.stderr,
        )

    return tool_registry.list_ids()


def ensure_tools_registered() -> None:
    """Ensure tools are registered. Call discover_tools() if registry is empty.

    This is a convenience function for activities that need to verify
    the registry is populated before using it.
    """
    from app.core.tools.registry import tool_registry

    if len(tool_registry) == 0:
        logger.info('Tool registry empty, running discovery...')
        discover_tools()
