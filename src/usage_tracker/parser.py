"""Usage extraction from API responses."""

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def extract_usage_from_response(response: Dict[str, Any]) -> Optional[tuple]:
    """Extract usage information from API response (DeepSeek and OpenRouter formats)."""
    try:
        if "usage" in response:
            usage = response["usage"]
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            return input_tokens, output_tokens
    except Exception as e:
        logger.warning(f"Failed to extract usage from response: {e}")
    return None
