from demand_radar.mvp_d2.query_pattern_library import DOMAIN_RECOMMENDED_QUERIES, QUERY_PATTERNS


def test_query_pattern_v2_contains_pain_workaround_complaint_manual_types():
    types = {pattern.query_type for pattern in QUERY_PATTERNS}
    assert {"pain_phrase", "workaround_phrase", "complaint_phrase", "manual_workflow"} <= types
    examples = [query for _, query in DOMAIN_RECOMMENDED_QUERIES]
    assert '"investment research workflow" "spreadsheet"' in examples
    assert '"portfolio monitoring" "hard to track"' in examples

