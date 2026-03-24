"""OpenRouter client for accessing multiple AI models with image support.

This module provides a unified interface for accessing various AI models
through OpenRouter API, including multimodal capabilities for image analysis.
"""

import base64
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.llm.base_client import BaseLLMClient
from .config import OpenRouterConfig
from .models import Requirement, RequirementType, RequirementPriority
from .usage_tracker import get_usage_report, extract_usage_from_response, calculate_cost, UsageStats
from .prompts import get_prompt_loader
from src.llm.json_utils import parse_json_safely
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about an available AI model."""
    name: str
    route: str
    description: str
    price_input: float  # Per 1M tokens
    price_output: float  # Per 1M tokens
    max_context: int
    speed: str  # fast, balanced, slow
    capability: str  # primary focus
    supports_images: bool = True  # Most OpenRouter models support images


# Type and priority mappings shared across extraction methods
TYPE_MAPPING: Dict[str, "RequirementType"] = {
    # English values (from v2.1+ prompts)
    "Supply": None,  # filled below after class import
    "Technical": None,
    "Functional": None,
    "Performance": None,
    "Safety": None,
    "Documentation": None,
    "Interface": None,
    "Constraint": None,
    "Process": None,
    "Unknown": None,
    # Russian values (backward compatibility)
    "Техническое": None,
    "Организационное": None,
    "Документационное": None,
    "Функциональное": None,
    "Нефункциональное": None,
    "Прочее": None,
}

PRIORITY_MAPPING: Dict[str, "RequirementPriority"] = {
    # English values
    "Mandatory": None,
    "Recommended": None,
    "Optional": None,
    "Unknown": None,
    # Russian values (backward compatibility)
    "Обязательно": None,
    "Желательно": None,
    "Опционально": None,
}


def _build_mappings() -> None:
    """Populate TYPE_MAPPING and PRIORITY_MAPPING after models are imported."""
    TYPE_MAPPING.update({
        "Supply": RequirementType.SUPPLY,
        "Technical": RequirementType.TECHNICAL,
        "Functional": RequirementType.FUNCTIONAL,
        "Performance": RequirementType.PERFORMANCE,
        "Safety": RequirementType.SAFETY,
        "Documentation": RequirementType.DOCUMENTATION,
        "Interface": RequirementType.INTERFACE,
        "Constraint": RequirementType.CONSTRAINT,
        "Process": RequirementType.PROCESS,
        "Unknown": RequirementType.UNKNOWN,
        "Техническое": RequirementType.TECHNICAL,
        "Организационное": RequirementType.PROCESS,
        "Документационное": RequirementType.DOCUMENTATION,
        "Функциональное": RequirementType.FUNCTIONAL,
        "Нефункциональное": RequirementType.CONSTRAINT,
        "Прочее": RequirementType.UNKNOWN,
    })
    PRIORITY_MAPPING.update({
        "Mandatory": RequirementPriority.MANDATORY,
        "Recommended": RequirementPriority.RECOMMENDED,
        "Optional": RequirementPriority.OPTIONAL,
        "Unknown": RequirementPriority.UNKNOWN,
        "Обязательно": RequirementPriority.MANDATORY,
        "Желательно": RequirementPriority.RECOMMENDED,
        "Опционально": RequirementPriority.OPTIONAL,
    })


_build_mappings()


# Available models configuration
AVAILABLE_MODELS = {
    "claude-opus-4.6": ModelInfo(
        name="Claude Opus 4.6",
        route="anthropic/claude-opus-4.6",
        description="Most advanced Claude model for coding and long-running professional tasks",
        price_input=5.0,
        price_output=25.0,
        max_context=1_000_000,
        speed="slow",
        capability="Complex coding and multi-step workflows",
        supports_images=True
    ),
    "gemini-3.1-pro": ModelInfo(
        name="Gemini 3.1 Pro Preview",
        route="google/gemini-3.1-pro-preview",
        description="Google's flagship model with 1M context window",
        price_input=2.0,
        price_output=12.0,
        max_context=1_048_576,
        speed="balanced",
        capability="Multimodal reasoning and software engineering",
        supports_images=True
    ),
    "claude-sonnet-4.5": ModelInfo(
        name="Claude Sonnet 4.5",
        route="anthropic/claude-sonnet-4.5",
        description="Most advanced Sonnet model for real-world agents and coding workflows",
        price_input=3.0,
        price_output=15.0,
        max_context=1_000_000,
        speed="fast",
        capability="Coding workflows and agent systems",
        supports_images=True
    ),
    "gpt-4.1": ModelInfo(
        name="GPT-4.1",
        route="openai/gpt-4.1",
        description="OpenAI's flagship model optimized for advanced instruction following",
        price_input=2.0,
        price_output=8.0,
        max_context=1_047_576,
        speed="balanced",
        capability="Software engineering and long-context reasoning",
        supports_images=True
    ),
    "qwen-3.5-plus": ModelInfo(
        name="Qwen3.5 Plus 2026-02-15",
        route="qwen/qwen3.5-plus-02-15",
        description="Efficient model with hybrid architecture",
        price_input=0.4,
        price_output=2.4,
        max_context=1_000_000,
        speed="fast",
        capability="Cost-effective general tasks",
        supports_images=True
    )
}


class OpenRouterClient(BaseLLMClient):
    """Client for OpenRouter API with multiple model support and image analysis."""
    
    def __init__(self, config: OpenRouterConfig):
        """Initialize OpenRouter client.
        
        Args:
            config: OpenRouter configuration with API settings
        """
        self.config = config
        self.selected_model = config.model if config.model in AVAILABLE_MODELS else "claude-sonnet-4.5"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "HTTP-Referer": config.referer or "",
            "X-Title": config.title or "Requirements Management System",
            "Content-Type": "application/json"
        })
        
        logger.info(f"OpenRouter client initialized with model: {self.selected_model}")
    
    def set_model(self, model_id: str) -> None:
        """Change the current AI model.
        
        Args:
            model_id: Model identifier from AVAILABLE_MODELS
            
        Raises:
            ValueError: If model_id is not available
        """
        if model_id not in AVAILABLE_MODELS:
            raise ValueError(f"Model {model_id} not in available models: {list(AVAILABLE_MODELS.keys())}")
        
        self.selected_model = model_id
        logger.info(f"Model changed to: {AVAILABLE_MODELS[model_id].name}")
    
    def _encode_image(self, image_path: Path) -> str:
        """Encode image to base64 for API.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string with data URI prefix
        """
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Determine MIME type from extension
            ext = image_path.suffix.lower()
            mime_types = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_types.get(ext, 'image/png')
            
            return f"data:{mime_type};base64,{base64_image}"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _make_request(self, messages: List[Dict[str, Any]], section: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Make API request to OpenRouter with retry logic.
        
        Args:
            messages: List of conversation messages (can include images)
            section: Optional section identifier for usage tracking
            **kwargs: Additional request parameters
            
        Returns:
            API response data
            
        Raises:
            requests.RequestException: For API errors
        """
        payload = {
            "model": AVAILABLE_MODELS[self.selected_model].route,
            "messages": messages,
            "stream": False,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 4000)
        }
        
        response = self.session.post(self.config.api_url, json=payload, timeout=120)
        response.raise_for_status()
        
        response_data = response.json()
        
        # Track usage
        try:
            usage = extract_usage_from_response(response_data)
            if usage:
                input_tokens, output_tokens = usage
                input_cost, output_cost = calculate_cost(
                    input_tokens,
                    output_tokens,
                    provider="openrouter",
                    model_name=self.selected_model
                )
                
                stats = UsageStats(
                    timestamp=datetime.now(),
                    model_name=AVAILABLE_MODELS[self.selected_model].name,
                    provider="openrouter",
                    section=section,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    input_cost=input_cost,
                    output_cost=output_cost,
                )
                
                get_usage_report().add_call(stats)
                
                logger.debug(
                    f"API Call [{section or 'N/A'}]: "
                    f"Input={input_tokens:,} tokens, "
                    f"Output={output_tokens:,} tokens, "
                    f"Cost=${stats.total_cost:.6f}"
                )
        except Exception as e:
            logger.warning(f"Failed to track usage: {e}")
        
        return response_data
    
    def extract_requirements_from_image(
        self,
        image_path: Path,
        page_number: int,
        section_number: str,
        section_title: str
    ) -> List[Requirement]:
        """Extract requirements from an image using vision capabilities.
        
        Args:
            image_path: Path to image file
            page_number: Page number where image is located (1-based)
            section_number: Section identifier (e.g., '3.2.1')
            section_title: Section title
            
        Returns:
            List of extracted Requirement objects from the image
        """
        if not image_path.exists():
            logger.warning(f"Image file not found: {image_path}")
            return []
        
        logger.info(f"[IMAGE] Starting extraction from image: {image_path.name} (page {page_number}, section {section_number})")
        
        # Encode image
        try:
            image_data_uri = self._encode_image(image_path)
            logger.debug(f"[IMAGE] Image encoded successfully, size: {len(image_data_uri)} chars")
        except Exception as e:
            logger.error(f"[IMAGE] Failed to encode image {image_path}: {e}")
            return []
        
        # Load prompt from YAML
        try:
            prompt_loader = get_prompt_loader()
            system_message, user_prompt_template = prompt_loader.format_prompt(
                "requirement_extractor_image",
                section_number=section_number,
                section_title=section_title,
                page_number=page_number
            )
            logger.debug(f"[IMAGE] Loaded prompt template from YAML")
        except Exception as e:
            logger.warning(f"[IMAGE] Failed to load prompt from YAML: {e}, using default")
            # Fallback to default prompt
            system_message = "Ты — эксперт по извлечению требований из технических заданий. Извлеки ВСЕ требования из изображения."
            user_prompt_template = f"""Раздел: {section_number} {section_title}
Страница: {page_number}

ВНИМАНИЕ: Это изображение из технического задания.

Извлеки все требования из этого изображения."""
        
        messages = [
            {"role": "system", "content": system_message},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt_template
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_uri
                        }
                    }
                ]
            }
        ]
        
        logger.info(f"[IMAGE] Sending image to AI model: {self.selected_model}")
        logger.debug(f"[IMAGE] System message length: {len(system_message)} chars")
        logger.debug(f"[IMAGE] User prompt length: {len(user_prompt_template)} chars")
        
        try:
            response = self._make_request(messages, section=f"{section_number} - {section_title} (image)", temperature=0.1)  # CHANGED from 0.7
            
            # Parse response
            content = response["choices"][0]["message"]["content"]
            logger.info(f"[IMAGE] Received response from AI, length: {len(content)} chars")
            logger.debug(f"[IMAGE] Response preview (first 500 chars): {content[:500]}")
            
            # Extract JSON array with safe parsing
            parsed_data = parse_json_safely(content, context=f"image extraction for section {section_number}")
            logger.info(f"[IMAGE] Parsed JSON successfully, got {len(parsed_data) if isinstance(parsed_data, list) else 1} items")
            
            # Handle both list and dict formats
            if isinstance(parsed_data, list):
                requirements_data = parsed_data
            elif isinstance(parsed_data, dict) and "requirements" in parsed_data:
                requirements_data = parsed_data["requirements"]
            else:
                requirements_data = []
            
            # Convert to Requirement objects
            requirements = []
            for item in requirements_data:
                type_str = item.get("requirement_kind", item.get("type", "Unknown"))
                req_type = TYPE_MAPPING.get(type_str, RequirementType.UNKNOWN)
                priority_str = item.get("priority", "Unknown")
                req_priority = PRIORITY_MAPPING.get(priority_str, RequirementPriority.UNKNOWN)
                
                raw_discipline = item.get("suggested_discipline")
                req = Requirement(
                    id=item.get("temp_id", item.get("id", f"REQ-{section_number.replace('.', '')}-IMG-XXX")),
                    text=item.get("text", ""),
                    type=req_type,
                    priority=req_priority,
                    source_page=page_number,
                    section_number=section_number,
                    source_type="image",
                    subitems=item.get("subitems", []),
                    source_quote=item.get("source_quote"),
                    source_fragment=item.get("source_fragment"),
                    visual_requirement_class=item.get("visual_requirement_class"),
                    confidence=float(item.get("confidence", 0.8)),
                    extraction_basis=item.get("extraction_basis", "image_text"),
                    suggested_discipline=raw_discipline if raw_discipline and str(raw_discipline).lower() != "null" else None,
                )
                requirements.append(req)
            
            logger.info(f"[IMAGE] Successfully extracted {len(requirements)} requirements from image {image_path.name}")
            if requirements:
                logger.debug(f"[IMAGE] Requirement IDs: {[req.id for req in requirements]}")
            else:
                logger.warning(f"[IMAGE] No requirements extracted from image {image_path.name} - check AI response")
            return requirements
            
        except Exception as e:
            logger.error(f"[IMAGE] Failed to extract requirements from image {image_path.name} using {self.selected_model}: {e}")
            logger.exception(e)  # Full traceback for debugging
            return []
    
    def extract_requirements(self, section_number: str, section_title: str, 
                           page_range: str, section_text: str) -> List[Requirement]:
        """Extract requirements from section text using selected AI model.
        
        Args:
            section_number: Section identifier (e.g., '3.2.1')
            section_title: Section title
            page_range: Page range text (e.g., '15-25')
            section_text: Full text content of the section
            
        Returns:
            List of extracted Requirement objects
        """
        logger.info(f"[TEXT] Extracting requirements from section {section_number} using {self.selected_model}")
        
        # Limit text to avoid context window issues
        section_text_limited = section_text[:12000]
        logger.debug(f"[TEXT] Section text length: {len(section_text)} chars (limited to {len(section_text_limited)})")
        
        # Load prompt from YAML
        try:
            prompt_loader = get_prompt_loader()
            system_message, user_prompt_template = prompt_loader.format_prompt(
                "requirement_extractor_text",  # NEW prompt name
                section_number=section_number,
                section_title=section_title,
                page_range=page_range,
                section_text=section_text_limited
            )
            logger.debug(f"[TEXT] Loaded prompt template from YAML")
        except Exception as e:
            logger.warning(f"[TEXT] Failed to load prompt from YAML: {e}, using default")
            # Fallback to default prompt
            system_message = "Ты — эксперт по извлечению требований из технических заданий. Извлеки ВСЕ требования из следующего раздела ТЗ."
            user_prompt_template = f"""Раздел: {section_number} {section_title}
Страницы: {page_range}

Текст:
```
{section_text_limited}
```

Извлеки все требования."""
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt_template}
        ]
        
        logger.debug(f"[TEXT] System message length: {len(system_message)} chars")
        logger.debug(f"[TEXT] User prompt length: {len(user_prompt_template)} chars")
        
        # Retry logic for JSON parsing errors
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"[TEXT] Sending text to AI model: {self.selected_model} (attempt {attempt + 1}/{max_retries + 1})")
                response = self._make_request(messages, section=f"{section_number} - {section_title}", temperature=0.1)
                
                # Parse response
                content = response["choices"][0]["message"]["content"]
                logger.info(f"[TEXT] Received response from AI, length: {len(content)} chars")
                logger.debug(f"[TEXT] Response preview (first 500 chars): {content[:500]}")
                
                # Extract JSON array with safe parsing
                parsed_data = parse_json_safely(content, context=f"text extraction for section {section_number}")
                logger.info(f"[TEXT] Parsed JSON successfully, got {len(parsed_data) if isinstance(parsed_data, list) else 1} items")
                
                # If we got here, parsing succeeded - break retry loop
                break
                
            except (ValueError, json.JSONDecodeError) as json_error:
                if attempt < max_retries:
                    delay = 2 ** attempt  # Exponential backoff: 1s, 2s
                    logger.warning(f"[TEXT] JSON parse error on attempt {attempt + 1}: {json_error}. Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"[TEXT] Failed to parse JSON after {max_retries + 1} attempts: {json_error}")
                    logger.error(f"[TEXT] Raw response: {content[:1000]}")
                    return []
        
        # Handle both list and dict formats
        if isinstance(parsed_data, list):
            requirements_data = parsed_data
        elif isinstance(parsed_data, dict) and "requirements" in parsed_data:
            requirements_data = parsed_data["requirements"]
        else:
            requirements_data = []
        
        try:
            # Convert to Requirement objects
            requirements = []
            for item in requirements_data:
                type_str = item.get("requirement_kind", item.get("type", "Unknown"))
                req_type = TYPE_MAPPING.get(type_str, RequirementType.UNKNOWN)
                priority_str = item.get("priority", "Unknown")
                req_priority = PRIORITY_MAPPING.get(priority_str, RequirementPriority.UNKNOWN)
                
                raw_discipline = item.get("suggested_discipline")
                req = Requirement(
                    id=item.get("temp_id", item.get("id", f"REQ-{section_number.replace('.', '')}-XXX")),
                    text=item.get("text", ""),
                    type=req_type,
                    priority=req_priority,
                    source_page=None,  # Will be set by caller from page_start
                    section_number=section_number,
                    source_type="text",
                    subitems=item.get("subitems", []),
                    source_quote=item.get("source_quote"),
                    source_fragment=item.get("source_fragment"),
                    confidence=float(item.get("confidence", 1.0)),
                    extraction_basis=item.get("extraction_basis"),
                    suggested_discipline=raw_discipline if raw_discipline and str(raw_discipline).lower() != "null" else None,
                )
                requirements.append(req)
            
            logger.info(f"[TEXT] Successfully extracted {len(requirements)} requirements from section {section_number}")
            if requirements:
                logger.debug(f"[TEXT] Requirement IDs: {[req.id for req in requirements[:5]]}...")  # Show first 5
            else:
                logger.warning(f"[TEXT] No requirements extracted from section {section_number} - check AI response")
            return requirements
            
        except Exception as e:
            logger.error(f"[TEXT] Failed to extract requirements from section {section_number} using {self.selected_model}: {e}")
            logger.exception(e)  # Full traceback for debugging
            return []
    
    def __enter__(self) -> "OpenRouterClient":
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.session.close()


def get_available_models() -> Dict[str, ModelInfo]:
    """Get all available models."""
    return AVAILABLE_MODELS.copy()


def get_model_info(model_id: str) -> Optional[ModelInfo]:
    """Get information about a specific model."""
    return AVAILABLE_MODELS.get(model_id)