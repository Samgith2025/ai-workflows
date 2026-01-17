"""Tools package - scrapers, API calls, and external integrations.

Tools are self-contained units that perform specific tasks. Each tool:
- Has typed input/output schemas (Pydantic)
- Is auto-discovered at startup
- Can be executed via Temporal activities

## Adding a New Tool

1. Create a file in the appropriate category directory:
   `app/core/tools/{category}/{tool_name}.py`

2. Define input/output schemas and tool class:

   ```python
   from pydantic import Field
   from app.core.tools.base import ToolCategory, ToolDefinition, ToolInput, ToolOutput
   from app.core.tools.registry import tool_registry


   class MyToolInput(ToolInput):
       url: str = Field(..., description='URL to process')


   class MyToolOutput(ToolOutput):
       data: str = Field(..., description='Processed data')


   class MyToolDefinition(ToolDefinition):
       input_class = MyToolInput
       output_class = MyToolOutput

       async def execute(self, input: MyToolInput) -> MyToolOutput:
           # Implementation here
           return MyToolOutput(success=True, data='result')


   MyTool = MyToolDefinition(
       id='my-tool',
       name='My Tool',
       category=ToolCategory.UTILITY,
       description='Does something useful',
   )

   tool_registry.register(MyTool)
   ```

3. The tool is automatically discovered - no other changes needed.

## Usage in Workflows

```python
from app.temporal.activities import execute_tool

result = await run_activity(
    execute_tool,
    ExecuteToolInput(tool_id='my-tool', params={'url': 'https://example.com'}),
)
```

## Categories

- scrapers/  - Web scraping tools (Firecrawl, Jina, etc.)
- search/    - Search APIs (Serper, Tavily, etc.)
- data/      - Data enrichment (Clearbit, etc.)
- media/     - Media processing tools
- communication/ - Email, SMS, etc.
- utility/   - General utilities
"""

from app.core.tools.base import (
    ToolCategory,
    ToolDefinition,
    ToolInput,
    ToolOutput,
)
from app.core.tools.registry import (
    ToolInfoResponse,
    ToolsListResponse,
    tool_registry,
)

__all__ = [
    # Base classes
    'ToolCategory',
    'ToolDefinition',
    'ToolInput',
    'ToolOutput',
    # Registry
    'tool_registry',
    # Response schemas
    'ToolInfoResponse',
    'ToolsListResponse',
]
