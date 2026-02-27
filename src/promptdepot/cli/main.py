import typer
from .templates import templates_app
from .versions import versions_app

app = typer.Typer()

app.add_typer(templates_app, name="templates")
app.add_typer(versions_app, name="versions")
