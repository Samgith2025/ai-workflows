"""Tool execution activities.

These activities allow workflows to execute any registered tool
by ID with validated input parameters.
"""

from typing import Any

from pydantic import BaseModel, Field
from temporalio import activity

from app.core.tools.registry import tool_registry
from app.temporal.registry import ensure_tools_registered


class ExecuteToolInput(BaseModel):
    """Input for executing a tool."""

    tool_id: str = Field(..., description='ID of the tool to execute')
    params: dict[str, Any] = Field(
        default_factory=dict,
        description='Tool input parameters',
    )


class ExecuteToolOutput(BaseModel):
    """Output from tool execution."""

    tool_id: str = Field(..., description='ID of the tool that was executed')
    success: bool = Field(..., description='Whether execution was successful')
    output: dict[str, Any] = Field(
        default_factory=dict,
        description='Tool output data',
    )
    error: str | None = Field(None, description='Error message if failed')


@activity.defn
async def execute_tool(input: ExecuteToolInput) -> ExecuteToolOutput:
    """Execute a tool by ID with the given parameters.

    This activity:
    1. Looks up the tool in the registry
    2. Validates the input against the tool's schema
    3. Executes the tool
    4. Returns the output

    Args:
        input: Tool ID and parameters

    Returns:
        ExecuteToolOutput with results or error

    Raises:
        ValueError: If tool is not found
    """
    activity.logger.info(f'Executing tool: {input.tool_id}')

    # Ensure tools are registered
    ensure_tools_registered()

    # Get the tool
    tool = tool_registry.get_or_raise(input.tool_id)

    try:
        # Validate and parse input
        tool_input = tool.validate_input(input.params)

        # Execute the tool
        result = await tool.execute(tool_input)

        activity.logger.info(f'Tool {input.tool_id} completed: success={result.success}')

        return ExecuteToolOutput(
            tool_id=input.tool_id,
            success=result.success,
            output=result.model_dump(),
            error=result.error,
        )

    except Exception as e:
        activity.logger.error(f'Tool {input.tool_id} failed: {e}')
        return ExecuteToolOutput(
            tool_id=input.tool_id,
            success=False,
            output={},
            error=str(e),
        )


@activity.defn
async def list_available_tools() -> list[dict[str, Any]]:
    """List all available tools.

    Returns:
        List of tool info dictionaries
    """
    ensure_tools_registered()

    return [
        {
            'id': tool.id,
            'name': tool.name,
            'category': tool.category.value,
            'description': tool.description,
            'requires_api_key': tool.requires_api_key,
        }
        for tool in tool_registry.list_all()
    ]
