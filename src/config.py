"""Configuration management for the PDF requirements extractor.

This module provides dataclass-based configuration management with validation
and automatic directory creation. Loads settings from environment variables
and provides defaults for all configuration parameters.

Classes:
    DeepSeekConfig: Configuration for DeepSeek API client.
    PDFProcessorConfig: Configuration for PDF text extraction.
    ApplicationConfig: Main application configuration aggregating all settings.

Functions:
    get_config: Factory function for creating configuration instances.
"""

# Standard library imports
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Third-party imports
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class OpenRouterConfig:
    """Configuration for OpenRouter API integration.
    
    Attributes:
        api_key: OpenRouter API key
        api_url: OpenRouter API endpoint
        model: Selected model ID
        referer: Referer URL for OpenRouter
        title: Application title for OpenRouter
        temperature: Temperature parameter
        max_tokens: Maximum tokens in response
    """
    api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    api_url: str = "https://openrouter.ai/api/v1/chat/completions"
    model: str = field(default_factory=lambda: os.getenv("MODEL", "claude-sonnet-4.5"))
    referer: Optional[str] = field(default_factory=lambda: os.getenv("OPENROUTER_REFERER"))
    title: Optional[str] = field(default_factory=lambda: os.getenv("OPENROUTER_TITLE"))
    temperature: float = 0.1
    max_tokens: int = 4000


@dataclass
class DeepSeekConfig:
    """Configuration for DeepSeek API client (legacy, deprecated).
    
    Loads API credentials from environment variables and provides
    default values for model parameters.
    
    Note: This is legacy support. OpenRouter is recommended instead.
    Validation of API key happens only when DeepSeek is actually used.
    
    Attributes:
        api_key: DeepSeek API key from environment (optional if not using DeepSeek).
        base_url: Base URL for DeepSeek API.
        model: Model name to use for completions.
        temperature: Sampling temperature (0-1).
        max_tokens: Maximum tokens per completion.
        timeout: Request timeout in seconds.
    """
    
    api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 8192
    timeout: int = 120
    max_concurrent_requests: int = 5  # Parallel API calls limit
    
    def __post_init__(self) -> None:
        """Validate configuration after initialization.
        
        Note: Validation is skipped if DeepSeek is not the active provider.
        This allows the config to exist without a key when using OpenRouter.
        """
        # Validation is done at runtime when DeepSeek is actually used
        # Don't validate here to allow config creation without key
        pass


@dataclass
class PDFProcessorConfig:
    """Configuration for PDF processing and text extraction.
    
    Controls how PDFs are processed and converted to text/markdown.
    
    Attributes:
        dpi: Image resolution for PDF rendering.
        write_images: Whether to extract and save images from PDF.
        image_format: Format for extracted images (png, jpg, etc).
        page_chunks: Whether to process PDF in page chunks.
        show_progress: Whether to show extraction progress.
        max_workers: Maximum number of worker threads for parallel processing.
            If None, uses min(32, cpu_count + 4) as default.
    """
    
    dpi: int = 200
    write_images: bool = True
    image_format: str = "png"
    page_chunks: bool = True
    show_progress: bool = True
    max_workers: Optional[int] = None  # Auto-detect if None


@dataclass
class ApplicationConfig:
    """Main application configuration.
    
    Aggregates all configuration settings and provides path management
    with automatic directory creation.
    
    Attributes:
        pdf_path: Path to input PDF file.
        output_dir: Directory for output files.
        image_dir: Directory for extracted images.
        logs_dir: Directory for log files.
        deepseek: DeepSeek API configuration.
        pdf_processor: PDF processing configuration.
        registry_filename: Filename for requirements registry JSON.
        toc_filename: Filename for table of contents JSON.
    """
    
    # Paths
    pdf_path: Path = Path("data/input/specification.pdf")
    output_dir: Path = Path("data/output")
    image_dir: Path = Path("data/images")
    logs_dir: Path = Path("logs")
    
    # API Configuration
    deepseek: DeepSeekConfig = field(default_factory=DeepSeekConfig)
    openrouter: OpenRouterConfig = field(default_factory=OpenRouterConfig)
    provider: str = field(default_factory=lambda: os.getenv("PROVIDER", "openrouter").lower())
    
    # PDF Processing
    pdf_processor: PDFProcessorConfig = field(default_factory=PDFProcessorConfig)
    
    # Output files
    registry_filename: str = "requirements_registry.json"
    toc_filename: str = "table_of_contents.json"
    
    def __post_init__(self) -> None:
        """Create necessary directories if they don't exist.
        
        Creates all required directories (output, images, logs, input)
        with parent directories as needed.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_path.parent.mkdir(parents=True, exist_ok=True)
    
    @property
    def registry_path(self) -> Path:
        """Get full path to requirements registry output file.
        
        Returns:
            Path to the requirements registry JSON file.
        """
        return self.output_dir / self.registry_filename
    
    @property
    def toc_path(self) -> Path:
        """Get full path to table of contents output file.
        
        Returns:
            Path to the table of contents JSON file.
        """
        return self.output_dir / self.toc_filename


def get_config() -> ApplicationConfig:
    """Factory function for creating application configuration.
    
    Creates and returns a new ApplicationConfig instance with default
    values and environment-based settings.
    
    Returns:
        ApplicationConfig: Fully configured application config instance.
        
    Raises:
        ValueError: If required environment variables are missing.
    """
    return ApplicationConfig()


def load_from_env() -> ApplicationConfig:
    """Load configuration from environment variables.
    
    Environment variables:
        OPENROUTER_API_KEY: OpenRouter API key (required for openrouter provider)
        DEEPSEEK_API_KEY: DeepSeek API key (required for deepseek provider)
        OPENROUTER_REFERER: Referer for OpenRouter
        OPENROUTER_TITLE: Title for OpenRouter
        PROVIDER: AI provider ("openrouter" or "deepseek")
        MODEL: Default model to use
        LOG_LEVEL: Logging level
        
    Returns:
        ApplicationConfig instance with loaded values
    """
    config = ApplicationConfig()
    
    # Provider selection
    config.provider = os.getenv("PROVIDER", "openrouter").lower()
    
    # Model selection
    if os.getenv("MODEL"):
        config.openrouter.model = os.getenv("MODEL")
    
    return config
