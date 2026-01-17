"""Generation workflows - one workflow per generation type.

Each generation type has its own workflow file for clarity and easy debugging.
Frontend just sends the generation type name, and we run the corresponding workflow.

Workflows are auto-discovered from this package. To add a new generation:
1. Create a new file (e.g., saas_showcase.py)
2. Define YourWorkflow class with @workflow.defn
3. That's it! It will be auto-discovered.

The workflow name is derived from the class name:
- RubyWorkflow -> 'ruby'
- SaaSShowcaseWorkflow -> 'saas_showcase'
- AnimationWorkflow -> 'animation'

Usage:
    from app.temporal.workflows.generations import GENERATION_WORKFLOWS

    # Get workflow class by name
    workflow_class = GENERATION_WORKFLOWS.get('ruby')

    # Or import directly
    from app.temporal.workflows.generations.ruby import RubyWorkflow
"""

from app.temporal.registry import discover_generation_workflows

# Import individual workflows for direct access
from app.temporal.workflows.generations.ruby import RubyInput, RubyOutput, RubyWorkflow
from app.temporal.workflows.generations.slideshows_pinterest import (
    PinterestImage,
    SlideshowsPinterestInput,
    SlideshowsPinterestOutput,
    SlideshowsPinterestWorkflow,
)

# Auto-discover all generation workflows
GENERATION_WORKFLOWS = discover_generation_workflows()

__all__ = [
    # Registry (auto-discovered)
    'GENERATION_WORKFLOWS',
    # Ruby (for direct imports)
    'RubyWorkflow',
    'RubyInput',
    'RubyOutput',
    # Pinterest Slideshows (for direct imports)
    'SlideshowsPinterestWorkflow',
    'SlideshowsPinterestInput',
    'SlideshowsPinterestOutput',
    'PinterestImage',
]
