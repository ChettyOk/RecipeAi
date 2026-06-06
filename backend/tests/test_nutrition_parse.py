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
