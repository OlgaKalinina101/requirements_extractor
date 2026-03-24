"""SQLAlchemy database models for requirements management system.

This module defines the database schema using SQLAlchemy ORM models.
Hierarchy: Project -> Document -> Section -> Requirement
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Date,
    ForeignKey,
    JSON,
    Float,
    ARRAY,
    Boolean,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

from src.models import RequirementType, RequirementPriority

Base = declarative_base()


class User(Base):
    """User model - for authentication and role-based access.

    Roles: admin, manager, department_head, user
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="user", nullable=False)  # admin, manager, department_head, user
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    assigned_requirements = relationship("Requirement", back_populates="assignee", foreign_keys="Requirement.assignee_id")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    requirement_history = relationship("RequirementHistory", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    """Project model - top-level grouping for documents.
    
    A project represents a real engineering project (e.g. a plant, a system).
    Multiple TT documents can belong to one project.
    """
    
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), nullable=True, unique=True, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active", nullable=False)
    requirement_manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    requirement_manager = relationship("User", foreign_keys=[requirement_manager_id])


class Document(Base):
    """Document model - represents uploaded PDF documents."""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    document_type = Column(String(100), nullable=True)  # Technical Specification, etc. (from dictionary)
    total_pages = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime, default=func.now(), nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="documents")
    sections = relationship("Section", back_populates="document", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="document", cascade="all, delete-orphan")
    coverage_metrics = relationship("CoverageMetrics", back_populates="document", cascade="all, delete-orphan", uselist=False)
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")


class Section(Base):
    """Section model - represents document sections.
    
    Attributes:
        id: Primary key
        document_id: Foreign key to documents table
        section_number: Section number (e.g., "1", "1.1")
        title: Section title
        page_start: Starting page number
        page_end: Ending page number
    """
    
    __tablename__ = "sections"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    section_number = Column(String(50), nullable=True)
    title = Column(Text, nullable=True)
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="sections")
    requirements = relationship("Requirement", back_populates="section", cascade="all, delete-orphan")


class Requirement(Base):
    """Requirement model - represents extracted requirements.
    
    Attributes:
        id: Primary key
        document_id: Foreign key to documents table
        section_id: Foreign key to sections table (optional)
        requirement_id: Unique requirement identifier (e.g., "REQ-1-015")
        text: Requirement text
        type: Requirement type (Technical, Functional, etc.)
        priority: Requirement priority (Mandatory, Recommended, Optional)
        page_number: Page number where requirement was found
        bbox: Bounding box coordinates (JSON)
        
        # Review fields
        status: Review status (pending, accepted, rejected, modified)
        ai_suggested: Original AI-suggested text
        human_edited: Human-edited text (if modified)
        edit_reason: Reason for editing
        edited_by: User who edited (for future use)
        edited_at: Edit timestamp
        
        created_at: Creation timestamp
    """
    
    __tablename__ = "requirements"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    parent_id = Column(Integer, ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True, index=True)
    
    requirement_id = Column(String(50), nullable=False, index=True)
    text = Column(Text, nullable=False)
    type = Column(String(50), nullable=True)  # Temporarily VARCHAR instead of ENUM
    priority = Column(String(50), nullable=True)  # Temporarily VARCHAR instead of ENUM
    page_number = Column(Integer, nullable=True)
    bbox = Column(JSON, nullable=True)  # Bounding box: {"x": 0, "y": 0, "width": 100, "height": 50}
    subitems = Column(JSON, nullable=True)  # List items if requirement is grouped
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    discipline = Column(String(100), nullable=True, index=True)
    deadline = Column(Date, nullable=True)  # Due date for execution
    verification_method = Column(String(100), nullable=True)  # Analysis, Test, Inspection, Demonstration (from dictionary)
    lifecycle_status = Column(String(100), nullable=True)  # extracted, verification, accepted, assigned, in_progress, completed, closed

    # Review fields
    status = Column(String(50), default="pending", nullable=False, index=True)
    ai_suggested = Column(Text, nullable=False)  # Original AI text
    human_edited = Column(Text, nullable=True)  # Human-edited version
    edit_reason = Column(Text, nullable=True)
    source_quote = Column(Text, nullable=True)  # Short verbatim quote from source
    edited_by = Column(String(255), nullable=True)
    edited_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="requirements")
    section = relationship("Section", back_populates="requirements")
    parent = relationship("Requirement", remote_side="Requirement.id", back_populates="children")
    children = relationship("Requirement", back_populates="parent", cascade="all, delete-orphan")
    assignee = relationship("User", back_populates="assigned_requirements", foreign_keys=[assignee_id])
    comments = relationship("Comment", back_populates="requirement", cascade="all, delete-orphan")
    history = relationship("RequirementHistory", back_populates="requirement", cascade="all, delete-orphan")
    outgoing_links = relationship(
        "RequirementLink",
        foreign_keys="RequirementLink.source_requirement_id",
        back_populates="source_requirement",
        cascade="all, delete-orphan",
    )
    incoming_links = relationship(
        "RequirementLink",
        foreign_keys="RequirementLink.target_requirement_id",
        back_populates="target_requirement",
        cascade="all, delete-orphan",
    )
    assignments = relationship(
        "Assignment", back_populates="requirement", cascade="all, delete-orphan",
        order_by="Assignment.assigned_at.desc()",
    )


