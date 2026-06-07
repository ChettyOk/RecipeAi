import app.nutrition as nutrition
from app.nutrition import compute_nutrition
from app.nutrition_parse import parse_stated_nutrition


def test_macros_colon_inline_format():
    text = """
    High protein chicken
    Macros: 670cal, 52g P, 40g C, 34g F
    Total Servings: 4
    """
    report = parse_stated_nutrition(text, servings=1)
    assert report is not None
    assert report.per_serving.calories == 670
    assert report.per_serving.protein_g == 52
    assert report.per_serving.carbs_g == 40
    assert report.per_serving.fat_g == 34
    assert report.servings == 4
    assert report.source == "Creator caption (stated macros)"


def test_per_tender_macros():
    text = """
    Macros for one (makes 8)
    396 calories
    38g C | 14g F | 32g P
    """
    report = parse_stated_nutrition(text, servings=1)
    assert report is not None
    assert report.per_serving.calories == 396
    assert report.servings == 8


def test_video_stated_macros_win_over_usda(monkeypatch):
    monkeypatch.setattr(nutrition, "USDA_API_KEY", "test-key")

    def fail_if_usda_used(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("USDA should not run when video-stated macros are present")

    monkeypatch.setattr(nutrition, "_estimate_line_usda", fail_if_usda_used)

    report = compute_nutrition(
        ["200 g chicken breast", "100 g cooked rice"],
        servings=2,
        context_text="Creator caption: Macros: 510cal, 44g P, 46g C, 12g F",
    )

    assert report.source == "Creator caption (stated macros)"
    assert report.per_serving.calories == 510
    assert report.per_serving.protein_g == 44
    assert report.per_serving.carbs_g == 46
    assert report.per_serving.fat_g == 12
