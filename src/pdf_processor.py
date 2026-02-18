"""PDF processor for extracting text and structure from PDF documents.

This module provides functionality for extracting text content from PDF files
using pymupdf4llm with support for progress tracking, image extraction, and
page-by-page processing.

Classes:
    PDFProcessor: Main processor for PDF text extraction.

Features:
    - Page-by-page extraction with progress callbacks
    - Image extraction from PDFs
    - Markdown conversion
    - Error recovery (continues on page errors)
"""

# Standard library imports
from pathlib import Path
from typing import Callable, List, Optional

# Third-party imports
import pymupdf
import pymupdf4llm

# Local imports
from .config import PDFProcessorConfig
from .logger import get_logger

logger = get_logger(__name__)


class PDFProcessor:
    """Handles PDF document processing and text extraction.
    
    Provides methods for extracting text content from PDF files with
    support for progress tracking and image extraction. Processes PDFs
    page-by-page to enable real-time progress reporting.
    
    Attributes:
        config: PDF processor configuration with extraction parameters.
        
    Example:
        >>> config = PDFProcessorConfig(dpi=200, write_images=True)
        >>> processor = PDFProcessor(config)
        >>> pages = processor.extract_pages(
        ...     Path("doc.pdf"),
        ...     Path("images/"),
        ...     progress_callback=lambda cur, tot: print(f"{cur}/{tot}")
        ... )
    """
    
    def __init__(self, config: PDFProcessorConfig) -> None:
        """Initialize PDF processor with configuration.
        
        Args:
            config: PDF processor configuration specifying DPI, image settings, etc.
        """
        self.config = config
    
    def extract_pages(
        self, 
        pdf_path: Path, 
        image_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[str]:
        """Extract text from PDF file page by page with progress tracking.
        
        Processes each page individually to enable real-time progress reporting.
        Automatically handles images if configured, and continues processing even
        if individual pages fail.
        
        Args:
            pdf_path: Path to PDF file to process.
            image_dir: Directory where extracted images will be saved.
            progress_callback: Optional callback function called after each page.
                Receives (current_page, total_pages) as arguments.
        
        Returns:
            List of strings, one per page, containing extracted text in markdown format.
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist at specified path.
            
        Note:
            If a page fails to process, a warning is logged and processing continues
            with remaining pages.
            
        Example:
            >>> def progress(current, total):
            ...     print(f"Processing {current}/{total}")
            >>> pages = processor.extract_pages(
            ...     Path("spec.pdf"),
            ...     Path("images/"),
            ...     progress_callback=progress
            ... )
            >>> print(f"Extracted {len(pages)} pages")
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Extracting text from PDF: {pdf_path}")
        logger.info(f"Images will be saved to: {image_dir}")
        
        # Create image directory
        image_dir.mkdir(parents=True, exist_ok=True)
        
        # Get total pages first for progress tracking
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        logger.info(f"PDF has {total_pages} pages")
        
        # Extract markdown by page with progress
        doc_chunks = []
        pages_processed = 0
        
        # Process page by page to show progress
        for page_num in range(total_pages):
            try:
                # Extract single page
                chunk = pymupdf4llm.to_markdown(
                    str(pdf_path),
                    page_chunks=True,
                    pages=[page_num],
                    write_images=self.config.write_images,
                    image_path=str(image_dir),
                    dpi=self.config.dpi,
                    show_progress=False  # Disable internal progress bar
                )
                
                if chunk:
                    doc_chunks.extend(chunk)
                
                pages_processed += 1
                
                # Call progress callback after each page
                if progress_callback:
                    progress_callback(pages_processed, total_pages)
                
                # Log every 10 pages or first/last page
                if pages_processed % 10 == 0 or pages_processed == 1 or pages_processed == total_pages:
                    logger.info(f"[PDF_PROCESSOR] Processed {pages_processed}/{total_pages} pages")
                
            except Exception as e:
                logger.warning(f"Failed to process page {page_num}: {e}")
                continue
        
        # Extract text from chunks
        pages = [chunk.get("text", "") for chunk in doc_chunks]
        
        logger.info(f"Successfully extracted {len(pages)} pages from PDF")
        
        return pages
    
    def get_section_text(
        self,
        pages: List[str],
        start_page: int,
        end_page: int = None
    ) -> str:
        """
        Get text for a specific section by page range.
        
        Args:
            pages: List of all page texts
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (1-indexed), None for end of document
        
        Returns:
            Combined text of the section
        """
        if end_page is None:
            end_page = len(pages) + 1
        
        # Convert to 0-indexed
        start_idx = start_page - 1
        end_idx = end_page - 1
        
        # Validate indices
        if start_idx < 0 or start_idx >= len(pages):
            logger.warning(f"Invalid start page {start_page}, using page 1")
            start_idx = 0
        
        if end_idx < 0 or end_idx > len(pages):
            logger.warning(f"Invalid end page {end_page}, using last page")
            end_idx = len(pages)
        
        # Extract section pages
        section_pages = pages[start_idx:end_idx]
        
        # Join with double newline
        section_text = "\n\n".join(section_pages)
        
        logger.debug(
            f"Extracted section text from pages {start_page}-{end_page-1 if end_page else 'end'}, "
            f"total length: {len(section_text)} characters"
        )
        
        return section_text