class Assignment(Base):
    """Assignment — links a requirement to an assignee (executor).

    Each (re-)assignment creates a new row; only the latest active row
    represents the current assignment.  Previous rows are kept for audit
    (is_active=False).

    Fields per ТЗ: requirement_id, assignee_id, assigned_by_id, assigned_at, deadline.
    """
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime, default=func.now(), nullable=False)
    deadline = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    requirement = relationship("Requirement", back_populates="assignments")
    assignee = relationship("User", foreign_keys=[assignee_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])


class CoverageMetrics(Base):
    """Coverage metrics model - stores document coverage statistics.
    
    Attributes:
        id: Primary key
        document_id: Foreign key to documents table
        total_pages: Total pages in document
        processed_pages: Number of processed pages
        skipped_pages: Array of skipped page numbers
        coverage_percent: Coverage percentage (0-100)
        requirements_count: Total number of requirements
        requirements_by_type: JSON with counts by type
        calculated_at: Calculation timestamp
    """
    
    __tablename__ = "coverage_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    total_pages = Column(Integer, nullable=False)
    processed_pages = Column(Integer, nullable=False)
    skipped_pages = Column(ARRAY(Integer), nullable=True)  # Array of page numbers
    coverage_percent = Column(Float, nullable=False)
    requirements_count = Column(Integer, nullable=False)
    requirements_by_type = Column(JSON, nullable=True)  # {"Technical": 34, "Functional": 28, ...}
    
    calculated_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="coverage_metrics")


class DictionaryItem(Base):
    """Generic dictionary item for editable reference data.

    Covers requirement types, priorities, and lifecycle statuses.
    The `dict_type` column distinguishes which dictionary an item belongs to:
      - 'requirement_types'
      - 'priorities'
      - 'statuses'
    """
    __tablename__ = "dictionary_items"

    id = Column(Integer, primary_key=True, index=True)
    dict_type = Column(String(50), nullable=False, index=True)
    code = Column(String(100), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(50), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)


class Comment(Base):
    """Comment on a requirement - for assignees to add notes."""
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    requirement = relationship("Requirement", back_populates="comments")
    author = relationship("User", back_populates="comments")


class RequirementLink(Base):
    """Link between two requirements (Depends on, Conflicts with, Derived from, etc.)."""
    __tablename__ = "requirement_links"

    id = Column(Integer, primary_key=True, index=True)
    source_requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    target_requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    link_type = Column(String(50), nullable=False)  # depends_on, conflicts_with, derived_from, parent_child (from dictionary)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    source_requirement = relationship("Requirement", foreign_keys=[source_requirement_id], back_populates="outgoing_links")
    target_requirement = relationship("Requirement", foreign_keys=[target_requirement_id], back_populates="incoming_links")


class RequirementHistory(Base):
    """Audit log for requirement changes - who, when, what changed."""
    __tablename__ = "requirement_history"

    id = Column(Integer, primary_key=True, index=True)
    requirement_id = Column(Integer, ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)  # accepted, rejected, edited, assigned, status_changed, etc.
    field_name = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    requirement = relationship("Requirement", back_populates="history")
    user = relationship("User", back_populates="requirement_history")


class DocumentPage(Base):
    """Raw page text and word-level bounding boxes for a document page.

    Populated during PDF extraction for every page — regardless of whether
    the page was text-based or required OCR.  The ``text_blocks`` JSON array
    is the canonical source for frontend highlighting: each element carries
    the recognised text fragment and its position on the page.

    Attributes:
        id:            Primary key.
        document_id:   FK to documents.
        page_number:   1-based page index.
        raw_text:      Full page text as a single string (for FTS / LLM).
        text_blocks:   JSON list of dicts:
                       [{text, x0, y0, x1, y1, block_type}, ...]
                       where x0/y0/x1/y1 are in PDF points (72 dpi).
        is_ocr:        True when the page had no embedded text and was
                       processed by easyocr instead of pymupdf.
        created_at:    Row creation timestamp.
    """

    __tablename__ = "document_pages"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=True)
    text_blocks = Column(JSON, nullable=True)
    is_ocr = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    document = relationship("Document", back_populates="pages")


class Prompt(Base):
    """AI prompt templates stored in DB. Editable by admin via UI.

    instruction     — editable part (role, task rules)
    response_format — read-only JSON schema / output format
    user_template   — editable user message template with {variables}
    """
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=True)
    version = Column(String(50), nullable=True)
    instruction = Column(Text, nullable=True)
    response_format = Column(Text, nullable=True)
    user_template = Column(Text, nullable=True)
    temperature = Column(Float, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    updated_at = Column(DateTime, nullable=True)
