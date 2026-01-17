"""Tool registry - stores registered tools.

The registry holds all registered tools. Tools register themselves
by calling `tool_registry.register(MyTool)` at module level.

Discovery happens in `app/temporal/registry.py` alongside workflow/activity discovery.
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

from app.core.tools.base import ToolCategory, ToolDefinition

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry of all available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool.

        Args:
            tool: Tool definition to register

        Raises:
            ValueError: If a tool with the same ID is already registered
        """
        if tool.id in self._tools:
            raise ValueError(f'Tool with ID "{tool.id}" is already registered')
        self._tools[tool.id] = tool
        logger.debug(f'Registered tool: {tool.id}')

    def unregister(self, tool_id: str) -> None:
        """Unregister a tool by ID."""
        if tool_id in self._tools:
            del self._tools[tool_id]

    def get(self, tool_id: str) -> ToolDefinition | None:
        """Get a tool by ID."""
        return self._tools.get(tool_id)

    def get_or_raise(self, tool_id: str) -> ToolDefinition:
        """Get a tool by ID or raise an error.

        Args:
            tool_id: Tool ID to look up

        Returns:
            Tool definition

        Raises:
            ValueError: If tool is not found
        """
        tool = self._tools.get(tool_id)
        if tool is None:
            available = ', '.join(sorted(self._tools.keys())) or '(none)'
            raise ValueError(f'Tool "{tool_id}" not found. Available tools: {available}')
        return tool

    def list_all(self) -> list[ToolDefinition]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_by_category(self, category: ToolCategory) -> list[ToolDefinition]:
        """List tools by category."""
        return [t for t in self._tools.values() if t.category == category]

    def list_ids(self) -> list[str]:
        """List all tool IDs."""
        return list(self._tools.keys())

    def __contains__(self, tool_id: str) -> bool:
        return tool_id in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# Global registry
tool_registry = ToolRegistry()


# API response schemas
class ToolInfoResponse(BaseModel):
    """Tool information for API response."""

    id: str = Field(description='Unique tool ID')
    name: str = Field(description='Human-readable name')
    category: ToolCategory = Field(description='Tool category')
    description: str = Field(description='Tool description')
    version: str = Field(description='Tool version')
    avg_execution_time_seconds: float | None = None
    rate_limit_per_minute: int | None = None
    requires_api_key: bool = Field(description='Whether API key is required')
    input_schema: dict[str, Any] = Field(description='JSON schema for inputs')
    output_schema: dict[str, Any] = Field(description='JSON schema for outputs')

    @classmethod
    def from_tool(cls, tool: ToolDefinition) -> 'ToolInfoResponse':
        """Create from a ToolDefinition."""
        return cls(
            id=tool.id,
            name=tool.name,
            category=tool.category,
            description=tool.description,
            version=tool.version,
            avg_execution_time_seconds=tool.avg_execution_time_seconds,
            rate_limit_per_minute=tool.rate_limit_per_minute,
            requires_api_key=tool.requires_api_key,
            input_schema=tool.get_input_schema(),
            output_schema=tool.get_output_schema(),
        )


class ToolsListResponse(BaseModel):
    """Response for listing tools."""

    tools: list[ToolInfoResponse] = Field(description='List of available tools')
    total: int = Field(description='Total number of tools')
