import json
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.config  # noqa: F401 — load .env before other app imports use env
from app.config import GEMINI_FALLBACK_ON_QUOTA, GEMINI_MODEL
from app.database import Base, engine, get_db
from app.models import Recipe
from app.heuristic_recipe import draft_from_video_context
from app.gemini_extract import GeminiUpstreamError, extract_recipe_draft
from app.schemas import (
    ExtractFromVideoResponse,
    RecipeCreate,
    RecipeRead,
    RecipeUpdate,
    VideoExtractRequest,
    lists_to_json,
    row_to_read,
    utc_now,
)
from app.video_context import fetch_video_context

app = FastAPI(title="Recipe API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/recipes", response_model=list[RecipeRead])
def list_recipes(db: Annotated[Session, Depends(get_db)]) -> list[RecipeRead]:
    rows = db.scalars(select(Recipe).order_by(Recipe.updated_at.desc())).all()
    return [row_to_read(r) for r in rows]


@app.get("/recipes/{recipe_id}", response_model=RecipeRead)
def get_recipe(recipe_id: int, db: Annotated[Session, Depends(get_db)]) -> RecipeRead:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return row_to_read(recipe)


@app.post("/recipes/extract-from-video", response_model=ExtractFromVideoResponse)
def extract_recipe_from_video(body: VideoExtractRequest) -> ExtractFromVideoResponse:
    """Use yt-dlp for text, then Gemini (optional) or heuristics to build an editable recipe draft."""
    url = str(body.url)
    if len(url) > 2000:
        raise HTTPException(status_code=400, detail="URL too long")

    try:
        ctx = fetch_video_context(url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read video: {e}") from e

    if not ctx.as_prompt_block().strip():
        raise HTTPException(
            status_code=422,
            detail="No title, description, or captions found for this URL.",
        )

    used_ai = False
    extraction_note: str | None = None

    if body.use_ai:
        try:
            outcome = extract_recipe_draft(ctx)
            draft = outcome.draft
            used_ai = True
            if outcome.model_used != GEMINI_MODEL:
                extraction_note = (
                    f"Gemini used model “{outcome.model_used}” "
                    f"(configured model “{GEMINI_MODEL}” was unavailable)."
                )
        except GeminiUpstreamError as e:
            if e.status_code == 429 and GEMINI_FALLBACK_ON_QUOTA:
                draft = draft_from_video_context(ctx)
                extraction_note = (
                    f"{e} Loaded a heuristic draft instead — edit below, or uncheck “Use Gemini” next time."
                )
            else:
                raise HTTPException(status_code=e.status_code, detail=str(e)) from e
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Model error: {e}") from e
    else:
        draft = draft_from_video_context(ctx)

    return ExtractFromVideoResponse(
        title=draft.title,
        ingredients=draft.ingredients,
        steps=draft.steps,
        source_url=url,
        source_video_title=ctx.title or None,
        had_transcript=bool(ctx.transcript.strip()),
        had_description=bool(ctx.description.strip()),
        used_ai=used_ai,
        extraction_note=extraction_note,
    )


@app.post("/recipes", response_model=RecipeRead, status_code=201)
def create_recipe(body: RecipeCreate, db: Annotated[Session, Depends(get_db)]) -> RecipeRead:
    ing, st = lists_to_json(body.ingredients, body.steps)
    recipe = Recipe(title=body.title.strip(), ingredients=ing, steps=st)
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return row_to_read(recipe)


@app.patch("/recipes/{recipe_id}", response_model=RecipeRead)
def update_recipe(
    recipe_id: int,
    body: RecipeUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> RecipeRead:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")

    if body.title is not None:
        recipe.title = body.title.strip()
    if body.ingredients is not None:
        recipe.ingredients = json.dumps(body.ingredients)
    if body.steps is not None:
        recipe.steps = json.dumps(body.steps)
    recipe.updated_at = utc_now()

    db.commit()
    db.refresh(recipe)
    return row_to_read(recipe)


@app.delete("/recipes/{recipe_id}", status_code=204)
def delete_recipe(recipe_id: int, db: Annotated[Session, Depends(get_db)]) -> None:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail="Recipe not found")
    db.delete(recipe)
    db.commit()
