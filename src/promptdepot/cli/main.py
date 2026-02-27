import typer
from promptdepot.cli.templates import templates_app
from promptdepot.cli.versions import versions_app

app = typer.Typer()

app.add_typer(templates_app, name="templates")
app.add_typer(versions_app, name="versions")
