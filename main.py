"""Main entry point for the PDF requirements extractor."""

from pathlib import Path

from src.extractor import create_extractor


def main():
    """Run the requirements extraction process."""
    
    # Manual TOC for testing (since we don't have the actual PDF)
    # This is a sample structure - replace with actual TOC or use API parsing
    manual_toc = [
        {
            "level": 1,
            "number": "1",
            "title": "Общие сведения",
            "page_start": 1,
            "children": []
        },
        {
            "level": 2,
            "number": "1.1",
            "title": "Цели и задачи проекта",
            "page_start": 1,
            "children": []
        },
        {
            "level": 1,
            "number": "2",
            "title": "Технические требования",
            "page_start": 2,
            "children": []
        },
    ]
    
    # Create extractor
    extractor = create_extractor(
        pdf_path=Path("data/input/specification.pdf"),
        output_dir=Path("data/output"),
        log_level="INFO"
    )
    
    # Run extraction
    try:
        registry_path = extractor.run_full_extraction(manual_toc=manual_toc)
        print(f"\n✅ Extraction complete! Registry saved to: {registry_path}")
        print(f"📊 Total requirements: {extractor.registry.total_requirements}")
        print(f"📁 Total sections: {len(extractor.registry.sections)}")
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        raise


if __name__ == "__main__":
    main()
