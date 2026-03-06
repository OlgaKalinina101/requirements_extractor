"""Data models for the PDF requirements extractor.

This module defines the core data structures used throughout the application
for representing requirements, document structure, and extracted data.

Classes:
    RequirementType: Enum of requirement types (technical, functional, etc).
    RequirementPriority: Enum of priority levels (mandatory, recommended, optional).
    Requirement: Single requirement with metadata.
    TableOfContentsEntry: Hierarchical TOC structure.
    Section: Document section with requirements.
    RequirementsRegistry: Complete collection of extracted requirements.
"""

# Standard library imports
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class RequirementType(str, Enum):
    """Classification of requirement types.
    
    Categorizes requirements by their functional purpose and domain.
    Used for filtering and reporting.
    
    Attributes:
        SUPPLY: Supply composition, delivery scope, equipment list.
        TECHNICAL: Technical parameters, characteristics, specifications.
        FUNCTIONAL: Functional behavior, operations, capabilities.
        PERFORMANCE: Performance metrics, throughput, response times.
        SAFETY: Safety requirements, protective measures, risk mitigation.
        DOCUMENTATION: Documentation, reporting, record-keeping requirements.
        INTERFACE: Interface specifications, connections, protocols.
        CONSTRAINT: Constraints, limitations, boundary conditions.
        PROCESS: Process requirements, workflows, procedures.
        UNKNOWN: Cannot be confidently classified.
    """
    
    SUPPLY = "Supply"
    TECHNICAL = "Technical"
    FUNCTIONAL = "Functional"
    PERFORMANCE = "Performance"
    SAFETY = "Safety"
    DOCUMENTATION = "Documentation"
    INTERFACE = "Interface"
    CONSTRAINT = "Constraint"
    PROCESS = "Process"
    UNKNOWN = "Unknown"


class RequirementPriority(str, Enum):
    """Priority level for requirements implementation.
    
    Defines urgency and importance of requirements for planning
    and resource allocation.
    
    Attributes:
        MANDATORY: Must be implemented (critical requirements).
        RECOMMENDED: Should be implemented (important but not critical).
        OPTIONAL: Nice to have (low priority).
        UNKNOWN: Cannot be confidently determined.
    """
    
    MANDATORY = "Mandatory"
    RECOMMENDED = "Recommended"
    OPTIONAL = "Optional"
    UNKNOWN = "Unknown"


@dataclass
class Requirement:
    """Single requirement extracted from specification document.
    
    Represents an atomic requirement with all associated metadata including
    classification, priority, source references, and location information.
    
    Attributes:
        id: Unique identifier (e.g., 'REQ-1-001').
        text: Full requirement text (normalized, close to source).
        type: Classification of requirement type.
        priority: Implementation priority level.
        reference: Optional reference to standards/documents.
        page_number: Optional page number where found (deprecated, use source_page).
        section: Optional section identifier (deprecated, use section_number).
        source_page: Page number where requirement was found (1-based).
        section_number: Section identifier (e.g., '3.2.1').
        source_type: Source of requirement - 'text' or 'image'.
        source_quote: Short verbatim quote from source document (NEW).
        source_fragment: Description of location in section (e.g., 'table', 'list_item') (NEW).
        confidence: AI confidence score 0.0-1.0 (NEW).
        extraction_basis: How requirement was extracted (NEW).
    """
    
    id: str
    text: str
    type: RequirementType
    priority: RequirementPriority = RequirementPriority.MANDATORY
    reference: Optional[str] = None
    page_number: Optional[int] = None  # Deprecated, use source_page
    section: Optional[str] = None  # Deprecated, use section_number
    source_page: Optional[int] = None  # Page number (1-based)
    section_number: Optional[str] = None  # Section identifier
    source_type: str = "text"  # 'text' or 'image'
    
    # NEW FIELDS for improved extraction quality
    subitems: List[str] = field(default_factory=list)  # List items if requirement is grouped
    source_quote: Optional[str] = None  # Verbatim quote from document
    source_fragment: Optional[str] = None  # Location description (table/list/paragraph)
    visual_requirement_class: Optional[str] = None  # For images: signal_table|equipment_list|callout_note|layout_constraint
    confidence: float = 1.0  # AI confidence 0.0-1.0
    extraction_basis: Optional[str] = None  # explicit|list_item|list_block|table|inferred_from_mandatory_context|image_text
    
    def to_dict(self) -> Dict[str, any]:
        """Convert requirement to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation with all fields. Enum values are
            converted to their string values.
        """
        return {
            "id": self.id,
            "text": self.text,
            "type": self.type.value,
            "priority": self.priority.value,
            "reference": self.reference,
            "page_number": self.source_page or self.page_number,  # Backward compatibility
            "section": self.section_number or self.section,  # Backward compatibility
            "source_page": self.source_page,
            "section_number": self.section_number,
            "source_type": self.source_type,
            "subitems": self.subitems,
            "source_quote": self.source_quote,
            "source_fragment": self.source_fragment,
            "visual_requirement_class": self.visual_requirement_class,
            "confidence": self.confidence,
            "extraction_basis": self.extraction_basis,
        }


