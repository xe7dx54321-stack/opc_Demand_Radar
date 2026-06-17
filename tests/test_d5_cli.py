"""D5 CLI tests."""
from __future__ import annotations

from typer.testing import CliRunner

from demand_radar.cli import app


def test_d5_commands_are_registered() -> None:
    runner = CliRunner()

    for command in ["run-d5", "build-demand-themes", "build-demand-themes-d5", "build-d5-report"]:
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0
