"""PDF processor for extracting text and structure from PDF documents.

This module provides functionality for extracting text content from PDF files
using pymupdf4llm for text-based pages and Tesseract OCR for scanned
(image-only) pages.  Every page additionally produces a ``text_blocks`` list
that carries word-level bounding-box coordinates — used by the frontend to
highlight requirement text inside the PDF viewer.

Classes:
    PDFProcessor: Main processor for PDF text extraction.

Features:
    - Hybrid text/scan detection per page
    - OCR fallback (Tesseract) for scanned pages
    - Image preprocessing (denoise + adaptive threshold) for better OCR
    - Per-page text_blocks: [{text, x0, y0, x1, y1, block_type}]  (PDF points)
    - Image extraction from PDFs
    - Markdown conversion via pymupdf4llm
    - Progress callbacks
    - Automatic worker count detection
"""

# Standard library imports
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

# Third-party imports
import pymupdf
import pymupdf4llm

# Local imports
from .config import PDFProcessorConfig
from .logger import get_logger

logger = get_logger(__name__)

def _is_scanned_page(page: pymupdf.Page, threshold: int) -> bool:
    """Return True when the page has fewer embedded characters than *threshold*.

    Typical values by page type:
      - True scan (image PDF):          0–20 chars
      - Native PDF technical drawing:  50–400 chars  (labels are vector text)
      - Real text page:              500–5 000 chars

    A threshold of 500 sits safely above drawing noise while remaining well
    below any genuine text page.
    """
    return len(page.get_text().strip()) < threshold


def _text_blocks_from_page(page: pymupdf.Page) -> List[Dict]:
    """Extract word-level bounding boxes from a text-based PDF page.

    Uses pymupdf's "dict" extraction which returns blocks → lines → spans
    with precise character positions.  We flatten everything to individual
    *span* entries (a span is a run of text with the same font/size).

    Returns:
        List of dicts with keys: text, x0, y0, x1, y1, block_type.
        Coordinates are in PDF points (1 pt = 1/72 inch), origin top-left.
    """
    blocks = []
    page_dict = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)
    for block in page_dict.get("blocks", []):
        block_type = "image" if block.get("type") == 1 else "text"
        if block_type == "image":
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                bbox = span.get("bbox", (0, 0, 0, 0))
                blocks.append({
                    "text": text,
                    "x0": round(bbox[0], 2),
                    "y0": round(bbox[1], 2),
                    "x1": round(bbox[2], 2),
                    "y1": round(bbox[3], 2),
                    "block_type": "text",
                })
    return blocks


def _render_page_to_array(page: pymupdf.Page, dpi: int):
    """Render a PyMuPDF page to an RGB numpy array.

    Must be called from a single thread while the document is open (PyMuPDF
    is not thread-safe for concurrent page access on the same document).

    Returns:
        Tuple (img_array, scale_x, scale_y) where scale factors convert pixel
        coordinates back to PDF points (origin top-left).
    """
    import numpy as np
    matrix = pymupdf.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB)
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, 3
    )
    scale_x = page.rect.width / pix.width
    scale_y = page.rect.height / pix.height
    return img_array, scale_x, scale_y


def _preprocess_for_ocr(img_array):
    """Enhance a scanned page image before OCR.

    Steps: convert to grayscale → denoise → adaptive binarisation.
    This dramatically improves Tesseract accuracy on noisy or low-contrast scans.
    """
    import cv2
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    binary = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 10,
    )
    return binary


def _ocr_array(
    img_array,
    scale_x: float,
    scale_y: float,
    page_number: int,
) -> Tuple[str, List[Dict]]:
    """Run Tesseract OCR on a pre-rendered numpy array (thread-safe).

    Tesseract is invoked as a subprocess via pytesseract, so multiple calls
    can run truly in parallel without any shared mutable state.

    Returns:
        Tuple (raw_text, text_blocks) following the same schema as
        _text_blocks_from_page.
    """
    import pytesseract

    processed = _preprocess_for_ocr(img_array)

    data = pytesseract.image_to_data(
        processed,
        lang="rus+eng",
        output_type=pytesseract.Output.DICT,
        config="--psm 6",
    )

    text_blocks: List[Dict] = []
    raw_parts: List[str] = []

    n = len(data["text"])
    for i in range(n):
        word = data["text"][i].strip()
        conf = int(data["conf"][i])
        if not word or conf < 30:
            continue
        x = data["left"][i]
        y = data["top"][i]
        w = data["width"][i]
        h = data["height"][i]
        text_blocks.append({
            "text": word,
            "x0": round(x * scale_x, 2),
            "y0": round(y * scale_y, 2),
            "x1": round((x + w) * scale_x, 2),
            "y1": round((y + h) * scale_y, 2),
            "block_type": "ocr",
        })
        raw_parts.append(word)

    logger.debug(f"[OCR] Page {page_number}: {len(text_blocks)} words recognised")
    return " ".join(raw_parts), text_blocks


