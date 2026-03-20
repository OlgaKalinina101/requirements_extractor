"""Pydantic schemas for prompts API."""

from pydantic import BaseModel


class UpdatePromptRequest(BaseModel):
    instruction: str
    user_template: str
