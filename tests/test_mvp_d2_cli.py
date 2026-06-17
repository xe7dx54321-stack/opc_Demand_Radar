from typer.testing import CliRunner

from demand_radar.cli import app


runner = CliRunner()


def test_mvp_d2_commands_are_registered():
    for command in [
        "diagnose-expansion-rejects",
        "build-calibrated-query-plan",
        "run-calibrated-expansion",
        "compare-expansion-v1-v2",
        "run-mvp-d2",
        "build-mvp-d2-report",
    ]:
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0