@dataclass
class TableOfContentsEntry:
    """Single entry in hierarchical table of contents structure.
    
    Represents a section in the document's table of contents with support
    for nested subsections.
    
    Attributes:
        level: Nesting level (1 = top level, 2 = subsection, etc).
        number: Section number (e.g., '1', '1.1', '1.1.1').
        title: Section title/heading.
        page_start: Starting page number.
        children: List of nested subsections.
    """
    
    level: int
    number: str
    title: str
    page_start: int
    children: List['TableOfContentsEntry'] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, any]:
        """Convert TOC entry to dictionary for JSON serialization.
        
        Recursively converts nested children to dictionaries.
        
        Returns:
            Dictionary representation including nested children.
        """
        return {
            "level": self.level,
            "number": self.number,
            "title": self.title,
            "page_start": self.page_start,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class Section:
    """Document section with extracted requirements and metadata.
    
    Represents a logical section of the document (typically from TOC)
    with all requirements extracted from that section.
    
    Attributes:
        number: Section number (e.g., '1', '1.1').
        title: Section title.
        page_start: Starting page number.
        page_end: Ending page number (None if not known).
        raw_text: Raw extracted text from this section.
        requirements: List of requirements found in this section.
    """
    
    number: str
    title: str
    page_start: int
    page_end: Optional[int]
    raw_text: str
    requirements: List[Requirement] = field(default_factory=list)
    images: List[Dict] = field(default_factory=list)  # Image metadata for this section
    
    @property
    def page_range(self) -> str:
        """Get formatted page range for display.
        
        Returns:
            Formatted string like '1-5' or '1-end' if page_end is None.
        """
        if self.page_end:
            return f"{self.page_start}-{self.page_end}"
        return f"{self.page_start}-end"
    
    @property
    def full_title(self) -> str:
        """Get full section title including number.
        
        Returns:
            Formatted string like '1.1 Introduction'.
        """
        return f"{self.number} {self.title}"
    
    def to_dict(self) -> Dict[str, any]:
        """Convert section to dictionary for JSON serialization.
        
        Includes all requirements and a preview of raw text (truncated
        to 500 characters for readability).
        
        Returns:
            Dictionary representation with requirements and text preview.
        """
        return {
            "section": self.full_title,
            "page_range": self.page_range,
            "requirements": [req.to_dict() for req in self.requirements],
            "raw_text_preview": self.raw_text[:500] + "..." if len(self.raw_text) > 500 else self.raw_text,
        }


@dataclass
class RequirementsRegistry:
    """Complete registry of all extracted requirements from a document.
    
    Aggregates all sections and provides metadata about the complete
    extraction result.
    
    Attributes:
        sections: List of all document sections with requirements.
        total_requirements: Total count of requirements across all sections.
    """
    
    sections: List[Section] = field(default_factory=list)
    total_requirements: int = 0
    
    def add_section(self, section: Section) -> None:
        """Add a section to the registry and update totals.
        
        Automatically updates the total_requirements counter.
        
        Args:
            section: Section instance to add.
        """
        self.sections.append(section)
        self.total_requirements += len(section.requirements)
    
    def to_dict(self) -> Dict[str, any]:
        """Convert entire registry to dictionary for JSON serialization.
        
        Includes metadata summary and all sections with requirements.
        
        Returns:
            Dictionary with 'metadata' and 'sections' keys. Metadata includes
            total counts for sections and requirements.
        """
        return {
            "metadata": {
                "total_sections": len(self.sections),
                "total_requirements": self.total_requirements,
            },
            "sections": [section.to_dict() for section in self.sections],
        }
