from typer.testing import CliRunner

from demand_radar.cli import app


runner = CliRunner()


def test_mvp_d_commands_are_registered():
    for command in [
        "run-mvp-d",
        "select-expansion-seeds",
        "build-seeded-query-plan",
        "run-seeded-acquisition",
        "run-expansion-extraction",
        "build-demand-themes",
        "build-mvp-d-report",
    ]:
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0

