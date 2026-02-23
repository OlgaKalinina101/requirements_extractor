"""Prompt templates loaded from YAML configuration.

This module loads and manages prompt templates from prompts.yaml file.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Path to prompts.yaml file
PROMPTS_FILE = Path(__file__).parent / "prompts.yaml"


class PromptLoader:
    """Loads and manages prompt templates from YAML."""
    
    def __init__(self, prompts_file: Path = None):
        """Initialize prompt loader.
        
        Args:
            prompts_file: Path to prompts.yaml file. Defaults to src/prompts.yaml
        """
        self.prompts_file = prompts_file or PROMPTS_FILE
        self._prompts: Dict[str, Dict[str, Any]] = {}
        self._load_prompts()
    
    def _load_prompts(self) -> None:
        """Load prompts from YAML file."""
        try:
            if not self.prompts_file.exists():
                logger.warning(f"Prompts file not found: {self.prompts_file}")
                return
            
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                self._prompts = yaml.safe_load(f) or {}
            
            logger.info(f"Loaded {len(self._prompts)} prompt templates from {self.prompts_file}")
        except Exception as e:
            logger.error(f"Failed to load prompts from {self.prompts_file}: {e}")
            self._prompts = {}
    
    def get_prompt(self, name: str) -> Optional[Dict[str, Any]]:
        """Get prompt template by name.
        
        Args:
            name: Prompt template name (e.g., 'toc_parser', 'requirement_extractor')
            
        Returns:
            Dictionary with prompt configuration or None if not found
        """
        return self._prompts.get(name)
    
    def format_prompt(self, name: str, **kwargs) -> tuple[str, str]:
        """Format prompt template with provided variables.
        
        Args:
            name: Prompt template name
            **kwargs: Variables to substitute in template
            
        Returns:
            Tuple of (system_message, user_message)
            
        Raises:
            ValueError: If prompt template not found
        """
        prompt_config = self.get_prompt(name)
        if not prompt_config:
            raise ValueError(f"Prompt template '{name}' not found")
        
        system_template = prompt_config.get("system", "")
        user_template = prompt_config.get("user_template", "")
        
        # Format templates with provided kwargs
        try:
            system_message = system_template.format(**kwargs) if system_template else ""
            user_message = user_template.format(**kwargs) if user_template else ""
        except KeyError as e:
            logger.error(f"Missing variable {e} for prompt '{name}'")
            raise ValueError(f"Missing required variable {e} for prompt '{name}'")
        
        return system_message, user_message


# Global prompt loader instance
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader() -> PromptLoader:
    """Get global prompt loader instance."""
    global _prompt_loader
    if _prompt_loader is None:
        _prompt_loader = PromptLoader()
    return _prompt_loader


def reload_prompts() -> None:
    """Reload prompts from file."""
    global _prompt_loader
    _prompt_loader = PromptLoader()
