"""Hello World Workflow.

Simple workflow for testing Temporal connectivity and worker health.
Returns a greeting message to verify end-to-end workflow execution.

Example:
    result = await client.execute_workflow(
        HelloWorldWorkflow.run,
        HelloWorldInput(name='World'),
        id='hello-123',
        task_queue='generation-queue',
    )
    print(result.message)  # "Hello, World!"
"""

from pydantic import BaseModel, Field
from temporalio import workflow

from app.temporal.schemas import WorkflowInput, WorkflowStatus
from app.temporal.workflows.base import WorkflowContext


class HelloWorldInput(WorkflowInput):
    """Input for HelloWorld workflow."""

    name: str = Field('World', description='Name to greet')


class HelloWorldOutput(BaseModel):
    """Output from HelloWorld workflow."""

    message: str = Field(..., description='Greeting message')


@workflow.defn
class HelloWorldWorkflow:
    """Simple workflow that returns a greeting.

    Used for testing connectivity and worker health.
    """

    def __init__(self) -> None:
        self._ctx = WorkflowContext()

    @workflow.query
    def get_status(self) -> WorkflowStatus:
        return self._ctx.status

    @workflow.run
    async def run(self, input: HelloWorldInput) -> HelloWorldOutput:
        self._ctx.start(input)

        async with self._ctx.step('greet', 'Generate Greeting', 50):
            message = f'Hello, {input.name}!'

        self._ctx.complete()
        return HelloWorldOutput(message=message)
