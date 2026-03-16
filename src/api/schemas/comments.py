"""Comments API schemas."""

from pydantic import BaseModel, Field


class CommentRequest(BaseModel):
    """Request model for adding a comment."""

    text: str = Field(..., min_length=1, max_length=2000, description="Comment text")
