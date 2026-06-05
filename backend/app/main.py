import json
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.config as config  # noqa: F401 — load .env before other app imports use env
from app.database import ensure_schema, get_db
from app.gemini_extract import GeminiUpstreamError
from app.insights import build_insights, compute_targets
from app.models import Profile, Recipe
from app.nutrition import compute_nutrition
from app.nutrition_portion import portion_nutrition
from app.pipeline import run_pipeline
from app.video_urls import normalize_video_url
from app.schemas import (
    ExtractFromVideoResponse,
    InsightsRequest,
    NutritionReport,
    NutritionRequest,
    PortionRequest,
    PortionResponse,
    ProfileBase,
    ProfileRead,
    RecipeCreate,
    RecipeInsights,
    RecipeRead,
    RecipeUpdate,
    VideoExtractRequest,
    lists_to_json,
    profile_row_to_base,
    row_to_read,
    utc_now,
)

app = FastAPI(title="Recipe API", version="0.2.0")

_default_origins = ["http://127.0.0.1:5173", "http://localhost:5173"]
_extra = [o.strip() for o in config.EXTRA_CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    ensure_schema()


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "ai": bool(config.GEMINI_API_KEY),
        "media_pipeline": config.ENABLE_MEDIA_PIPELINE and config.ffmpeg_available(),
        "ffmpeg": config.ffmpeg_available(),
        "nutrition": config.ENABLE_NUTRITION,
        "nutrition_usda": bool(config.USDA_API_KEY),
        "nutrition_gemini": bool(config.GEMINI_API_KEY),
        "supported_video_platforms": ["tiktok", "youtube", "instagram", "facebook"],
    }


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
    """Pipeline: yt-dlp + (optional) ffmpeg/Gemini transcription & frame vision -> structured recipe."""
    url = normalize_video_url(str(body.url))
    if len(url) > 2000:
        raise HTTPException(status_code=400, detail="URL too long")

    try:
        result = run_pipeline(url, use_ai=body.use_ai, use_media=body.use_media)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except GeminiUpstreamError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Extraction failed: {e}") from e

    draft = result.draft

    nutrition: NutritionReport | None = None
    want_nutrition = config.ENABLE_NUTRITION if body.compute_nutrition is None else body.compute_nutrition
    if want_nutrition and draft.ingredients:
        nutrition = compute_nutrition(
            draft.ingredients,
            draft.servings,
            context_text=result.source_context_text,
        )
        if nutrition.servings and (draft.servings is None or draft.servings == 1):
            draft.servings = nutrition.servings
        result.steps_log.append(f"computed nutrition ({nutrition.source or 'estimate'})")

    return ExtractFromVideoResponse(
        title=draft.title,
        ingredients=draft.ingredients,
        steps=draft.steps,
        prep_time_min=draft.prep_time_min,
        cook_time_min=draft.cook_time_min,
        servings=draft.servings,
        dietary_flags=draft.dietary_flags,
        source_url=url,
        source_platform=result.platform,
        source_video_title=result.source_video_title,
        had_transcript=result.had_transcript,
        had_description=result.had_description,
        had_audio_transcription=result.had_audio_transcription,
        had_frame_vision=result.had_frame_vision,
        used_ai=result.used_ai,
        nutrition=nutrition,
        pipeline_steps=result.steps_log,
        extraction_note=result.note,
        source_context_text=result.source_context_text,
        thumbnail_url=result.thumbnail_url,
    )


@app.post("/nutrition", response_model=NutritionReport)
def nutrition_for_ingredients(body: NutritionRequest) -> NutritionReport:
    """Recompute nutrition for an edited ingredient list (used by the serving adjuster / edits)."""
    if not config.ENABLE_NUTRITION:
        return NutritionReport(servings=body.servings, notes=["Nutrition is disabled on the server."])
    return compute_nutrition(body.ingredients, body.servings, context_text=body.context_text)


@app.post("/nutrition/portion", response_model=PortionResponse)
def nutrition_portion(body: PortionRequest) -> PortionResponse:
    """Scale per-serving nutrition to a user portion (g, kg, ml, oz, cups, or servings)."""
    portion, factor, warning = portion_nutrition(body.nutrition, body.amount, body.unit)
    return PortionResponse(portion=portion, scale_factor=round(factor, 4), warning=warning)


def _get_profile_base(db: Session) -> ProfileBase | None:
    row = db.get(Profile, 1)
    if row is None:
        return None
    return profile_row_to_base(row)


@app.get("/profile", response_model=ProfileRead)
def get_profile(db: Annotated[Session, Depends(get_db)]) -> ProfileRead:
    base = _get_profile_base(db)
    if base is None:
        return ProfileRead(targets=None)
    return ProfileRead(**base.model_dump(), targets=compute_targets(base))


@app.put("/profile", response_model=ProfileRead)
def put_profile(body: ProfileBase, db: Annotated[Session, Depends(get_db)]) -> ProfileRead:
    row = db.get(Profile, 1)
    if row is None:
        row = Profile(id=1)
        db.add(row)
    row.height_cm = body.height_cm
    row.weight_kg = body.weight_kg
    row.age = body.age
    row.sex = body.sex
    row.activity_level = body.activity_level
    row.goal = body.goal
    row.allergies = json.dumps(body.allergies)
    row.dietary_prefs = json.dumps(body.dietary_prefs)
    row.updated_at = utc_now()
    db.commit()
    return ProfileRead(**body.model_dump(), targets=compute_targets(body))


@app.post("/insights", response_model=RecipeInsights)
def insights(body: InsightsRequest, db: Annotated[Session, Depends(get_db)]) -> RecipeInsights:
    """Personalized insights, allergy warnings, and substitution suggestions for a recipe/draft."""
    profile = _get_profile_base(db)
    return build_insights(body.ingredients, body.nutrition, body.servings, profile)


def _apply_create(body: RecipeCreate) -> Recipe:
    ing, st = lists_to_json(body.ingredients, body.steps)
    return Recipe(
        title=body.title.strip(),
        ingredients=ing,
        steps=st,
        prep_time_min=body.prep_time_min,
        cook_time_min=body.cook_time_min,
        servings=body.servings,
        dietary_flags=json.dumps(body.dietary_flags),
        nutrition=body.nutrition.model_dump_json() if body.nutrition else None,
        source_url=body.source_url,
        source_platform=body.source_platform,
        source_context_text=body.source_context_text,
        thumbnail_url=body.thumbnail_url,
    )


@app.post("/recipes", response_model=RecipeRead, status_code=201)
def create_recipe(body: RecipeCreate, db: Annotated[Session, Depends(get_db)]) -> RecipeRead:
    recipe = _apply_create(body)
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
    if body.prep_time_min is not None:
        recipe.prep_time_min = body.prep_time_min
    if body.cook_time_min is not None:
        recipe.cook_time_min = body.cook_time_min
    if body.servings is not None:
        recipe.servings = body.servings
    if body.dietary_flags is not None:
        recipe.dietary_flags = json.dumps(body.dietary_flags)
    if body.nutrition is not None:
        recipe.nutrition = body.nutrition.model_dump_json()
    if body.source_context_text is not None:
        recipe.source_context_text = body.source_context_text
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
