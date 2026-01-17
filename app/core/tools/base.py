"""Base types for tool definitions.

Tools are self-contained units that perform specific tasks like:
- Web scraping (Firecrawl, Jina)
- Search APIs (Serper, Tavily)
- Data enrichment (Clearbit, etc.)

Each tool has:
- Input schema (what it accepts)
- Output schema (what it returns)
- An async execute() method
"""

from abc import abstractmethod
from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Category of the tool."""

    SCRAPER = 'scraper'
    SEARCH = 'search'
    DATA = 'data'
    MEDIA = 'media'
    COMMUNICATION = 'communication'
    UTILITY = 'utility'


class ToolInput(BaseModel):
    """Base class for tool input schemas.

    Each tool should define its own input class inheriting from this.
    """

    def validate_params(self) -> None:
        """Validate input parameters.

        Override to add custom validation beyond Pydantic field validators.
        Raises ValueError if validation fails.
        """


class ToolOutput(BaseModel):
    """Base class for tool output schemas.

    Each tool should define its own output class inheriting from this.
    All outputs include success/error fields for consistent error handling.
    """

    success: bool = Field(..., description='Whether the tool executed successfully')
    error: str | None = Field(None, description='Error message if failed')

    @classmethod
    def failure(cls, error: str, **kwargs: Any) -> 'ToolOutput':
        """Create a failure output with an error message."""
        return cls(success=False, error=error, **kwargs)


class ToolDefinition(BaseModel):
    """Definition of a tool.

    Contains metadata about a tool and provides the execute() method.
    """

    # Identification
    id: str = Field(description='Unique tool ID (e.g., "firecrawl", "serper")')
    name: str = Field(description='Human-readable tool name')

    # Categorization
    category: ToolCategory = Field(description='Tool category')

    # Metadata
    description: str = Field('', description='Tool description')
    version: str = Field('1.0.0', description='Tool version')

    # Execution hints
    avg_execution_time_seconds: float | None = Field(
        None,
        description='Average execution time in seconds',
    )
    rate_limit_per_minute: int | None = Field(
        None,
        description='Rate limit (requests per minute)',
    )
    requires_api_key: bool = Field(
        True,
        description='Whether this tool requires an API key',
    )
    timeout_seconds: float = Field(
        30.0,
        description='Default timeout for tool execution',
    )

    # Schema classes (set by subclass)
    input_class: ClassVar[type[ToolInput]]
    output_class: ClassVar[type[ToolOutput]]

    def get_input_schema(self) -> dict[str, Any]:
        """Get the JSON schema for this tool's inputs."""
        return self.input_class.model_json_schema()

    def get_output_schema(self) -> dict[str, Any]:
        """Get the JSON schema for this tool's outputs."""
        return self.output_class.model_json_schema()

    def validate_input(self, input_data: dict[str, Any]) -> ToolInput:
        """Validate and parse input data against this tool's schema."""
        tool_input = self.input_class.model_validate(input_data)
        tool_input.validate_params()
        return tool_input

    @abstractmethod
    async def execute(self, input: ToolInput) -> ToolOutput:
        """Execute the tool with the given input.

        Args:
            input: Validated tool input

        Returns:
            Tool output with results or error
        """
        raise NotImplementedError('Subclass must implement execute()')

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
