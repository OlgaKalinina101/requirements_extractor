"""Main orchestrator for PDF requirements extraction.

This module provides the high-level orchestration logic for the entire
requirements extraction pipeline, coordinating PDF processing, TOC parsing,
and requirement extraction with DeepSeek API.

Classes:
    RequirementsExtractor: Main coordinator class for extraction workflow.

Functions:
    create_extractor: Factory function for creating configured extractors.

Workflow:
    1. Extract text from all PDF pages
    2. Parse table of contents (or use manual TOC)
    3. Extract requirements from each section using AI
    4. Generate reports and save results
"""

# Standard library imports
import json
from pathlib import Path
from typing import List, Optional

# Local imports
from .config import ApplicationConfig
from .deepseek_client import DeepSeekClient
from .logger import get_logger, setup_logger
from .models import RequirementsRegistry, Section, TableOfContentsEntry
from .pdf_processor import PDFProcessor
from .usage_tracker import get_usage_report

logger = get_logger(__name__)


class RequirementsExtractor:
    """Main orchestrator for the requirements extraction pipeline.
    
    Coordinates the complete workflow from PDF ingestion through requirement
    extraction and report generation. Manages state across extraction steps
    and provides both individual step methods and full pipeline execution.
    
    Attributes:
        config: Application configuration.
        pdf_processor: PDF processor instance.
        pages: Extracted pages from PDF (populated after extraction).
        toc_entries: Parsed table of contents entries.
        registry: Requirements registry (populated during extraction).
        
    Example:
        >>> config = ApplicationConfig()
        >>> extractor = RequirementsExtractor(config)
        >>> extractor.extract_pdf_pages()
        >>> extractor.parse_table_of_contents(manual_toc=toc_data)
        >>> extractor.extract_requirements_from_sections()
        >>> registry_path = extractor.save_registry()
    """
    
    def __init__(self, config: ApplicationConfig) -> None:
        """Initialize requirements extractor with configuration.
        
        Args:
            config: Application configuration with paths and API settings.
        """
        self.config = config
        self.pdf_processor = PDFProcessor(config.pdf_processor)
        self.pages: List[str] = []
        self.toc_entries: List[TableOfContentsEntry] = []
        self.registry = RequirementsRegistry()
    
    def extract_pdf_pages(self) -> List[str]:
        """Extract text from all pages in the PDF document.
        
        Step 1 of the extraction pipeline. Processes PDF page by page
        with progress logging.
        
        Returns:
            List of strings, one per page, containing extracted text.
            Also stores result in self.pages for later use.
            
        Example:
            >>> extractor = RequirementsExtractor(config)
            >>> pages = extractor.extract_pdf_pages()
            >>> print(f"Extracted {len(pages)} pages")
        """
        logger.info("Step 1: Extracting pages from PDF")
        
        def progress_callback(current: int, total: int) -> None:
            """Callback for PDF extraction progress logging.
            
            Args:
                current: Current page number being processed.
                total: Total number of pages in PDF.
            """
            percentage = int((current / total) * 100)
            logger.info(f"PDF extraction progress: {current}/{total} pages ({percentage}%)")
        
        self.pages = self.pdf_processor.extract_pages(
            self.config.pdf_path,
            self.config.image_dir,
            progress_callback=progress_callback
        )
        return self.pages
    
    def parse_table_of_contents(
        self,
        toc_text: Optional[str] = None,
        manual_toc: Optional[List[dict]] = None
    ) -> List[TableOfContentsEntry]:
        """Parse table of contents from text or manual input.
        
        Step 2 of the extraction pipeline. Accepts either raw TOC text
        to parse with DeepSeek API, or a manually structured TOC.
        Saves parsed TOC to JSON file.
        
        Args:
            toc_text: Raw table of contents text extracted from PDF.
                If provided, will be parsed using DeepSeek API.
            manual_toc: Manually structured TOC as list of dictionaries.
                Each dict should have: level, number, title, page_start, children.
        
        Returns:
            List of TableOfContentsEntry instances. Also stores in self.toc_entries.
            
        Raises:
            ValueError: If neither toc_text nor manual_toc is provided.
            
        Example:
            >>> # Using manual TOC
            >>> manual = [
            ...     {"level": 1, "number": "1", "title": "Introduction",
            ...      "page_start": 1, "children": []}
            ... ]
            >>> entries = extractor.parse_table_of_contents(manual_toc=manual)
            
            >>> # Using AI parsing
            >>> toc_text = "1. Introduction ... 5\\n1.1 Purpose ... 5"
            >>> entries = extractor.parse_table_of_contents(toc_text=toc_text)
        """
        logger.info("Step 2: Parsing table of contents")
        
        if manual_toc:
            # Use manually provided TOC
            logger.info(f"Using manually provided TOC with {len(manual_toc)} entries")
            self.toc_entries = [
                TableOfContentsEntry(**entry) for entry in manual_toc
            ]
        elif toc_text:
            # Parse TOC using DeepSeek API
            logger.info("Parsing TOC using DeepSeek API")
            with DeepSeekClient(self.config.deepseek) as client:
                self.toc_entries = client.parse_table_of_contents(toc_text)
        else:
            raise ValueError("Either toc_text or manual_toc must be provided")
        
        # Save TOC to file
        toc_data = {"toc": [entry.to_dict() for entry in self.toc_entries]}
        with open(self.config.toc_path, "w", encoding="utf-8") as f:
            json.dump(toc_data, f, ensure_ascii=False, indent=2)
        logger.info(f"TOC saved to {self.config.toc_path}")
        
        return self.toc_entries
    
    def extract_requirements_from_sections(self) -> RequirementsRegistry:
        """Extract requirements from all sections using DeepSeek AI.
        
        Step 3 of the extraction pipeline. Processes each section from the
        TOC, extracting and classifying requirements. Progress is logged
        for each section.
        
        Returns:
            Complete requirements registry with all sections and requirements.
            Also stores in self.registry.
            
        Raises:
            ValueError: If TOC hasn't been parsed or PDF hasn't been extracted.
            
        Example:
            >>> extractor.extract_pdf_pages()
            >>> extractor.parse_table_of_contents(manual_toc=toc)
            >>> registry = extractor.extract_requirements_from_sections()
            >>> print(f"Extracted {registry.total_requirements} requirements")
        """
        logger.info("Step 3: Extracting requirements from sections")
        
        if not self.toc_entries:
            raise ValueError("TOC must be parsed before extracting requirements")
        
        if not self.pages:
            raise ValueError("PDF must be extracted before processing sections")
        
        with DeepSeekClient(self.config.deepseek) as client:
            for i, toc_entry in enumerate(self.toc_entries):
                logger.info(f"Processing section {i+1}/{len(self.toc_entries)}: {toc_entry.number} {toc_entry.title}")
                
                # Find end page (next section start or end of document)
                end_page = None
                for next_entry in self.toc_entries[i+1:]:
                    if next_entry.page_start > toc_entry.page_start:
                        end_page = next_entry.page_start
                        break
                
                # Get section text
                section_text = self.pdf_processor.get_section_text(
                    self.pages,
                    toc_entry.page_start,
                    end_page
                )
                
                # Extract requirements using DeepSeek
                page_range = f"{toc_entry.page_start}-{end_page-1 if end_page else 'end'}"
                requirements = client.extract_requirements(
                    section_number=toc_entry.number,
                    section_title=toc_entry.title,
                    page_range=page_range,
                    section_text=section_text
                )
                
                # Create section object
                section = Section(
                    number=toc_entry.number,
                    title=toc_entry.title,
                    page_start=toc_entry.page_start,
                    page_end=end_page - 1 if end_page else None,
                    raw_text=section_text,
                    requirements=requirements
                )
                
                self.registry.add_section(section)
                
                logger.info(
                    f"Section {toc_entry.number}: extracted {len(requirements)} requirements"
                )
        
        logger.info(
            f"Extraction complete: {self.registry.total_requirements} total requirements "
            f"from {len(self.registry.sections)} sections"
        )
        
        return self.registry
    
    def save_registry(self) -> Path:
        """Save requirements registry to JSON file.
        
        Step 4 of the extraction pipeline. Serializes the complete requirements
        registry to JSON format and saves to configured output path.
        
        Returns:
            Path to the saved registry JSON file.
            
        Example:
            >>> registry_path = extractor.save_registry()
            >>> print(f"Saved to {registry_path}")
        """
        logger.info("Step 4: Saving requirements registry")
        
        registry_data = self.registry.to_dict()
        
        with open(self.config.registry_path, "w", encoding="utf-8") as f:
            json.dump(registry_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Requirements registry saved to {self.config.registry_path}")
        logger.info(f"Total requirements: {self.registry.total_requirements}")
        logger.info(f"Total sections: {len(self.registry.sections)}")
        
        return self.config.registry_path
    
    def run_full_extraction(
        self,
        toc_text: Optional[str] = None,
        manual_toc: Optional[List[dict]] = None
    ) -> Path:
        """Run the complete extraction pipeline from start to finish.
        
        Executes all steps in sequence: PDF extraction, TOC parsing, requirements
        extraction, and report generation. This is the primary entry point for
        complete document processing.
        
        Args:
            toc_text: Raw TOC text to parse with DeepSeek API (optional).
            manual_toc: Manually structured TOC as list of dictionaries (optional).
                One of toc_text or manual_toc must be provided.
        
        Returns:
            Path to the saved requirements registry JSON file.
            
        Side Effects:
            - Extracts PDF to self.pages
            - Parses TOC to self.toc_entries
            - Generates registry in self.registry
            - Saves registry JSON to config.registry_path
            - Saves TOC JSON to config.toc_path
            - Saves usage report to output_dir/usage_report.txt
            - Prints usage report to console
            
        Example:
            >>> config = ApplicationConfig()
            >>> extractor = RequirementsExtractor(config)
            >>> manual_toc = [
            ...     {"level": 1, "number": "1", "title": "Introduction",
            ...      "page_start": 1, "children": []}
            ... ]
            >>> registry_path = extractor.run_full_extraction(manual_toc=manual_toc)
        """
        logger.info("=" * 80)
        logger.info("Starting PDF Requirements Extraction")
        logger.info("=" * 80)
        
        # Step 1: Extract PDF pages
        self.extract_pdf_pages()
        
        # Step 2: Parse table of contents
        self.parse_table_of_contents(toc_text=toc_text, manual_toc=manual_toc)
        
        # Step 3: Extract requirements from sections
        self.extract_requirements_from_sections()
        
        # Step 4: Save registry
        registry_path = self.save_registry()
        
        logger.info("=" * 80)
        logger.info("Extraction Complete!")
        logger.info(f"Registry saved to: {registry_path}")
        logger.info(f"Images saved to: {self.config.image_dir}")
        logger.info("=" * 80)
        
        # Print and save usage report
        usage_report = get_usage_report()
        print("\n" + usage_report.format_report())
        
        # Save usage report to file
        usage_report_path = self.config.output_dir / "usage_report.txt"
        usage_report.save_to_file(usage_report_path)
        logger.info(f"Usage report saved to: {usage_report_path}")
        
        return registry_path


def create_extractor(
    pdf_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
    log_level: str = "INFO"
) -> RequirementsExtractor:
    """Factory function to create a configured extractor instance.
    
    Convenience function that creates an ApplicationConfig, optionally overrides
    paths, sets up logging, and returns a ready-to-use RequirementsExtractor.
    
    Args:
        pdf_path: Path to input PDF file. If None, uses config default.
        output_dir: Directory for output files. If None, uses config default.
        log_level: Logging level string ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL').
    
    Returns:
        Configured RequirementsExtractor instance ready for use.
        
    Example:
        >>> extractor = create_extractor(
        ...     pdf_path=Path("data/input/spec.pdf"),
        ...     output_dir=Path("data/output"),
        ...     log_level="DEBUG"
        ... )
        >>> registry_path = extractor.run_full_extraction(manual_toc=toc)
    """
    # Create configuration
    config = ApplicationConfig()
    
    # Override paths if provided
    if pdf_path:
        config.pdf_path = pdf_path
    if output_dir:
        config.output_dir = output_dir
    
    # Setup logging with appropriate level
    import logging
    level = getattr(logging, log_level.upper(), logging.INFO)
    setup_logger(
        log_file=config.logs_dir / "extraction.log",
        level=level
    )
    
    # Create and return extractor
    return RequirementsExtractor(config)
