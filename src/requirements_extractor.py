"""Requirements extractor using OpenRouter client with image support.

This module provides the main extraction logic for processing PDF documents,
extracting requirements using AI models via OpenRouter, including requirements
from images.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Import OpenRouter client (primary)
from .openrouter_client import OpenRouterClient, get_available_models
# DeepSeek imported only if explicitly needed (legacy mode)
from .models import Section, RequirementsRegistry, Requirement, TableOfContentsEntry
from .config import ApplicationConfig
from .logger import get_logger

logger = get_logger(__name__)


class RequirementsExtractor:
    """Main extraction engine using AI models via OpenRouter or DeepSeek."""
    
    def __init__(self, config: ApplicationConfig):
        """Initialize extractor with configuration.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.registry = RequirementsRegistry()
        self.pages: List[str] = []
        self.toc_entries: List[TableOfContentsEntry] = []
        self.current_section: Optional[str] = None
        
        # Initialize PDF processor
        from .pdf_processor import PDFProcessor
        self.pdf_processor = PDFProcessor(config.pdf_processor)
        
        # Initialize AI client based on provider config
        self.ai_client = None
        self.ai_provider = config.provider.lower()
        
        # Track image metadata from PDF pages
        self.page_image_metadata: Dict[int, List[Dict]] = {}  # page_number -> list of image metadata
        
        logger.info(f"Requirements extractor initialized with {self.ai_provider}")
    
    def parse_table_of_contents(self, manual_toc: List[Dict[str, Any]] = None) -> None:
        """Parse table of contents from extracted pages or manual entries.
        
        Args:
            manual_toc: Manual TOC entries if automatic parsing fails
        """
        if manual_toc:
            logger.info("Using manual TOC entries")
            self.toc_entries = [
                TableOfContentsEntry(
                    level=entry["level"],
                    number=entry["number"],
                    title=entry["title"],
                    page_start=entry["page_start"]
                )
                for entry in manual_toc
                if entry.get("number") and entry.get("title")
            ]
        else:
            # For now, create default sections every 20 pages
            logger.info("Creating default TOC entries every 20 pages")
            total_pages = len(self.pages)
            sections_per_doc = max(1, total_pages // 20)  # ~20 pages per section
            
            self.toc_entries = []
            for i in range(0, total_pages, sections_per_doc):
                section_num = len(self.toc_entries) + 1
                self.toc_entries.append(TableOfContentsEntry(
                    level=1,
                    number=str(section_num),
                    title=f"Раздел {section_num} (стр. {i+1}-{min(i+sections_per_doc, total_pages)})",
                    page_start=i + 1
                ))
            
            logger.info(f"Created {len(self.toc_entries)} default TOC entries")
    
    def setup_ai_client(self, model_id: str = None) -> None:
        """Set up AI client with specified model.
        
        Args:
            model_id: Model identifier from AVAILABLE_MODELS (only for OpenRouter)
            
        Raises:
            ValueError: If provider is not supported or API key is missing
        """
        if self.ai_provider == "openrouter":
            if not self.config.openrouter.api_key:
                raise ValueError(
                    "OPENROUTER_API_KEY not found. Please set it in .env file or environment variables. "
                    "Get your key at: https://openrouter.ai/keys"
                )
            self.ai_client = OpenRouterClient(self.config.openrouter)
            if model_id:
                self.ai_client.set_model(model_id)
            logger.info(f"OpenRouter client set up with model: {self.ai_client.selected_model}")
        elif self.ai_provider == "deepseek":
            # Legacy DeepSeek support (only if explicitly set)
            from .deepseek_client import DeepSeekClient
            if not self.config.deepseek.api_key:
                raise ValueError(
                    "DEEPSEEK_API_KEY not found. Please set it in .env file or switch to OpenRouter."
                )
            self.ai_client = DeepSeekClient(self.config.deepseek)
            logger.info("DeepSeek client set up (legacy mode)")
        else:
            raise ValueError(
                f"Unknown provider: {self.ai_provider}. "
                "Supported providers: 'openrouter' (recommended) or 'deepseek' (legacy)"
            )
    
    def extract_requirements_from_images(
        self,
        toc_entry: TableOfContentsEntry,
        image_dir: Path
    ) -> List[Requirement]:
        """Extract requirements from images in a section.
        
        Args:
            toc_entry: Table of contents entry for the section
            image_dir: Directory containing extracted images
            
        Returns:
            List of Requirement objects extracted from images
        """
        if not self.ai_client:
            return []
        
        # Find end page
        end_page = None
        start_page = toc_entry.page_start
        for next_entry in self.toc_entries:
            if next_entry.page_start > start_page:
                end_page = next_entry.page_start
                break
        
        all_image_requirements = []
        
        # Process images for pages in this section
        for page_num in range(start_page, end_page or len(self.pages) + 1):
            if page_num in self.page_image_metadata:
                images = self.page_image_metadata[page_num]
                
                for img_meta in images:
                    image_path = Path(img_meta["path"])
                    
                    if not image_path.exists():
                        logger.warning(f"Image file not found: {image_path}")
                        continue
                    
                    logger.info(f"Extracting requirements from image: {image_path.name} (page {page_num})")
                    
                    # Extract requirements from this image
                    if hasattr(self.ai_client, 'extract_requirements_from_image'):
                        # OpenRouter client with image support
                        image_requirements = self.ai_client.extract_requirements_from_image(
                            image_path=image_path,
                            page_number=page_num,
                            section_number=toc_entry.number,
                            section_title=toc_entry.title
                        )
                        all_image_requirements.extend(image_requirements)
                    else:
                        # DeepSeek client doesn't support images yet
                        logger.debug(f"Skipping image extraction - client doesn't support images")
        
        logger.info(f"Extracted {len(all_image_requirements)} requirements from images in section {toc_entry.number}")
        return all_image_requirements
    
    def extract_requirements_from_section(self, toc_entry: TableOfContentsEntry, image_dir: Optional[Path] = None) -> Section:
        """Extract requirements from a specific section using AI (text + images).
        
        Args:
            toc_entry: Table of contents entry for the section
            image_dir: Directory containing extracted images (optional)
            
        Returns:
            Section object with extracted requirements from both text and images
        """
        if not self.ai_client:
            raise RuntimeError("AI client not configured. Call setup_ai_client() first.")
        
        # Find end page
        end_page = None
        start_page = toc_entry.page_start
        for next_entry in self.toc_entries:
            if next_entry.page_start > start_page:
                end_page = next_entry.page_start
                break
        
        # Get section text
        if hasattr(self, 'pdf_processor'):
            section_text = self.pdf_processor.get_section_text(
                self.pages, 
                start_page,
                end_page
            )
        else:
            # Fallback: manual extraction
            start_idx = start_page - 1
            if end_page:
                end_idx = end_page - 1
            else:
                end_idx = len(self.pages)
            
            section_pages = self.pages[start_idx:end_idx]
            section_text = "\n\n".join(section_pages)
        
        # Extract requirements from text
        text_requirements = self.ai_client.extract_requirements(
            section_number=toc_entry.number,
            section_title=toc_entry.title,
            page_range=f"{start_page}-{end_page-1 if end_page else 'end'}",
            section_text=section_text
        )
        
        # Set source page for each text requirement
        for req in text_requirements:
            req.source_page = start_page
            req.section_number = toc_entry.number
            req.source_type = "text"
        
        # Extract requirements from images if available
        image_requirements = []
        if image_dir and self.page_image_metadata:
            image_requirements = self.extract_requirements_from_images(toc_entry, image_dir)
        
        # Combine all requirements
        all_requirements = text_requirements + image_requirements
        
        # Create section object
        section = Section(
            number=toc_entry.number,
            title=toc_entry.title,
            page_start=start_page,
            page_end=end_page-1 if end_page else None,
            raw_text=section_text,
            requirements=all_requirements
        )
        
        # Store image metadata in section
        if self.page_image_metadata:
            for page_num in range(start_page, end_page or len(self.pages) + 1):
                if page_num in self.page_image_metadata:
                    section.images.extend(self.page_image_metadata[page_num])
        
        logger.info(f"Extracted {len(text_requirements)} text + {len(image_requirements)} image = {len(all_requirements)} total requirements from section {toc_entry.number}")
        return section
    
    def save_registry(self) -> Path:
        """Save requirements registry to JSON file.
        
        Returns:
            Path to saved registry file
        """
        if not self.config.output_dir:
            raise ValueError("Output directory not configured")
        
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        registry_path = self.config.output_dir / "requirements_registry.json"
        
        # Convert registry to dict
        registry_dict = {
            "total_requirements": self.registry.total_requirements,
            "sections": []
        }
        
        for section in self.registry.sections:
            section_dict = {
                "number": section.number,
                "title": section.title,
                "page_start": section.page_start,
                "page_end": section.page_end,
                "requirements": [req.to_dict() for req in section.requirements],
                "images": section.images if hasattr(section, 'images') else []
            }
            registry_dict["sections"].append(section_dict)
        
        # Save to file
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry_dict, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Registry saved to: {registry_path}")
        return registry_path


def create_extractor(config: ApplicationConfig, model_id: str = None) -> RequirementsExtractor:
    """Factory function to create a requirements extractor with specified settings.
    
    Args:
        config: Application configuration
        model_id: AI model to use (overrides config default)
        
    Returns:
        Configured RequirementsExtractor instance
    """
    extractor = RequirementsExtractor(config)
    extractor.setup_ai_client(model_id)
    return extractor