class PDFProcessor:
    """Handles PDF document processing with hybrid text/OCR extraction.

    For each page the processor first checks whether embedded text is present.
    If yes, pymupdf4llm (called once for the whole document) supplies the
    markdown text, while pymupdf's dict extraction supplies the text_blocks.
    If a page is image-only (scanned), easyocr is used to recognise text and
    produce bounding boxes.

    Attributes:
        config: PDF processor configuration with extraction parameters.
        max_workers: Number of worker threads for parallel processing.

    Example:
        >>> config = PDFProcessorConfig(dpi=200, write_images=True)
        >>> processor = PDFProcessor(config)
        >>> pages, image_meta, page_blocks = processor.extract_pages(
        ...     Path("doc.pdf"), Path("images/")
        ... )
    """

    def __init__(self, config: PDFProcessorConfig) -> None:
        self.config = config
        self.max_workers = config.max_workers or min(32, (os.cpu_count() or 1) + 4)
        logger.info(f"PDF processor initialized with {self.max_workers} worker threads")

    def extract_pages(
        self,
        pdf_path: Path,
        image_dir: Path,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[List[Dict], Dict[int, List[Dict]], List[Dict]]:
        """Extract text, images, and text_blocks from a PDF.

        Args:
            pdf_path: Path to PDF file to process.
            image_dir: Directory where extracted images will be saved.
            progress_callback: Optional callback called with (current, total).

        Returns:
            Tuple of (pages, image_metadata, page_blocks_list):

            - pages: List of dicts {page_number: int (1-based), text: str}
            - image_metadata: Dict mapping page_number to list of image dicts
            - page_blocks_list: List of dicts per page::

                  {
                      page_number: int,
                      raw_text:    str,
                      text_blocks: [{text, x0, y0, x1, y1, block_type}, ...],
                      is_ocr:      bool,
                  }
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        logger.info(f"Extracting text from PDF: {pdf_path}")
        image_dir.mkdir(parents=True, exist_ok=True)

        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)

        threshold = self.config.ocr_text_threshold
        # Detect which pages are scanned
        scanned_pages = {
            i + 1  # 1-based
            for i in range(total_pages)
            if _is_scanned_page(doc[i], threshold)
        }
        text_pages = set(range(1, total_pages + 1)) - scanned_pages

        if scanned_pages:
            logger.info(
                f"{len(scanned_pages)} scanned page(s) detected — OCR will be used: "
                + ", ".join(str(p) for p in sorted(scanned_pages))
            )
        else:
            logger.info("All pages contain embedded text — OCR not required")

        if progress_callback:
            progress_callback(0, total_pages)

        # ------------------------------------------------------------------
        # 1. Extract markdown text for text-based pages via pymupdf4llm
        #    (single call with page_chunks=True for correctness)
        # ------------------------------------------------------------------
        chunks: List[Dict] = []
        if text_pages:
            chunks = pymupdf4llm.to_markdown(
                str(pdf_path),
                page_chunks=True,
                write_images=self.config.write_images,
                image_path=str(image_dir),
                dpi=self.config.dpi,
                show_progress=False,
            )
            logger.info(f"pymupdf4llm returned {len(chunks)} chunks")

        # Map page_number → markdown text from pymupdf4llm
        llm_text_by_page: Dict[int, str] = {}
        for idx, chunk in enumerate(chunks):
            meta = chunk.get("metadata", {})
            pn = meta.get("page", idx + 1) if meta else idx + 1
            llm_text_by_page[pn] = chunk.get("text", "")

        # ------------------------------------------------------------------
        # 2. Build per-page text_blocks (bbox data)
        #
        # Strategy:
        #   a) Text pages: fast, done right here in the main thread.
        #   b) Scanned pages: render to numpy arrays first (PyMuPDF is not
        #      thread-safe, so rendering must be sequential), then OCR all
        #      arrays in parallel via ThreadPoolExecutor.  Each worker thread
        #      holds its own easyocr Reader (thread-local), so inference runs
        #      truly concurrently on multi-core CPUs.
        # ------------------------------------------------------------------
        pages: List[Dict] = []
        image_results: Dict[int, List[Dict]] = {}
        page_blocks_list: List[Dict] = []

        # Pre-collect text-page blocks and render scanned pages to arrays
        text_results: Dict[int, Tuple[str, List[Dict]]] = {}   # page_num → (text, blocks)
        scan_arrays: Dict[int, Tuple] = {}                     # page_num → (array, sx, sy)

        for page_idx in range(total_pages):
            page_number = page_idx + 1
            page = doc[page_idx]
            image_results[page_number] = []

            if page_number in scanned_pages:
                # Render now (single-thread, PyMuPDF not thread-safe)
                arr, sx, sy = _render_page_to_array(page, dpi=self.config.ocr_dpi)
                scan_arrays[page_number] = (arr, sx, sy)
            else:
                raw_text = llm_text_by_page.get(page_number, "")
                text_blocks = _text_blocks_from_page(page)
                text_results[page_number] = (raw_text, text_blocks)

        doc.close()

        # Run OCR in parallel
        ocr_results: Dict[int, Tuple[str, List[Dict]]] = {}
        if scan_arrays:
            n_workers = min(self.config.ocr_workers, len(scan_arrays))
            logger.info(
                f"[OCR] Starting parallel OCR: {len(scan_arrays)} pages, "
                f"{n_workers} workers, dpi={self.config.ocr_dpi}"
            )
            with ThreadPoolExecutor(max_workers=n_workers) as executor:
                futures = {
                    executor.submit(_ocr_array, arr, sx, sy, pn): pn
                    for pn, (arr, sx, sy) in scan_arrays.items()
                }
                for future in as_completed(futures):
                    pn = futures[future]
                    try:
                        ocr_results[pn] = future.result()
                    except Exception as exc:
                        logger.error(f"[OCR] Page {pn} failed: {exc}")
                        ocr_results[pn] = ("", [])
                    if progress_callback:
                        progress_callback(pn, total_pages)

        # Assemble final ordered lists
        for page_idx in range(total_pages):
            page_number = page_idx + 1
            if page_number in scanned_pages:
                raw_text, text_blocks = ocr_results.get(page_number, ("", []))
                is_ocr = True
            else:
                raw_text, text_blocks = text_results.get(page_number, ("", []))
                is_ocr = False
                if progress_callback:
                    progress_callback(page_number, total_pages)

            pages.append({"page_number": page_number, "text": raw_text})
            page_blocks_list.append({
                "page_number": page_number,
                "raw_text": raw_text,
                "text_blocks": text_blocks,
                "is_ocr": is_ocr,
            })

        # ------------------------------------------------------------------
        # 3. Discover and rename images written by pymupdf4llm
        # ------------------------------------------------------------------
        if self.config.write_images:
            pdf_name = pdf_path.name
            all_image_files = sorted(image_dir.glob(f"{pdf_name}-*"))
            logger.info(f"Found {len(all_image_files)} image files on disk")

            pattern = re.compile(
                rf"^{re.escape(pdf_name)}-0*(\d+)-0*(\d+)\.\w+$"
            )
            for img_file in all_image_files:
                m = pattern.match(img_file.name)
                if not m:
                    continue
                page_number = int(m.group(1))
                img_idx = int(m.group(2))
                image_ext = img_file.suffix.lstrip(".")

                new_filename = f"page_{page_number}_image_{img_idx + 1}.{image_ext}"
                new_path = image_dir / new_filename
                try:
                    img_file.rename(new_path)
                    if page_number not in image_results:
                        image_results[page_number] = []
                    image_results[page_number].append({
                        "filename": new_filename,
                        "path": str(new_path),
                        "page_number": page_number,
                        "image_index": img_idx + 1,
                        "ext": image_ext,
                    })
                except Exception as exc:
                    logger.warning(f"Failed to rename image {img_file.name}: {exc}")

            img_pages = {p for p, imgs in image_results.items() if imgs}
            total_imgs = sum(len(imgs) for imgs in image_results.values())
            logger.info(f"Mapped {total_imgs} images across {len(img_pages)} pages")

        successful = sum(1 for p in pages if p["text"])
        total_images = sum(len(imgs) for imgs in image_results.values())
        logger.info(
            f"Extraction complete: {successful}/{total_pages} pages with text, "
            f"{total_images} images, "
            f"{len(scanned_pages)} OCR pages"
        )

        logger.info("[PAGE CONTENT MAP] Verifying page extraction order:")
        for p in pages:
            preview = p["text"][:120].replace("\n", " ").strip() if p["text"] else "(EMPTY)"
            logger.info(f"[PAGE CONTENT MAP] Page {p['page_number']:3d}: {preview}")

        return pages, image_results, page_blocks_list

    def get_section_text(
        self,
        pages: List[str],
        start_page: int,
        end_page: int = None,
    ) -> str:
        """Get combined text for a page range.

        Args:
            pages: List of all page texts.
            start_page: Starting page number (1-indexed).
            end_page: Ending page number (1-indexed), None for end of document.

        Returns:
            Combined text of the section.
        """
        if end_page is None:
            end_page = len(pages) + 1

        start_idx = start_page - 1
        end_idx = end_page - 1

        if start_idx < 0 or start_idx >= len(pages):
            logger.warning(f"Invalid start page {start_page}, using page 1")
            start_idx = 0

        if end_idx < 0 or end_idx > len(pages):
            logger.warning(f"Invalid end page {end_page}, using last page")
            end_idx = len(pages)

        section_pages = pages[start_idx:end_idx]
        section_text = "\n\n".join(section_pages)

        logger.debug(
            f"Extracted section text from pages {start_page}-"
            f"{end_page - 1 if end_page else 'end'}, "
            f"total length: {len(section_text)} characters"
        )
        return section_text
