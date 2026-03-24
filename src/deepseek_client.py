"""DeepSeek API client for requirements extraction.

This module provides a synchronous client for interacting with DeepSeek's
chat completion API to parse table of contents and extract requirements from
technical documents.

Classes:
    DeepSeekAPIError: Custom exception for API errors.
    DeepSeekClient: Synchronous client for API interactions with retry logic.

Features:
    - Automatic retry with exponential backoff
    - Usage tracking via decorator
    - JSON parsing with error recovery
    - Context manager support
"""

# Standard library imports
import json
import time
from typing import Any, Dict, List, Optional

# Third-party imports
import httpx

# Local imports
from src.llm.base_client import BaseLLMClient
from .config import DeepSeekConfig
from .logger import get_logger
from .models import (
    Requirement,
    RequirementPriority,
    RequirementType,
    TableOfContentsEntry,
)
from .usage_tracker import track_usage

logger = get_logger(__name__)


class DeepSeekAPIError(Exception):
    """Custom exception for DeepSeek API errors.
    
    Raised when API requests fail after all retry attempts or when
    response parsing fails.
    """
    pass


class DeepSeekClient(BaseLLMClient):
    """Client for interacting with DeepSeek chat completion API.
    
    Provides methods for parsing table of contents and extracting requirements
    from technical specification documents using AI. Includes automatic retry
    logic, rate limit handling, and usage tracking.
    
    Attributes:
        config: DeepSeek API configuration.
        base_url: Base API URL with version.
        headers: HTTP headers including authorization.
        client: HTTP client instance.
        model_name: Model name for tracking.
        provider: Provider name for tracking.
        current_section: Current section being processed (for usage tracking).
    
    Example:
        >>> config = DeepSeekConfig()
        >>> with DeepSeekClient(config) as client:
        ...     toc = client.parse_table_of_contents(toc_text)
        ...     reqs = client.extract_requirements("1.1", "Title", "1-5", text)
    """
    
    def __init__(self, config: DeepSeekConfig) -> None:
        """Initialize DeepSeek API client.
        
        Args:
            config: DeepSeek configuration with API key and parameters.
        """
        self.config = config
        self.base_url = f"{config.base_url}/v1"
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        self.client = httpx.Client(timeout=config.timeout)
        self.model_name = config.model
        self.provider = "deepseek"
        self.current_section: Optional[str] = None  # Set before each call for tracking
    
    def __enter__(self) -> 'DeepSeekClient':
        """Context manager entry.
        
        Returns:
            Self for use in with statement.
        """
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - closes HTTP client.
        
        Args:
            exc_type: Exception type if raised.
            exc_val: Exception value if raised.
            exc_tb: Exception traceback if raised.
        """
        self.client.close()
    
    @track_usage()
    def _make_request(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> Dict[str, Any]:
        """Make API request to DeepSeek with automatic retry.
        
        Sends chat completion request with retry logic for transient errors.
        Handles rate limits (429) and server errors (5xx) with exponential backoff.
        Decorated with @track_usage for token and cost tracking.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'.
            temperature: Sampling temperature (0-1). If None, uses config default.
            max_tokens: Maximum tokens in response. If None, uses config default.
            retry_count: Number of retry attempts on failure.
            retry_delay: Base delay in seconds between retries (exponential backoff).
        
        Returns:
            Full API response dictionary including:
                - choices: List with completion message
                - usage: Token usage statistics
        
        Raises:
            DeepSeekAPIError: If request fails after all retry attempts.
        """
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        
        last_error: Optional[Exception] = None
        for attempt in range(retry_count):
            try:
                logger.debug(f"Making API request (attempt {attempt + 1}/{retry_count})")
                response = self.client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                
                data = response.json()
                
                logger.debug("API request successful")
                return data  # Return full response with usage info
            
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"HTTP error on attempt {attempt + 1}: {e.response.status_code} - {e.response.text}"
                )
                if e.response.status_code == 429:  # Rate limit
                    time.sleep(retry_delay * (attempt + 1) * 2)
                elif e.response.status_code >= 500:  # Server error
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    break  # Don't retry on client errors (4xx)
            
            except (httpx.RequestError, json.JSONDecodeError) as e:
                last_error = e
                logger.warning(f"Request error on attempt {attempt + 1}: {str(e)}")
                time.sleep(retry_delay * (attempt + 1))
        
        error_msg = f"Failed to get response from DeepSeek API after {retry_count} attempts: {last_error}"
        logger.error(error_msg)
        raise DeepSeekAPIError(error_msg)
    
    def parse_table_of_contents(self, toc_text: str) -> List[TableOfContentsEntry]:
        """Parse table of contents from raw extracted text using AI.
        
        Sends the raw TOC text to DeepSeek API for intelligent parsing,
        cleaning, and structuring. Handles messy PDF extractions with tables,
        page numbers, and formatting issues.
        
        Args:
            toc_text: Raw table of contents text extracted from PDF.
        
        Returns:
            List of TableOfContentsEntry instances with hierarchical structure.
            
        Raises:
            DeepSeekAPIError: If API fails or returns invalid JSON.
            
        Example:
            >>> toc_text = "1. Introduction ... 5\\n1.1 Purpose ... 5"
            >>> entries = client.parse_table_of_contents(toc_text)
            >>> print(entries[0].title)
            'Introduction'
        """
        logger.info("Parsing table of contents with DeepSeek API")
        self.current_section = "TOC Parsing"
        
        system_prompt = """Ты — эксперт по разбору технических заданий на русском языке.
У меня есть грязное оглавление из PDF (скопировано из таблицы).

