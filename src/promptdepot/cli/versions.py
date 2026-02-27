import typer
from rich.console import Console
from rich.table import Table

from promptdepot.stores.core import CreationStrategy, TemplateStore

from .utils import get_store

versions_app = typer.Typer(help="Manage versions of a prompt template.")
console = Console()


@versions_app.command("create")
def versions_create(
    template_id: str = typer.Argument(..., help="The template identifier."),
    version: str | None = typer.Option(
        None,
        "--version",
        "-v",
        help="The version identifier. If not provided, you will be prompted to enter a version.",
    ),
    from_previous: bool = typer.Option(
        False,
        "--from-previous",
        "-p",
        help="Whether to create the new version from the previous version's content. If not set, the new version will be empty.",
    ),
    empty: bool = typer.Option(
        False,
        "--empty",
        help="Whether to create the new version with empty content. If not set, the new version will be created from the previous version's content.",
    ),
    with_content: bool = typer.Option(
        False,
        "--with-content",
        help="Whether to create the new version with content. If not set, the new version will be created from the previous version's content.",
    ),
    content: str | None = typer.Option(
        None,
        "--content",
        "-c",
        help="The content for the new version. If not provided, the new version will be created from the previous version's content.",
    ),
) -> None:
    """Create a new version of a prompt template."""
    store: TemplateStore = get_store()
    if not version:
        latest_version = store.get_template(template_id).latest_version
        version = typer.prompt(
            f"Version not provided. Please enter a version identifier. Current version is {latest_version}."
        )

    # Ensure mutually exclusive creation strategy flags
    selected_flags = [from_previous, empty, with_content]
    if sum(1 for flag in selected_flags if flag) > 1:
        raise typer.BadParameter(
            "Options --from-previous, --empty, and --with-content are mutually exclusive. "
            "Please specify at most one."
        )

    if from_previous:
        strategy = CreationStrategy.FROM_PREVIOUS_VERSION
    elif empty:
        strategy = CreationStrategy.EMPTY
    elif with_content:
        strategy = CreationStrategy.WITH_CONTENT
    else:
        strategy = CreationStrategy.FROM_PREVIOUS_VERSION
    if strategy != CreationStrategy.WITH_CONTENT and content:
        console.print(
            "[yellow]Warning: Content provided will be ignored because of the creation strategy.[/yellow]"
        )

    if strategy == CreationStrategy.WITH_CONTENT and not content:
        content = typer.prompt("Enter the content for the new version")

    try:
        store.create_version(
            template_id=template_id,
            version=version,
            strategy=strategy,
            content=content,
        )
        console.print(
            f"[green]Version '{version}' for template '{template_id}' created successfully![/green]"
        )
    except FileExistsError:
        console.print(
            f"[red]Version '{version}' for template '{template_id}' already exists.[/red]"
        )


@versions_app.command("ls")
def versions_ls(
    template_id: str = typer.Argument(..., help="The template identifier."),
) -> None:
    """List all versions of a prompt template."""
    store: TemplateStore = get_store()
    versions = store.list_template_versions(template_id)

    table = Table(title=f"Versions for Template: {template_id}")
    table.add_column("Version", style="cyan", no_wrap=True)
    table.add_column("Description", style="magenta")
    table.add_column("Created At", style="green")
    table.add_column("Author", style="yellow")
    table.add_column("Tags", style="blue")
    table.add_column("Model", style="red")
    table.add_column("Changelog", style="white")
    for version in versions:
        description = version.metadata.description
        created_at = version.metadata.created_at
        author = version.metadata.author
        tags = ", ".join(version.metadata.tags or [])
        model = version.metadata.model
        changelog = "\n".join(version.metadata.changelog or [])
        table.add_row(
            str(version.version),
            description,
            str(created_at),
            author,
            tags,
            model,
            changelog,
        )

    console.print(table)


@versions_app.command("show")
def versions_show(
    template_id: str = typer.Argument(..., help="The template identifier."),
    version: str = typer.Argument(..., help="The version identifier."),
) -> None:
    """Show a specific version of a prompt template."""
    store: TemplateStore = get_store()
    version_data = store.get_template_version(template_id, version)
    metadata = version_data.metadata
    console.print(f"[bold cyan]Template ID:[/bold cyan] {template_id}")
    console.print(f"[bold cyan]Version:[/bold cyan] {version}")
    console.print(f"[bold cyan]Description:[/bold cyan] {metadata.description}")
    console.print(f"[bold cyan]Created At:[/bold cyan] {metadata.created_at}")
    console.print(f"[bold cyan]Author:[/bold cyan] {metadata.author}")
    console.print(f"[bold cyan]Tags:[/bold cyan] {', '.join(metadata.tags or [])}")
    console.print(f"[bold cyan]Model:[/bold cyan] {metadata.model}")
    console.print("[bold cyan]Changelog:[/bold cyan]")
    for change in metadata.changelog:
        console.print(f"- {change}")
    console.print("[bold cyan]Content:[/bold cyan]")
    console.print(store.get_template_version_content(template_id, version))
