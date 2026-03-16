"""Usage tracking data models."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class UsageStats:
    """Statistics for a single LLM API call."""

    timestamp: Any  # datetime
    model_name: str
    provider: str
    section: Optional[str]
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def total_cost(self) -> float:
        return self.input_cost + self.output_cost


@dataclass
class UsageReport:
    """Complete usage report aggregating multiple API calls."""

    calls: List[UsageStats] = field(default_factory=list)

    def add_call(self, stats: UsageStats) -> None:
        self.calls.append(stats)

    @property
    def total_input_tokens(self) -> int:
        return sum(call.input_tokens for call in self.calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(call.output_tokens for call in self.calls)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def total_cost(self) -> float:
        return sum(call.total_cost for call in self.calls)

    @property
    def calls_count(self) -> int:
        return len(self.calls)

    def get_stats_by_section(self) -> Dict[str, Dict[str, Any]]:
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
        import logging
        logger = logging.getLogger(__name__)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        if provider_name is None:
            if self.calls:
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
