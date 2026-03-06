"""PDF processor for extracting text and structure from PDF documents.

This module provides functionality for extracting text content from PDF files
using pymupdf4llm with support for multi-threaded processing, progress tracking,
and image extraction.

Classes:
    PDFProcessor: Main processor for PDF text extraction with multi-threading.

Features:
    - Multi-threaded parallel page extraction
    - Progress callbacks with thread-safe updates
    - Image extraction from PDFs
    - Markdown conversion
    - Error recovery (continues on page errors)
    - Automatic worker count detection
"""

# Standard library imports
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# Third-party imports
import pymupdf
import pymupdf4llm

# Local imports
from .config import PDFProcessorConfig
from .logger import get_logger

logger = get_logger(__name__)


class PDFProcessor:
    """Handles PDF document processing with multi-threaded text extraction.
    
    Provides methods for extracting text content from PDF files using
    parallel processing for maximum performance. Automatically determines
    optimal thread count based on CPU cores.
    
    Attributes:
        config: PDF processor configuration with extraction parameters.
        max_workers: Number of worker threads for parallel processing.
        
    Example:
        >>> config = PDFProcessorConfig(dpi=200, write_images=True, max_workers=4)
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
            config: PDF processor configuration specifying DPI, image settings,
                and max_workers for parallel processing.
        """
        self.config = config
        # Determine optimal worker count
        self.max_workers = config.max_workers or min(32, (os.cpu_count() or 1) + 4)
        logger.info(f"PDF processor initialized with {self.max_workers} worker threads")
    
    def extract_pages(
        self, 
        pdf_path: Path, 
        image_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[List[Dict], Dict[int, List[Dict]]]:
        """Extract text and images from PDF in a SINGLE call to pymupdf4llm.
        
        CRITICAL: Uses one call with page_chunks=True to avoid pymupdf4llm
        returning wrong/duplicated text when called per-page.
        
        Args:
            pdf_path: Path to PDF file to process.
            image_dir: Directory where extracted images will be saved.
            progress_callback: Optional callback function called with (current, total).
        
        Returns:
            Tuple of (pages, image_metadata) where:
            - pages: List of dicts {page_number: int (1-based), text: str}
            - image_metadata: Dict mapping page_number (1-based) to list of image metadata dicts
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Extracting text and images from PDF: {pdf_path}")
        logger.info(f"Images will be saved to: {image_dir}")
        
        image_dir.mkdir(parents=True, exist_ok=True)
        
        # Get total pages
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        logger.info(f"PDF has {total_pages} pages — extracting ALL at once with page_chunks=True")
        
        if progress_callback:
            progress_callback(0, total_pages)
        
        # SINGLE CALL to extract ALL pages at once
        chunks = pymupdf4llm.to_markdown(
            str(pdf_path),
            page_chunks=True,
            write_images=self.config.write_images,
            image_path=str(image_dir),
            dpi=self.config.dpi,
            show_progress=False
        )
        
        logger.info(f"pymupdf4llm returned {len(chunks)} chunks for {total_pages} pages")
        
        # Build pages list with EXPLICIT page numbers from chunk metadata
        pages = []
        image_results: Dict[int, List[Dict]] = {}
        
        for chunk_idx, chunk_data in enumerate(chunks):
            text = chunk_data.get("text", "")
            metadata = chunk_data.get("metadata", {})
            
            # pymupdf4llm metadata.page is already 1-based
            page_number = metadata.get("page", chunk_idx + 1) if metadata else chunk_idx + 1
            
            pages.append({
                "page_number": page_number,
                "text": text
            })
            
            # Process images for this chunk
            page_images = []
            if self.config.write_images and "images" in chunk_data:
                images_info = chunk_data.get("images", [])
                pdf_name = pdf_path.stem
                page_idx_0based = page_number - 1  # pymupdf4llm names image files with 0-based index
                
                for img_idx, img_info in enumerate(images_info):
                    image_ext = self.config.image_format
                    old_path = None
                    
                    # Try to find the image file
                    for ext in ['png', 'jpg', 'jpeg']:
                        candidate = image_dir / f"{pdf_name}-{page_idx_0based}-{img_idx}.{ext}"
                        if candidate.exists():
                            old_path = candidate
                            image_ext = ext
                            break
                    
                    if not old_path:
                        for ext in ['png', 'jpg', 'jpeg']:
                            for pattern in [
                                f"{pdf_name}-p{page_idx_0based}-img{img_idx}.{ext}",
                                f"{pdf_name}-p{page_number}-img{img_idx}.{ext}",
                            ]:
                                candidate = image_dir / pattern
                                if candidate.exists():
                                    old_path = candidate
                                    image_ext = ext
                                    break
                            if old_path:
                                break
                    
                    # Glob fallback
                    if not old_path:
                        for pat in [f"*{page_idx_0based}*{img_idx}*", f"*{page_idx_0based}*"]:
                            found = list(image_dir.glob(pat))
                            if found:
                                old_path = found[0]
                                image_ext = old_path.suffix.lstrip('.')
                                break
                    
                    if old_path and old_path.exists():
                        new_filename = f"page_{page_number}_image_{img_idx + 1}.{image_ext}"
                        new_path = image_dir / new_filename
                        try:
                            old_path.rename(new_path)
                            page_images.append({
                                "filename": new_filename,
                                "path": str(new_path),
                                "page_number": page_number,
                                "image_index": img_idx + 1,
                                "width": img_info.get("width"),
                                "height": img_info.get("height"),
                                "ext": image_ext
                            })
                        except Exception as e:
                            logger.warning(f"Failed to rename image {old_path.name}: {e}")
            
            image_results[page_number] = page_images
            
            if progress_callback:
                progress_callback(chunk_idx + 1, total_pages)
        
        successful = sum(1 for p in pages if p["text"])
        total_images = sum(len(imgs) for imgs in image_results.values())
        
        logger.info(f"Successfully extracted {successful}/{total_pages} pages and {total_images} images")
        
        # Verify page extraction: log first ~100 chars of each page
        logger.info(f"[PAGE CONTENT MAP] Verifying page extraction order:")
        for p in pages:
            text_preview = p["text"][:120].replace('\n', ' ').strip() if p["text"] else "(EMPTY)"
            logger.info(f"[PAGE CONTENT MAP] Page {p['page_number']:3d}: {text_preview}")
        
        return pages, image_results
    
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
