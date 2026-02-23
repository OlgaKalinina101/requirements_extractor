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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
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
    
    def _extract_single_page(
        self,
        pdf_path: Path,
        page_num: int,
        image_dir: Path
    ) -> Tuple[int, Optional[str], List[Dict]]:
        """Extract text and image metadata from a single PDF page (thread-safe).
        
        This method is called by worker threads in parallel.
        
        Args:
            pdf_path: Path to PDF file.
            page_num: Page number to extract (0-indexed).
            image_dir: Directory for saving images.
            
        Returns:
            Tuple of (page_num, extracted_text, image_metadata_list) where:
            - page_num: Page number (0-indexed)
            - text: Extracted text or None if failed
            - image_metadata: List of dicts with image info (filename, page, index)
        """
        image_metadata = []
        
        try:
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
                chunk_data = chunk[0]
                text = chunk_data.get("text", "")
                
                # Extract image metadata from chunk
                if self.config.write_images and "images" in chunk_data:
                    images_info = chunk_data.get("images", [])
                    page_number_1based = page_num + 1  # Convert to 1-based
                    
                    for img_idx, img_info in enumerate(images_info):
                        # Find corresponding image file in directory
                        # pymupdf4llm saves images as: {filename}-p{page}-img{idx}.{ext}
                        pdf_name = pdf_path.stem
                        image_ext = self.config.image_format
                        
                        # Try to find the image file — multiple strategies
                        old_path = None
                        
                        # Strategy 1: exact match (0-indexed page)
                        for ext in ['png', 'jpg', 'jpeg']:
                            candidate = image_dir / f"{pdf_name}-p{page_num}-img{img_idx}.{ext}"
                            if candidate.exists():
                                old_path = candidate
                                image_ext = ext
                                break
                        
                        # Strategy 2: 1-indexed page (some pymupdf4llm versions)
                        if not old_path:
                            for ext in ['png', 'jpg', 'jpeg']:
                                candidate = image_dir / f"{pdf_name}-p{page_num + 1}-img{img_idx}.{ext}"
                                if candidate.exists():
                                    old_path = candidate
                                    image_ext = ext
                                    break
                        
                        # Strategy 3: glob fallback — any file matching page+img index
                        if not old_path:
                            patterns = [
                                f"*p{page_num}*img{img_idx}*",
                                f"*p{page_num + 1}*img{img_idx}*",
                                f"*{page_num}*{img_idx}*",
                            ]
                            for pat in patterns:
                                found = list(image_dir.glob(pat))
                                if found:
                                    old_path = found[0]
                                    image_ext = old_path.suffix.lstrip('.')
                                    logger.debug(f"Found image via glob '{pat}': {old_path.name}")
                                    break
                        
                        if old_path is None:
                            # Log all files in dir to help debug
                            all_files = list(image_dir.iterdir()) if image_dir.exists() else []
                            logger.debug(
                                f"Image not found for page {page_num}, img {img_idx}. "
                                f"Files in dir: {[f.name for f in all_files[:10]]}"
                            )
                        
                        if old_path and old_path.exists():
                            # Rename to our format: page_X_image_Y.ext
                            new_filename = f"page_{page_number_1based}_image_{img_idx + 1}.{image_ext}"
                            new_path = image_dir / new_filename
                            
                            try:
                                old_path.rename(new_path)
                                logger.debug(f"Renamed image: {old_path.name} → {new_filename}")
                                
                                image_metadata.append({
                                    "filename": new_filename,
                                    "path": str(new_path),
                                    "page_number": page_number_1based,
                                    "image_index": img_idx + 1,
                                    "width": img_info.get("width"),
                                    "height": img_info.get("height"),
                                    "xref": img_info.get("xref"),
                                    "ext": image_ext
                                })
                            except Exception as e:
                                logger.warning(f"Failed to rename image {old_path.name}: {e}")
                                # Still add metadata with old filename
                                image_metadata.append({
                                    "filename": old_path.name,
                                    "path": str(old_path),
                                    "page_number": page_number_1based,
                                    "image_index": img_idx + 1,
                                    "width": img_info.get("width"),
                                    "height": img_info.get("height"),
                                    "xref": img_info.get("xref"),
                                    "ext": image_ext
                                })
                        else:
                            logger.debug(f"Image file not found for page {page_number_1based}, image {img_idx}")
                
                return (page_num, text, image_metadata)
            return (page_num, "", [])
            
        except Exception as e:
            logger.warning(f"Failed to process page {page_num}: {e}")
            return (page_num, None, [])
    
    def extract_pages(
        self, 
        pdf_path: Path, 
        image_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[List[str], Dict[int, List[Dict]]]:
        """Extract text and images from PDF file using multi-threaded parallel processing.
        
        Processes multiple pages simultaneously for maximum performance.
        Progress callback is called in a thread-safe manner.
        
        Args:
            pdf_path: Path to PDF file to process.
            image_dir: Directory where extracted images will be saved.
            progress_callback: Optional callback function called after each page completes.
                Receives (current_page, total_pages) as arguments. Thread-safe.
        
        Returns:
            Tuple of (pages, image_metadata) where:
            - pages: List of strings, one per page, containing extracted text in markdown format
            - image_metadata: Dict mapping page_number (1-based) to list of image metadata dicts
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist at specified path.
            
        Note:
            - Uses ThreadPoolExecutor with auto-detected worker count
            - Failed pages return empty strings to maintain page order
            - Progress callback is called from worker threads (ensure thread-safety)
            - Images are renamed to format: page_X_image_Y.ext
            
        Example:
            >>> def progress(current, total):
            ...     print(f"Processing {current}/{total}")
            >>> pages, images = processor.extract_pages(
            ...     Path("spec.pdf"),
            ...     Path("images/"),
            ...     progress_callback=progress
            ... )
            >>> print(f"Extracted {len(pages)} pages and {sum(len(imgs) for imgs in images.values())} images")
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Extracting text and images from PDF: {pdf_path}")
        logger.info(f"Images will be saved to: {image_dir}")
        logger.info(f"Using {self.max_workers} worker threads for parallel extraction")
        
        # Create image directory
        image_dir.mkdir(parents=True, exist_ok=True)
        
        # Get total pages
        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        logger.info(f"PDF has {total_pages} pages - starting parallel extraction")
        
        # Thread-safe progress tracking
        progress_lock = Lock()
        pages_completed = [0]  # Use list for mutability in closure
        
        def report_progress() -> None:
            """Thread-safe progress reporting."""
            with progress_lock:
                pages_completed[0] += 1
                current = pages_completed[0]
                if progress_callback:
                    progress_callback(current, total_pages)
                # Log every 10 pages
                if current % 10 == 0 or current == 1 or current == total_pages:
                    logger.info(f"[PDF_PROCESSOR] Processed {current}/{total_pages} pages")
        
        # Store results by page number to maintain order
        results: Dict[int, Optional[str]] = {}
        image_results: Dict[int, List[Dict]] = {}
        
        # Process pages in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all pages for processing
            future_to_page = {
                executor.submit(self._extract_single_page, pdf_path, page_num, image_dir): page_num
                for page_num in range(total_pages)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_page):
                page_num, text, image_metadata = future.result()
                results[page_num] = text if text is not None else ""
                # Store images by 1-based page number
                page_number_1based = page_num + 1
                image_results[page_number_1based] = image_metadata
                report_progress()
        
        # Reconstruct pages in order
        pages = [results.get(i, "") for i in range(total_pages)]
        
        successful = sum(1 for p in pages if p)
        total_images = sum(len(imgs) for imgs in image_results.values())
        
        logger.info(f"Successfully extracted {successful}/{total_pages} pages and {total_images} images from PDF")
        
        if successful < total_pages:
            logger.warning(f"{total_pages - successful} pages failed to extract")
        
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
