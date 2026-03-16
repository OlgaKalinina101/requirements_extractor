"""Usage tracking decorator and global report management."""

import functools
import logging
from datetime import datetime
from typing import Callable, Optional

from .models import UsageReport, UsageStats
from .cost import calculate_cost
from .parser import extract_usage_from_response

logger = logging.getLogger(__name__)

_usage_report = UsageReport()


def get_usage_report() -> UsageReport:
    """Get the global usage report instance."""
    return _usage_report


def reset_usage_report() -> None:
    """Reset the global usage report."""
    global _usage_report
    _usage_report = UsageReport()


def track_usage(
    model_name: Optional[str] = None,
    provider: Optional[str] = "deepseek",
    section: Optional[str] = None,
):
    """Decorator for tracking LLM API usage and costs."""

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            try:
                _model_name = model_name or getattr(args[0], "model_name", "unknown")
                _provider = provider or getattr(args[0], "provider", "deepseek")
                _section = section or getattr(args[0], "current_section", None)

                usage = extract_usage_from_response(result)
                if usage is None:
                    logger.debug("No usage information found in response")
                    return result

                input_tokens, output_tokens = usage
                input_cost, output_cost = calculate_cost(
                    input_tokens,
                    output_tokens,
                    provider=_provider,
                    model_name=_model_name,
                )

                stats = UsageStats(
                    timestamp=datetime.now(),
                    model_name=_model_name,
                    provider=_provider,
                    section=_section,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    input_cost=input_cost,
                    output_cost=output_cost,
                )
                _usage_report.add_call(stats)

                logger.info(
                    f"API Call [{_section or 'N/A'}]: "
                    f"Input={input_tokens:,} tokens, "
                    f"Output={output_tokens:,} tokens, "
                    f"Cost=${stats.total_cost:.6f}"
                )
            except Exception as e:
                logger.warning(f"[track_usage] Error in decorator: {e}")
            return result

        return wrapper

    return decorator
