"""
Image text extraction for Tasker.

Uses Claude's vision API to extract text from handwritten note images.
"""

import base64
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from .config import fetch_api_key, load_model_config, DEFAULT_MODEL
from .prompts import IMAGE_EXTRACTION_PROMPT

# Supported image file extensions
IMAGE_EXTENSIONS = {".png"}

# Mapping of file extensions to MIME types
MEDIA_TYPE_MAP = {".png": "image/png"}


def extract_text_from_image(image_path: Path, api_key: str | None = None) -> str:
    """Extract text from an image of handwritten notes using Claude's vision API.

    Args:
        image_path: Path to the image file
        api_key: Optional Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)

    Returns:
        Extracted text content from the image
    """
    config = load_model_config()

    # Extract model from config or use default
    model = config.pop("model", DEFAULT_MODEL)

    # Build ChatAnthropic with config parameters
    llm = ChatAnthropic(
        model=model,
        api_key=fetch_api_key(api_key),
        **config
    )

    # Read and encode the image
    image_data = base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")

    # Determine media type based on file extension
    suffix = image_path.suffix.lower()
    media_type = MEDIA_TYPE_MAP.get(suffix, "image/png")

    # Create message with image content
    message = HumanMessage(
        content=[
            {"type": "text", "text": IMAGE_EXTRACTION_PROMPT},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{image_data}"},
            },
        ]
    )

    response = llm.invoke([message])
    return response.content
