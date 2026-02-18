"""Test script for PDF requirements extraction with sample data."""

from pathlib import Path
from typing import List

from src.config import ApplicationConfig
from src.extractor import RequirementsExtractor
from src.logger import setup_logger
from src.models import TableOfContentsEntry
from src.usage_tracker import get_usage_report, reset_usage_report


def load_test_pages() -> List[str]:
    """Load test pages from markdown files."""
    test_dir = Path("data/test")
    pages = []
    
    for i in range(1, 4):
        page_file = test_dir / f"test_specification_page{i}.md"
        if page_file.exists():
            with open(page_file, encoding="utf-8") as f:
                pages.append(f.read())
        else:
            print(f"Warning: {page_file} not found")
    
    return pages


def create_test_toc() -> List[TableOfContentsEntry]:
    """Create test table of contents."""
    return [
        TableOfContentsEntry(
            level=1,
            number="1",
            title="Общие сведения",
            page_start=1,
            children=[]
        ),
        TableOfContentsEntry(
            level=2,
            number="1.1",
            title="Цели и задачи проекта",
            page_start=1,
            children=[]
        ),
        TableOfContentsEntry(
            level=2,
            number="1.2",
            title="Назначение системы",
            page_start=1,
            children=[]
        ),
        TableOfContentsEntry(
            level=1,
            number="2",
            title="Технические требования",
            page_start=2,
            children=[]
        ),
        TableOfContentsEntry(
            level=2,
            number="2.1",
            title="Требования к архитектуре",
            page_start=2,
            children=[]
        ),
        TableOfContentsEntry(
            level=2,
            number="2.2",
            title="Требования к производительности",
            page_start=2,
            children=[]
        ),
        TableOfContentsEntry(
            level=1,
            number="3",
            title="Функциональные требования",
            page_start=3,
            children=[]
        ),
        TableOfContentsEntry(
            level=2,
            number="3.1",
            title="Управление пользователями",
            page_start=3,
            children=[]
        ),
        TableOfContentsEntry(
            level=2,
            number="3.2",
            title="Управление проектами",
            page_start=3,
            children=[]
        ),
    ]


def main():
    """Run test extraction with sample data."""
    print("=" * 80)
    print("PDF REQUIREMENTS EXTRACTOR - TEST RUN")
    print("=" * 80)
    print()
    
    # Reset usage tracking
    reset_usage_report()
    
    # Setup logging
    setup_logger(
        log_file=Path("logs/test_extraction.log"),
        level="INFO"
    )
    
    # Create configuration
    config = ApplicationConfig()
    config.output_dir = Path("data/test_output")
    config.image_dir = Path("data/test_output/images")
    config.output_dir.mkdir(parents=True, exist_ok=True)
    
    print("[CONFIG] Configuration:")
    print(f"   Output directory: {config.output_dir}")
    print(f"   Registry file: {config.registry_filename}")
    print()
    
    # Create extractor
    extractor = RequirementsExtractor(config)
    
    # Load test pages (simulating PDF extraction)
    print("[LOADING] Loading test pages...")
    extractor.pages = load_test_pages()
    print(f"   [OK] Loaded {len(extractor.pages)} pages")
    print()
    
    # Create test TOC
    print("[TOC] Creating test table of contents...")
    extractor.toc_entries = create_test_toc()
    print(f"   [OK] Created TOC with {len(extractor.toc_entries)} entries")
    print()
    
    # Save TOC
    import json
    toc_data = {"toc": [entry.to_dict() for entry in extractor.toc_entries]}
    with open(config.toc_path, "w", encoding="utf-8") as f:
        json.dump(toc_data, f, ensure_ascii=False, indent=2)
    print(f"   [SAVED] TOC saved to: {config.toc_path}")
    print()
    
    # Extract requirements using DeepSeek API
    print("[API] Extracting requirements with DeepSeek API...")
    print("   This will make real API calls to DeepSeek")
    print()
    
    try:
        extractor.extract_requirements_from_sections()
        
        # Save registry
        registry_path = extractor.save_registry()
        
        print()
        print("=" * 80)
        print("[SUCCESS] TEST EXTRACTION COMPLETE!")
        print("=" * 80)
        print()
        print("[RESULTS] Results:")
        print(f"   Total sections processed: {len(extractor.registry.sections)}")
        print(f"   Total requirements extracted: {extractor.registry.total_requirements}")
        print()
        print("[OUTPUT] Output files:")
        print(f"   Registry: {registry_path}")
        print(f"   TOC: {config.toc_path}")
        print(f"   Logs: logs/test_extraction.log")
        print()
        
        # Display summary by section
        print("[SUMMARY] Requirements by section:")
        for section in extractor.registry.sections:
            print(f"   {section.full_title}: {len(section.requirements)} requirements")
        
        print()
        print("=" * 80)
        
        # Print usage report
        print()
        usage_report = get_usage_report()
        print(usage_report.format_report())
        
    except Exception as e:
        print()
        print("=" * 80)
        print(f"[ERROR] {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
