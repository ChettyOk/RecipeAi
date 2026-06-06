"""Tests for BMI-aware daily target calculations."""

from app.insights import bmi_category, compute_bmi, compute_targets
from app.schemas import ProfileBase


def _profile(**kwargs) -> ProfileBase:
    defaults = dict(
        height_cm=170,
        weight_kg=70,
        age=30,
        sex="female",
        activity_level="moderate",
        goal="maintain",
        allergies=[],
        dietary_prefs=[],
    )
    defaults.update(kwargs)
    return ProfileBase(**defaults)


def test_bmi_who_categories():
    assert bmi_category(17.0) == "underweight"
    assert bmi_category(22.0) == "normal"
    assert bmi_category(27.0) == "overweight"
    assert bmi_category(32.0) == "obese"


def test_bmi_formula():
    # 70 kg, 170 cm → BMI ≈ 24.2
    assert round(compute_bmi(70, 170), 1) == 24.2


def test_mifflin_st_jeor_maintain_includes_bmi():
    t = compute_targets(_profile(goal="maintain"))
    assert t is not None
    assert t.bmi == 24.2
    assert t.bmi_category == "normal"
    assert t.bmr is not None
    raw_bmr = 10 * 70 + 6.25 * 170 - 5 * 30 - 161
    assert t.tdee == round(raw_bmr * 1.55)
    assert t.target_calories == t.tdee
    assert "WHO BMI" in (t.basis or "")
    assert "Mifflin" in (t.basis or "")


def test_lose_normal_uses_nih_500_deficit():
    t = compute_targets(_profile(goal="lose", weight_kg=70))
    assert t is not None
    assert t.target_calories == t.tdee - 500


def test_lose_underweight_no_deficit():
    t = compute_targets(_profile(goal="lose", weight_kg=50, height_cm=170))
    assert t is not None
    assert t.bmi_category == "underweight"
    assert t.target_calories == t.tdee


def test_lose_obese_uses_larger_deficit():
    t = compute_targets(_profile(goal="lose", weight_kg=95, height_cm=170))
    assert t is not None
    assert t.bmi_category == "obese"
    assert t.target_calories == t.tdee - 750


def test_lose_morbid_obese_caps_at_1000_deficit():
    t = compute_targets(_profile(goal="lose", weight_kg=110, height_cm=170))
    assert t is not None
    assert t.bmi is not None and t.bmi >= 35
    assert t.target_calories == max(t.tdee - 1000, 1200)


def test_minimum_calories_female_floor():
    t = compute_targets(_profile(goal="lose", weight_kg=45, height_cm=155, age=50, sex="female", activity_level="sedentary"))
    assert t is not None
    assert t.target_calories >= 1200


def test_minimum_calories_male_floor():
    t = compute_targets(_profile(goal="lose", sex="male", weight_kg=55, height_cm=165, activity_level="sedentary"))
    assert t is not None
    assert t.target_calories >= 1500


def test_gain_underweight_larger_surplus():
    t = compute_targets(_profile(goal="gain", weight_kg=50, height_cm=170))
    assert t is not None
    assert t.bmi_category == "underweight"
    assert t.target_calories == t.tdee + 500


def test_macros_within_reasonable_amdr():
    t = compute_targets(_profile(goal="lose", weight_kg=85, height_cm=175, sex="male"))
    assert t is not None
    cal = t.target_calories or 0
    protein_cal = (t.protein_g or 0) * 4
    fat_cal = (t.fat_g or 0) * 9
    carbs_cal = (t.carbs_g or 0) * 4
    total_macro_cal = protein_cal + fat_cal + carbs_cal
    assert abs(total_macro_cal - cal) <= cal * 0.08  # rounding tolerance
    assert (t.protein_g or 0) >= 1.6 * 85  # elevated protein when cutting
    assert (t.carbs_g or 0) >= 130  # IOM minimum when calories allow
