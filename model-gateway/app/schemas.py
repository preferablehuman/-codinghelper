from typing import Literal
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1)
    max_new_tokens: int = Field(default=1024, ge=1, le=65_536)
    json_mode: bool = False
    schema_name: Literal["problem_analysis", "problem_equivalence", "solution", "tests", "explanation"] | None = None


class GenerateResponse(BaseModel):
    text: str
    provider: str
    model: str
