# type: ignore[attr-defined]

import typer
from github_tests_validator_app import __version__
from github_tests_validator_app.cli import dialogs
from rich.console import Console

app = typer.Typer(
    name="github_tests_validator_app",
    help="`github_tests_validator_app` is a Python cli/package",
    add_completion=True,
)
app.add_typer(dialogs.app, name="dialogs")
console = Console()


def version_callback(value: bool):
    """Prints the version of the package."""
    if value:
        console.print(
            f"[yellow]github_tests_validator_app[/] version: [bold blue]{__version__}[/]"
        )
        raise typer.Exit()
