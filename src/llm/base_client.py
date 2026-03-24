"""Abstract base class for LLM API clients used in requirements extraction."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from src.models import Requirement


class BaseLLMClient(ABC):
    """Abstract base for LLM clients that extract requirements from text and optionally images."""

    @abstractmethod
    def extract_requirements(
        self,
        section_number: str,
        section_title: str,
        page_range: str,
        section_text: str,
    ) -> List[Requirement]:
        """Extract requirements from section text."""
        ...

    def extract_requirements_from_image(
        self,
        image_path: Path,
        page_number: int,
        section_number: str,
        section_title: str,
    ) -> List[Requirement]:
        """Extract requirements from an image. Override in clients that support vision.

        Default implementation returns empty list (image extraction not supported).
        """
        return []
