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
    ForeignKey,
    JSON,
    Float,
    ARRAY,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

from src.models import RequirementType, RequirementPriority

Base = declarative_base()


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
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")


class Document(Base):
    """Document model - represents uploaded PDF documents."""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    total_pages = Column(Integer, nullable=True)
    model_used = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime, default=func.now(), nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="documents")
    sections = relationship("Section", back_populates="document", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="document", cascade="all, delete-orphan")
    coverage_metrics = relationship("CoverageMetrics", back_populates="document", cascade="all, delete-orphan", uselist=False)


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
    
    requirement_id = Column(String(50), nullable=False, index=True)
    text = Column(Text, nullable=False)
    type = Column(String(50), nullable=True)  # Temporarily VARCHAR instead of ENUM
    priority = Column(String(50), nullable=True)  # Temporarily VARCHAR instead of ENUM
    page_number = Column(Integer, nullable=True)
    bbox = Column(JSON, nullable=True)  # Bounding box: {"x": 0, "y": 0, "width": 100, "height": 50}
    subitems = Column(JSON, nullable=True)  # List items if requirement is grouped
    
    # Review fields
    status = Column(String(50), default="pending", nullable=False, index=True)
    ai_suggested = Column(Text, nullable=False)  # Original AI text
    human_edited = Column(Text, nullable=True)  # Human-edited version
    edit_reason = Column(Text, nullable=True)
    edited_by = Column(String(255), nullable=True)
    edited_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="requirements")
    section = relationship("Section", back_populates="requirements")


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