Задача:
1. Очисти весь мусор (таблицы, инв.№, подписи и т.д.).
2. Построй иерархическую структуру.
3. Для каждого раздела укажи page_start (номер страницы начала).
4. Верни ТОЛЬКО валидный JSON в таком формате:

{
  "toc": [
    {
      "level": 1,
      "number": "1",
      "title": "Общие положения",
      "page_start": 4,
      "children": []
    },
    {
      "level": 2,
      "number": "1.1",
      "title": "Назначение документа",
      "page_start": 4,
      "children": []
    }
  ]
}

Будь максимально точен с номерами страниц. Не добавляй ничего лишнего. Верни ТОЛЬКО JSON, без пояснений."""
        
        user_prompt = f"""Вот грязное оглавление:
```
{toc_text}
```

Выполни задачу. Верни ТОЛЬКО JSON."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response_data = self._make_request(messages, temperature=0.3, max_tokens=4096)
        
        # Extract content from response
        content = response_data["choices"][0]["message"]["content"]
        
        # Extract JSON from response (in case there's extra text)
        try:
            # Try to find JSON in the content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                data = json.loads(json_str)
            else:
                data = json.loads(content)
            
            toc_entries = []
            for entry in data.get("toc", []):
                toc_entries.append(
                    TableOfContentsEntry(
                        level=entry["level"],
                        number=entry["number"],
                        title=entry["title"],
                        page_start=entry["page_start"],
                        children=[],
                    )
                )
            
            logger.info(f"Successfully parsed {len(toc_entries)} TOC entries")
            return toc_entries
        
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse TOC response: {e}")
            logger.debug(f"Response was: {content}")
            raise DeepSeekAPIError(f"Invalid JSON response from API: {e}")
    
    def extract_requirements(
        self,
        section_number: str,
        section_title: str,
        page_range: str,
        section_text: str,
    ) -> List[Requirement]:
        """Extract requirements from a document section using AI.
        
        Analyzes section text and identifies all requirements with proper
        classification, priority, and references. Automatically truncates
        very long sections to fit within API limits.
        
        Args:
            section_number: Section number/identifier (e.g., '1.2', '3.1.4').
            section_title: Human-readable section title.
            page_range: Page range string for reference (e.g., '5-8', '12-end').
            section_text: Full text content of the section to analyze.
        
        Returns:
            List of Requirement instances extracted from the section.
            Returns empty list if parsing fails (to allow processing to continue).
            
        Note:
            Long sections (>12000 chars) are automatically truncated to prevent
            API token limits. A truncation notice is added to the text.
            
        Example:
            >>> reqs = client.extract_requirements(
            ...     "1.1", "System Requirements", "5-8",
            ...     "The system must support 100 concurrent users..."
            ... )
            >>> print(reqs[0].text)
            'The system must support 100 concurrent users'
        """
        logger.info(f"Extracting requirements from section {section_number} {section_title}")
        self.current_section = f"{section_number} {section_title}"
        
        # Truncate text if too long (keep first 12000 chars)
        if len(section_text) > 12000:
            section_text = section_text[:12000] + "\n\n[...текст обрезан...]"
        
        system_prompt = f"""Ты — эксперт по извлечению требований из технических заданий.
Извлеки ВСЕ требования из следующего раздела ТЗ.

Раздел: {section_number} {section_title}
Страницы: {page_range}

Верни ТОЛЬКО валидный JSON в таком формате:
{{
  "requirements": [
    {{
      "id": "REQ-{section_number.replace('.', '')}-001",
      "text": "полный текст требования без сокращений",
      "type": "Техническое",
      "priority": "Обязательно",
      "reference": "ГОСТ 12345 или ссылка из текста или null"
    }}
  ]
}}

Типы требований: "Техническое", "Организационное", "Документационное", "Функциональное", "Нефункциональное", "Прочее"
Приоритеты: "Обязательно", "Желательно", "Опционально"

Извлекай ВСЕ требования, даже небольшие. Не пропускай детали.
Верни ТОЛЬКО JSON, без пояснений."""
        
        user_prompt = f"""Текст раздела:
```
{section_text}
```

Извлеки все требования из этого раздела."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response_data = self._make_request(messages, temperature=0.5, max_tokens=8192)
        
        # Extract content from response
        content = response_data["choices"][0]["message"]["content"]
        
        # Parse response
        try:
            # Extract JSON from content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                data = json.loads(json_str)
            else:
                data = json.loads(content)
            
            requirements = []
            for req_data in data.get("requirements", []):
                try:
                    # Map string type to enum
                    req_type = RequirementType.OTHER
                    type_str = req_data.get("type", "")
                    for rt in RequirementType:
                        if rt.value in type_str:
                            req_type = rt
                            break
                    
                    # Map string priority to enum
                    priority = RequirementPriority.MANDATORY
                    priority_str = req_data.get("priority", "")
                    for rp in RequirementPriority:
                        if rp.value in priority_str:
                            priority = rp
                            break
                    
                    requirement = Requirement(
                        id=req_data["id"],
                        text=req_data["text"],
                        type=req_type,
                        priority=priority,
                        reference=req_data.get("reference"),
                        section=f"{section_number} {section_title}",
                    )
                    requirements.append(requirement)
                except (KeyError, ValueError) as e:
                    logger.warning(f"Skipping invalid requirement: {e}")
                    continue
            
            logger.info(f"Successfully extracted {len(requirements)} requirements")
            return requirements
        
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse requirements response: {e}")
            logger.debug(f"Response was: {content}")
            # Return empty list instead of raising to allow processing to continue
            return []
