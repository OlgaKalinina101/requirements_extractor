"""Usage tracking decorator and utilities for LLM API calls.

This module provides decorators and utilities for tracking token usage and
costs across LLM API calls (DeepSeek, OpenRouter, etc.). Maintains session-wide statistics and
generates detailed cost reports.

Classes:
    UsageStats: Statistics for a single API call.
    UsageReport: Aggregate usage report for a session.

Functions:
    calculate_cost: Calculate cost for given token counts based on provider/model.
    track_usage: Decorator for tracking API usage.
    get_usage_report: Retrieve current usage report.
    reset_usage_report: Clear usage statistics.
    extract_usage_from_response: Parse usage data from API response.
"""

# Standard library imports
import functools
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# Local imports
from .logger import get_logger

logger = get_logger(__name__)


@dataclass
class UsageStats:
    """Statistics for a single LLM API call.
    
    Tracks token usage and associated costs for one API request/response.
    
    Attributes:
        timestamp: When the API call was made.
        model_name: Name of the model used.
        provider: API provider (e.g., 'deepseek').
        section: Optional section identifier for grouping stats.
        input_tokens: Number of input (prompt) tokens.
        output_tokens: Number of output (completion) tokens.
        input_cost: Cost of input tokens in USD.
        output_cost: Cost of output tokens in USD.
    """
    
    timestamp: datetime
    model_name: str
    provider: str
    section: Optional[str]
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens used in this call.
        
        Returns:
            Sum of input and output tokens.
        """
        return self.input_tokens + self.output_tokens
    
    @property
    def total_cost(self) -> float:
        """Get total cost of this call in USD.
        
        Returns:
            Sum of input and output costs.
        """
        return self.input_cost + self.output_cost


@dataclass
class UsageReport:
    """Complete usage report aggregating multiple API calls.
    
    Maintains a list of all API calls in a session and provides
    aggregate statistics and formatted reports.
    
    Attributes:
        calls: List of individual API call statistics.
    """
    
    calls: List[UsageStats] = field(default_factory=list)
    
    def add_call(self, stats: UsageStats) -> None:
        """Add a new API call to the report.
        
        Args:
            stats: UsageStats instance for the API call.
        """
        self.calls.append(stats)
    
    @property
    def total_input_tokens(self) -> int:
        """Get total input tokens across all calls.
        
        Returns:
            Sum of input tokens from all API calls.
        """
        return sum(call.input_tokens for call in self.calls)
    
    @property
    def total_output_tokens(self) -> int:
        """Get total output tokens across all calls.
        
        Returns:
            Sum of output tokens from all API calls.
        """
        return sum(call.output_tokens for call in self.calls)
    
    @property
    def total_tokens(self) -> int:
        """Get total tokens across all calls.
        
        Returns:
            Sum of all input and output tokens.
        """
        return self.total_input_tokens + self.total_output_tokens
    
    @property
    def total_cost(self) -> float:
        """Get total cost in USD across all calls.
        
        Returns:
            Sum of all API call costs.
        """
        return sum(call.total_cost for call in self.calls)
    
    @property
    def calls_count(self) -> int:
        """Get number of API calls tracked.
        
        Returns:
            Total number of API calls in this report.
        """
        return len(self.calls)
    
    def get_stats_by_section(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics grouped by section identifier.
        
        Aggregates usage statistics by section for detailed breakdowns.
        
        Returns:
            Dictionary mapping section names to their aggregate statistics:
                - calls: Number of calls in this section
                - input_tokens: Total input tokens
                - output_tokens: Total output tokens
                - cost: Total cost in USD
        """
        sections: Dict[str, Dict[str, Any]] = {}
        for call in self.calls:
            section = call.section or "unknown"
            if section not in sections:
                sections[section] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                }
            sections[section]["calls"] += 1
            sections[section]["input_tokens"] += call.input_tokens
            sections[section]["output_tokens"] += call.output_tokens
            sections[section]["cost"] += call.total_cost
        return sections
    
    def format_report(self, provider_name: str = "LLM API") -> str:
        """Format usage report as human-readable text.
        
        Generates a formatted text report with overall statistics and
        per-section breakdowns.
        
        Args:
            provider_name: Name of the API provider (e.g., "OpenRouter", "DeepSeek API")
        
        Returns:
            Multi-line string with formatted usage report.
        """
        lines = [
            "=" * 80,
            f"USAGE REPORT - {provider_name}",
            "=" * 80,
            "",
            f"Total API Calls: {self.calls_count}",
            f"Total Input Tokens: {self.total_input_tokens:,}",
            f"Total Output Tokens: {self.total_output_tokens:,}",
            f"Total Tokens: {self.total_tokens:,}",
            "",
            f"Total Cost: ${self.total_cost:.4f} USD",
            "",
            "=" * 80,
            "BREAKDOWN BY SECTION",
            "=" * 80,
            "",
        ]
        
        sections = self.get_stats_by_section()
        for section_name, stats in sorted(sections.items()):
            lines.extend([
                f"Section: {section_name}",
                f"  Calls: {stats['calls']}",
                f"  Input Tokens: {stats['input_tokens']:,}",
                f"  Output Tokens: {stats['output_tokens']:,}",
                f"  Cost: ${stats['cost']:.4f}",
                "",
            ])
        
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def save_to_file(self, filepath: Path, provider_name: Optional[str] = None) -> None:
        """Save report to file.
        
        Args:
            filepath: Path to save the report
            provider_name: Name of the API provider (e.g., "OpenRouter", "DeepSeek API")
                          If None, will try to detect from calls
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Auto-detect provider if not specified
        if provider_name is None:
            if self.calls:
                # Get provider from first call
                provider_name = self.calls[0].provider.title()
                if provider_name == "Openrouter":
                    provider_name = "OpenRouter"
                elif provider_name == "Deepseek":
                    provider_name = "DeepSeek API"
            else:
                provider_name = "LLM API"
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.format_report(provider_name=provider_name))
        logger.info(f"Usage report saved to {filepath}")


# Global usage report instance
_usage_report = UsageReport()


def get_usage_report() -> UsageReport:
    """Get the global usage report instance."""
    return _usage_report


def reset_usage_report() -> None:
    """Reset the global usage report."""
    global _usage_report
    _usage_report = UsageReport()


def calculate_cost(
    input_tokens: int, 
    output_tokens: int, 
    provider: str = "deepseek",
    model_name: Optional[str] = None
) -> Tuple[float, float]:
    """Calculate cost for LLM API usage based on provider and model.
    
    Supports multiple providers:
    - DeepSeek: Fixed pricing
    - OpenRouter: Model-specific pricing (from ModelInfo)
    
    Args:
        input_tokens: Number of input (prompt) tokens.
        output_tokens: Number of output (completion) tokens.
        provider: Provider name ("deepseek" or "openrouter").
        model_name: Model identifier (required for OpenRouter).
    
    Returns:
        Tuple of (input_cost, output_cost) in USD.
    """
    if provider == "deepseek":
        # DeepSeek pricing (as of 2026)
        INPUT_COST_PER_1M = 0.28
        OUTPUT_COST_PER_1M = 0.42
    elif provider == "openrouter":
        # OpenRouter pricing - need to get from model info
        try:
            from .openrouter_client import AVAILABLE_MODELS
            if model_name and model_name in AVAILABLE_MODELS:
                model_info = AVAILABLE_MODELS[model_name]
                INPUT_COST_PER_1M = model_info.price_input
                OUTPUT_COST_PER_1M = model_info.price_output
            else:
                # Default to Claude Sonnet pricing if model not found
                logger.warning(f"Model {model_name} not found, using default pricing")
                INPUT_COST_PER_1M = 3.0
                OUTPUT_COST_PER_1M = 15.0
        except ImportError:
            logger.warning("Could not import OpenRouter models, using default pricing")
            INPUT_COST_PER_1M = 3.0
            OUTPUT_COST_PER_1M = 15.0
    else:
        # Unknown provider - use DeepSeek pricing as default
        logger.warning(f"Unknown provider {provider}, using DeepSeek pricing")
        INPUT_COST_PER_1M = 0.28
        OUTPUT_COST_PER_1M = 0.42
    
    input_cost = (input_tokens / 1_000_000) * INPUT_COST_PER_1M
    output_cost = (output_tokens / 1_000_000) * OUTPUT_COST_PER_1M
    
    return input_cost, output_cost


def calculate_deepseek_cost(input_tokens: int, output_tokens: int) -> Tuple[float, float]:
    """Calculate cost for DeepSeek API usage (legacy function for backward compatibility).
    
    Args:
        input_tokens: Number of input (prompt) tokens.
        output_tokens: Number of output (completion) tokens.
    
    Returns:
        Tuple of (input_cost, output_cost) in USD.
    """
    return calculate_cost(input_tokens, output_tokens, provider="deepseek")


def extract_usage_from_response(response: Dict[str, Any]) -> Optional[tuple[int, int]]:
    """
    Extract usage information from API response (supports DeepSeek and OpenRouter formats).
    
    Args:
        response: API response dictionary
    
    Returns:
        Tuple of (input_tokens, output_tokens) or None if not found
    """
    try:
        if "usage" in response:
            usage = response["usage"]
            # Both DeepSeek and OpenRouter use prompt_tokens and completion_tokens
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            return input_tokens, output_tokens
    except Exception as e:
        logger.warning(f"Failed to extract usage from response: {e}")
    
    return None


def track_usage(
    model_name: Optional[str] = None,
    provider: Optional[str] = "deepseek",
    section: Optional[str] = None,
):
    """
    Decorator for tracking LLM API usage and costs.
    
    Intercepts API calls, extracts token usage information,
    calculates costs, and adds to the global usage report.
    
    Example usage:
    
        @track_usage(model_name="deepseek-chat", section="Requirements Extraction")
        def extract_requirements(self, text: str) -> dict:
            response = self.api_call(text)
            return response
    
    Args:
        model_name: Model name (e.g., "deepseek-chat").
                   If None, uses self.model_name from instance.
        provider: Provider name (default: "deepseek").
                 If None, uses self.provider from instance.
        section: Section name for grouping in reports.
                If None, uses self.section from instance.
    
    Returns:
        Decorated function that tracks usage.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Execute the original function
            result = func(*args, **kwargs)
            
            try:
                # Get parameters from decorator or instance
                _model_name = model_name or getattr(args[0], "model_name", "unknown")
                _provider = provider or getattr(args[0], "provider", "deepseek")
                _section = section or getattr(args[0], "current_section", None)
                
                # Extract usage from result (assuming it's a dict with usage info)
                usage = extract_usage_from_response(result)
                
                if usage is None:
                    logger.debug("No usage information found in response")
                    return result
                
                input_tokens, output_tokens = usage
                
                # Calculate costs based on provider
                input_cost, output_cost = calculate_cost(
                    input_tokens, 
                    output_tokens,
                    provider=_provider,
                    model_name=_model_name
                )
                
                # Create usage stats
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
                
                # Add to global report
                _usage_report.add_call(stats)
                
                # Log usage
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
