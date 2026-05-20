import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field, HttpUrl, field_validator


class RecipeBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    ingredients: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)

    @field_validator("title", mode="before")
    @classmethod
    def title_strip(cls, v: str) -> str:
        return str(v).strip()

    @field_validator("ingredients", "steps", mode="before")
    @classmethod
    def strip_strings(cls, v: list[str]) -> list[str]:
        if not isinstance(v, list):
            raise TypeError("expected a list of strings")
        return [str(x).strip() for x in v if str(x).strip()]


class RecipeCreate(RecipeBase):
    pass


class RecipeUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    ingredients: list[str] | None = None
    steps: list[str] | None = None


class RecipeRead(RecipeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoExtractRequest(BaseModel):
    url: HttpUrl
    use_ai: bool = Field(
        default=True,
        description="If true, call Google Gemini to structure the recipe. If false, use heuristics only (no API usage).",
    )


class ExtractFromVideoResponse(RecipeBase):
    """Draft recipe from a video URL; not saved until the client POSTs /recipes."""

    source_url: str = Field(..., max_length=2000)
    source_video_title: str | None = Field(default=None, max_length=500)
    had_transcript: bool = False
    had_description: bool = False
    used_ai: bool = False
    extraction_note: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional note when heuristic fallback or alternate Gemini model was used.",
    )


def lists_to_json(ingredients: list[str], steps: list[str]) -> tuple[str, str]:
    return json.dumps(ingredients), json.dumps(steps)


def row_to_read(recipe) -> RecipeRead:
    return RecipeRead(
        id=recipe.id,
        title=recipe.title,
        ingredients=json.loads(recipe.ingredients),
        steps=json.loads(recipe.steps),
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
