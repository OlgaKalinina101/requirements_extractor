"""Common API schemas."""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ExtractionStatus(BaseModel):
    """Status information for ongoing extraction process."""

    status: str = Field(..., description="Current extraction status")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    current_step: str = Field(..., description="Current processing step")
    message: str = Field(..., description="Status message")


class ExtractionResult(BaseModel):
    """Result of completed extraction process."""

    success: bool = Field(..., description="Success status")
    message: str = Field(..., description="Result message")
    requirements_count: int = Field(..., ge=0, description="Number of requirements")
    sections_count: int = Field(..., ge=0, description="Number of sections")
    total_tokens: int = Field(..., ge=0, description="Total tokens used")
    total_cost: float = Field(..., ge=0, description="Total cost in USD")
    processing_time: float = Field(..., ge=0, description="Processing time in seconds")
    files: Dict[str, str] = Field(..., description="Generated file paths")
    model_used: Optional[str] = Field(None, description="AI model used")
    document_id: Optional[int] = Field(None, description="Database document ID")
