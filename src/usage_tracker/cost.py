"""Cost calculation for LLM API usage."""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    provider: str = "deepseek",
    model_name: Optional[str] = None,
) -> Tuple[float, float]:
    """Calculate cost for LLM API usage based on provider and model."""
    if provider == "deepseek":
        INPUT_COST_PER_1M = 0.28
        OUTPUT_COST_PER_1M = 0.42
    elif provider == "openrouter":
        try:
            from src.openrouter_client import AVAILABLE_MODELS
            if model_name and model_name in AVAILABLE_MODELS:
                model_info = AVAILABLE_MODELS[model_name]
                INPUT_COST_PER_1M = model_info.price_input
                OUTPUT_COST_PER_1M = model_info.price_output
            else:
                logger.warning(f"Model {model_name} not found, using default pricing")
                INPUT_COST_PER_1M = 3.0
                OUTPUT_COST_PER_1M = 15.0
        except ImportError:
            logger.warning("Could not import OpenRouter models, using default pricing")
            INPUT_COST_PER_1M = 3.0
            OUTPUT_COST_PER_1M = 15.0
    else:
        logger.warning(f"Unknown provider {provider}, using DeepSeek pricing")
        INPUT_COST_PER_1M = 0.28
        OUTPUT_COST_PER_1M = 0.42

    input_cost = (input_tokens / 1_000_000) * INPUT_COST_PER_1M
    output_cost = (output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
    return input_cost, output_cost


def calculate_deepseek_cost(input_tokens: int, output_tokens: int) -> Tuple[float, float]:
    """Calculate cost for DeepSeek API usage (legacy)."""
    return calculate_cost(input_tokens, output_tokens, provider="deepseek")
