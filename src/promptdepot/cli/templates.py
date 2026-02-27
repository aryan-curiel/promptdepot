import typer
from rich.console import Console
from rich.table import Table

from promptdepot.stores.core import TemplateStore

from .utils import get_store

templates_app = typer.Typer(help="Manage prompt templates.")
console = Console()


@templates_app.command("create")
def templates_create() -> None:
    """Create a new prompt template."""
    store: TemplateStore = get_store()
    template_id = typer.prompt("Enter a unique template ID")
    try:
        store.create_template(template_id=template_id)
        console.print(f"[green]Template '{template_id}' created successfully![/green]")
    except FileExistsError:
        console.print(f"[red]Template '{template_id}' already exists.[/red]")


@templates_app.command("ls")
def templates_ls() -> None:
    """List all prompt templates."""
    store: TemplateStore = get_store()
    templates = store.list_templates()

    table = Table(title="Prompt Templates")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Latest Version", style="magenta")

    for template in templates:
        table.add_row(template.id, str(template.latest_version))

    console.print(table)


@templates_app.command("show")
def templates_show(
    template_id: str = typer.Argument(..., help="The template identifier."),
) -> None:
    """Show a specific prompt template."""
    store: TemplateStore = get_store()
    template = store.get_template(template_id)
    versions = store.list_template_versions(template_id)

    table = Table(title=f"Template: {template_id} ({template.latest_version})")
    table.add_column("Version", style="cyan", no_wrap=True)
    table.add_column("Description", style="magenta")
    for version in versions:
        description = version.metadata.description or ""
        table.add_row(str(version.version), description)

    console.print(table)
