import pytest

from torquay_pipeline.building_heights import HeightPolicy, parse_height, resolve_building_height


@pytest.mark.parametrize(
    ("raw", "expected", "unit"),
    [
        ("8", 8.0, "metres"),
        ("12 m", 12.0, "metres"),
        ("10 ft", 3.048, "feet"),
        ("10' 6\"", 3.2004, "feet_inches"),
        ("78 inches", 1.9812, "inches"),
    ],
)
def test_parses_explicit_single_heights(raw, expected, unit):
    parsed = parse_height(raw)
    assert parsed is not None
    assert parsed[0] == pytest.approx(expected)
    assert parsed[1] == unit


@pytest.mark.parametrize("raw", ["10;12", "8-10", "~8", "NaN", "Infinity", "0", "-2", ""])
def test_rejects_ambiguous_or_nonpositive_height_forms(raw):
    assert parse_height(raw) is None


def test_height_policy_prefers_tag_then_levels_then_default_and_records_clamps():
    policy = HeightPolicy(maximum_height_m=150)
    tagged = resolve_building_height({"height": "600 ft", "building:levels": "2"}, policy)
    assert tagged.method == "osm_height"
    assert tagged.height_m == 150
    assert tagged.clamp == "clamped_high"
    assert tagged.confidence == "tagged_but_unverified"

    levels = resolve_building_height({"height": "10;12", "building:levels": "4"}, policy)
    assert levels.method == "estimated_levels"
    assert levels.height_m == 12
    assert "ambiguous" in (levels.fallback_reason or "")

    default = resolve_building_height({"building:levels": "2.5"}, policy)
    assert default.method == "estimated_default"
    assert default.height_m == 8
    assert default.raw_levels == "2.5"
