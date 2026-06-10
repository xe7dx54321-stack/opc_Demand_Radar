from demand_radar.config.load_config import load_configs


def test_stage1_configs_load() -> None:
    configs = load_configs("configs")

    assert configs["domain"]["project_name"] == "demand_radar"
    assert "ai_investment_research" in configs["domain"]["domains"]
    assert configs["sources"]["sources"][0]["name"] == "manual_import"
    assert configs["extraction"]["pain_extraction"]["default_mode"] == "rule_based"
    assert configs["extraction"]["pain_extraction"]["min_confidence"] == 0.65

