"""Sora video extraction activities.

These activities handle extracting MP4 URLs from Sora share links and downloading
the raw video files for further processing in the workflow.
"""

from pathlib import Path

from temporalio import activity

from app.core.services.sora_extraction.service import get_sora_service
from app.temporal.schemas import SoraExtractionInput, SoraExtractionOutput


@activity.defn
async def extract_sora_video(input_data: SoraExtractionInput) -> SoraExtractionOutput:
    """Extract MP4 from Sora share link and download to local storage.

    Complete flow:
    1. Fetch the Sora share page
    2. Parse HTML/JSON to extract the underlying MP4 URL
    3. Stream-download the MP4 to temporary storage

    Args:
        input_data: SoraExtractionInput with share_url

    Returns:
        SoraExtractionOutput with local file path and metadata

    Raises:
        ValueError: If the URL is invalid or MP4 cannot be extracted
        aiohttp.ClientError: If HTTP requests fail
        IOError: If file operations fail
    """
    activity.logger.info(f'Extracting video from Sora share link: {input_data.share_url}')

    service = get_sora_service()

    try:
        # Extract and download the video
        output_path = await service.extract_and_download(
            sora_share_url=input_data.share_url,
            temp_dir=Path(input_data.temp_dir) if input_data.temp_dir else None,
        )

        activity.logger.info(f'Successfully extracted video to: {output_path}')

        # Get file metadata
        file_size = output_path.stat().st_size

        return SoraExtractionOutput(
            local_path=str(output_path),
            file_size_bytes=file_size,
        )

    except Exception as e:
        activity.logger.error(f'Failed to extract video from Sora: {str(e)}')
        raise


@activity.defn
async def extract_sora_video_to_path(
    share_url: str,
    output_path: str,
) -> SoraExtractionOutput:
    """Extract and download Sora video to a specific path.

    Args:
        share_url: The Sora share URL
        output_path: Explicit output path for the video

    Returns:
        SoraExtractionOutput with file path and metadata
    """
    activity.logger.info(f'Extracting Sora video to {output_path}')

    service = get_sora_service()

    try:
        result_path = await service.extract_and_download(
            sora_share_url=share_url,
            output_path=Path(output_path),
        )

        file_size = result_path.stat().st_size

        return SoraExtractionOutput(
            local_path=str(result_path),
            file_size_bytes=file_size,
        )

    except Exception as e:
        activity.logger.error(f'Failed to extract video from Sora: {str(e)}')
        raise
