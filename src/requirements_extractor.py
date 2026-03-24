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

from .openrouter_client import get_available_models
from .models import RequirementsRegistry, Requirement, TableOfContentsEntry
from src.llm.factory import create_llm_client
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
        
        # Initialize PDF processor
        from .pdf_processor import PDFProcessor
        self.pdf_processor = PDFProcessor(config.pdf_processor)
        
        # Initialize AI client based on provider config
        self.ai_client = None
        self.ai_provider = config.provider.lower()
        
        # Track image metadata from PDF pages
        self.page_image_metadata: Dict[int, List[Dict]] = {}  # page_number -> list of image metadata
        
        logger.info(f"Requirements extractor initialized with {self.ai_provider}")
    
    def setup_ai_client(self, model_id: str = None) -> None:
        """Set up AI client with specified model.
        
        Args:
            model_id: Model identifier from AVAILABLE_MODELS (only for OpenRouter)
            
        Raises:
            ValueError: If provider is not supported or API key is missing
        """
        if self.ai_provider == "openrouter" and not self.config.openrouter.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not found. Please set it in .env file or environment variables. "
                "Get your key at: https://openrouter.ai/keys"
            )
        if self.ai_provider == "deepseek" and not self.config.deepseek.api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY not found. Please set it in .env file or switch to OpenRouter."
            )

        self.ai_client = create_llm_client(self.config)
        if model_id and hasattr(self.ai_client, "set_model"):
            self.ai_client.set_model(model_id)
        logger.info(
            f"{self.ai_provider} client set up"
            + (f" with model: {self.ai_client.selected_model}" if hasattr(self.ai_client, "selected_model") else "")
        )
    
    async def extract_requirements_from_all_pages(self, image_dir: Optional[Path] = None, batch_size: int = 7, progress_callback=None) -> List[Requirement]:
        """Extract requirements from ALL pages directly without TOC parsing.
        
        This is a simplified, faster approach that processes all pages in batches
        without needing to parse the table of contents first.
        
        Args:
            image_dir: Directory containing extracted images (optional)
            batch_size: Number of pages to process in parallel (default: 7)
            progress_callback: Callback function(page_num, total_pages, message) for progress updates
            
        Returns:
            List of all extracted requirements
        """
        if not self.ai_client:
            raise RuntimeError("AI client not configured. Call setup_ai_client() first.")
        
        # IMPORTANT: self.pages now contains dicts with structure: {page_number: int, text: str}
        total_pages = len(self.pages)
        logger.info(f"[EXTRACT] Processing {total_pages} pages in batches of {batch_size} (no TOC)")
        
        all_requirements = []
        
        # Process all pages in batches using their EXPLICIT page numbers
        for batch_start_idx in range(0, total_pages, batch_size):
            batch_end_idx = min(batch_start_idx + batch_size, total_pages)
            # Get page objects for this batch (not indices!)
            batch_page_objects = self.pages[batch_start_idx:batch_end_idx]
            
            # Extract page numbers for logging
            page_numbers = [p["page_number"] for p in batch_page_objects]
            logger.info(f"[EXTRACT] Processing batch: pages {page_numbers[0]}-{page_numbers[-1]} ({len(batch_page_objects)} pages)")
            
            # Process pages in this batch concurrently
            batch_requirements = await self._process_page_batch_simple(
                batch_page_objects,  # Pass page objects with explicit page_number
                image_dir,
                progress_callback,
                total_pages
            )
            
            all_requirements.extend(batch_requirements)
            logger.info(f"[EXTRACT] Batch complete: {len(batch_requirements)} requirements, total: {len(all_requirements)}")
        
        logger.info(f"[EXTRACT] All pages processed: extracted {len(all_requirements)} total requirements")
        return all_requirements
    
    async def _process_page_batch_simple(
        self,
        page_objects: List[Dict],  # CHANGED: now list of {page_number: int, text: str}
        image_dir: Optional[Path],
        progress_callback,
        total_pages: int
    ) -> List[Requirement]:
        """Process a batch of pages concurrently (simplified version without TOC).
        
        Args:
            page_objects: List of page dicts with {page_number: int, text: str}
            image_dir: Directory containing extracted images
            progress_callback: Progress callback function
            total_pages: Total pages in document for progress calculation
            
        Returns:
            List of requirements extracted from all pages in batch
        """
        import asyncio
        
        tasks = []
        for page_obj in page_objects:
            task = self._process_single_page_simple(
                page_obj,  # Pass page object with explicit page_number
                image_dir,
                progress_callback,
                total_pages
            )
            tasks.append(task)
        
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and filter out errors
        all_requirements = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error processing page: {result}")
            elif isinstance(result, list):
                all_requirements.extend(result)
        
        return all_requirements
    
    async def _process_single_page_simple(
        self,
        page_obj: Dict,  # CHANGED: now {page_number: int, text: str}
        image_dir: Optional[Path],
        progress_callback,
        total_pages: int
    ) -> List[Requirement]:
        """Process a single page: extract text and image requirements (simplified version).
        
        Args:
            page_obj: Page dict with {page_number: int (1-based physical page), text: str}
            image_dir: Directory containing extracted images
            progress_callback: Progress callback function
            total_pages: Total pages for progress calculation
            
        Returns:
            List of requirements extracted from this page
        """
        import asyncio
        
        # Extract physical page number (1-based, guaranteed correct!)
        page_number = page_obj["page_number"]
        page_text = page_obj["text"]
        has_images = bool(
            image_dir and page_number in self.page_image_metadata and self.page_image_metadata[page_number]
        )
        text_is_usable = page_text and len(page_text.strip()) >= 50

        # Пропускаем только если нет ни текста, ни изображений
        if not text_is_usable and not has_images:
            logger.debug(f"Page {page_number}: skipping (empty text and no images)")
            if progress_callback:
                progress_callback(page_number, total_pages, f"Page {page_number} skipped (empty)")
            return []

        # Extract requirements from text (если текст достаточный)
        text_requirements = []
        if text_is_usable:
            logger.info(f"[PAGE {page_number}] Extracting from text ({len(page_text)} chars)")
            text_requirements = await self._async_extract_from_text_simple(
                page_number,
                page_text
            )
        elif has_images:
            logger.info(f"[PAGE {page_number}] Text too short, extracting from images only")

        # Extract requirements from images on this page (PARALLEL)
        image_requirements = []
        # NOTE: image_metadata uses 1-based page numbers as keys
        if image_dir and page_number in self.page_image_metadata:
            images = self.page_image_metadata[page_number]
            if images:
                image_tasks = [
                    self._async_extract_from_image_simple(
                        Path(img_meta["path"]),
                        page_number  # Physical page number (1-based)
                    )
                    for img_meta in images
                    if Path(img_meta["path"]).exists()
                ]
                if image_tasks:
                    image_results = await asyncio.gather(*image_tasks, return_exceptions=True)
                    for result in image_results:
                        if isinstance(result, Exception):
                            logger.error(f"Error extracting from image on page {page_number}: {result}")
                        elif isinstance(result, list):
                            image_requirements.extend(result)
        
        if progress_callback:
            progress_callback(page_number, total_pages, f"Page {page_number}: {len(text_requirements)} text + {len(image_requirements)} image requirements")
        
        logger.info(f"Page {page_number}: extracted {len(text_requirements)} text + {len(image_requirements)} image requirements")
        
        return text_requirements + image_requirements
    
    async def _async_extract_from_text_simple(
        self,
        page_num: int,
        page_text: str
    ) -> List[Requirement]:
        """Async wrapper for text extraction (simplified version without TOC context)."""
        import asyncio
        
        logger.info(f"[TEXT_EXTRACT] page_num={page_num} - CALLING AI for text extraction")
        
        # Run sync AI client call in thread pool
        loop = asyncio.get_running_loop()
        requirements = await loop.run_in_executor(
            None,
            self.ai_client.extract_requirements,
            "Page",  # section_number (generic)
            f"Page {page_num}",  # section_title
            str(page_num),  # page_range
            page_text
        )
        
        logger.debug(f"[TEXT_EXTRACT] page_num={page_num} - AI returned {len(requirements)} requirements")
        
        for req in requirements:
            req.source_page = page_num
            req.section_number = None
            req.source_type = "text"
        
        return requirements
    
    async def _async_extract_from_image_simple(
        self,
        image_path: Path,
        page_num: int
    ) -> List[Requirement]:
        """Async wrapper for image extraction (simplified version)."""
        import asyncio
        
        if not hasattr(self.ai_client, 'extract_requirements_from_image'):
            return []
        
        # Run sync AI client call in thread pool
        loop = asyncio.get_running_loop()
        requirements = await loop.run_in_executor(
            None,
            self.ai_client.extract_requirements_from_image,
            image_path,
            page_num,  # page_number (ADDED!)
            "Page",  # section_number
            f"Page {page_num}"  # section_title
        )
        
        # Set metadata for each requirement
        for req in requirements:
            req.source_page = page_num
            req.section_number = None
            req.source_type = "image"
        
        return requirements
    
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