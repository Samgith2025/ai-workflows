"""Workflow for downloading videos from Sora share links.

Simple one-step workflow:
1. Extract and download MP4 from Sora URL

This can be used standalone or as a building block in larger workflows.
"""

from temporalio import workflow

from app.temporal.activities.sora_extraction import extract_sora_video
from app.temporal.schemas import SoraExtractionInput, SoraExtractionOutput


@workflow.defn
class SoraDownloadWorkflow:
    """Download a video from a Sora share link.

    Usage in a workflow client:
        handle = await client.start_workflow(
            SoraDownloadWorkflow.run,
            SoraExtractionInput(share_url="https://sora.chatgpt.com/share/xxxx"),
            id=f"sora-download-{uuid.uuid4()}",
            task_queue="default",
        )
        result = await handle.result()
    """

    @workflow.run
    async def run(self, input_data: SoraExtractionInput) -> SoraExtractionOutput:
        """Execute the workflow."""
        workflow.logger.info(f'Starting Sora download workflow for: {input_data.share_url}')

        # Call the extraction activity
        result = await workflow.execute_activity(
            extract_sora_video,
            input_data,
            start_to_close_timeout=600,  # 10 minutes
        )

        workflow.logger.info(f'Workflow complete: {result.local_path}')
        return result
