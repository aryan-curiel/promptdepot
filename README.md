# Prompt Depot

Prompt Depot is a Python library for storing, versioning, loading, and rendering prompt templates for LLM workflows.

It provides:

- A versioned local filesystem store (`LocalTemplateStore`) for prompt templates and metadata
- A renderer abstraction (`PromptRenderer`) for pluggable template engines
- Built-in renderer implementations for Mako and Jinja2
- A manager abstraction (`PromptDepotManager`) that coordinates store + renderer with version-aware caching
- A CLI (`promptdepot`) for managing templates and versions from the terminal

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Core Concepts](#core-concepts)
- [Prompt Metadata Schema](#prompt-metadata-schema)
- [Using LocalTemplateStore](#using-localtemplatestore)
- [Using Renderers](#using-renderers)
- [Using PromptDepotManager](#using-promptdepotmanager)
- [CLI](#cli)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Coverage](#coverage)
- [CI/CD](#cicd)
- [Development Notes](#development-notes)

## Features

- Semantic-versioned prompt storage
- Metadata validation using Pydantic models
- List templates and list versions per template
- Create new templates and versions (empty, cloned from latest, or with provided content)
- Renderer abstraction to support multiple template engines
- Manager API to fetch + render prompts through one call
- CLI for creating, listing, and inspecting templates and versions
- Settings loaded from `[tool.promptdepot]` in `pyproject.toml`
- Optional dependencies for renderer engines (`mako`, `jinja2`)

## Requirements

- Python `>= 3.10`

## Installation

### Base package

```bash
pip install promptdepot
```

Or with `uv`:

```bash
uv add promptdepot
```

### With Mako renderer support

```bash
pip install "promptdepot[mako]"
```

Or with `uv`:

```bash
uv add "promptdepot[mako]"
```

### With Jinja2 renderer support

```bash
pip install "promptdepot[jinja2]"
```

Or with `uv`:

```bash
uv add "promptdepot[jinja2]"
```

### Development dependencies

```bash
uv sync --frozen --all-extras --group dev
```

## Project Structure

```text
src/promptdepot/
  __init__.py
  py.typed
  manager.py
  cli/
    __init__.py         # Entry point (main function)
    main.py             # Typer app with sub-command groups
    settings.py         # Settings loaded from pyproject.toml
    templates.py        # templates create/ls/show commands
    versions.py         # versions create/ls/show commands
    utils.py            # get_store() helper
  renderers/
    __init__.py
    core.py
    mako.py
    jinja2.py
  stores/
    __init__.py
    core.py             # ABC, domain models, CreationStrategy
    local.py            # LocalTemplateStore implementation
tests/
  test_manager.py
  test_renderers_core.py
  test_renderers_mako.py
  test_renderers_jinja2.py
  test_stores_local.py
  test_cli_settings.py
  test_cli_utils.py
  test_cli_templates.py
  test_cli_versions.py
  test_prompts/           # Fixture data (prompt template directories)
.github/workflows/
  ci.yml
```

## Core Concepts

### Domain Models

All domain models live in `promptdepot.stores.core` and use Pydantic:

- **`Template`** -- represents a template with its `id` and `latest_version`.
- **`TemplateVersionMetadata`** -- metadata for a single version: `template_id`, `version`, `created_at`, `description`, `author`, `tags`, `model`, `changelog`.
- **`TemplateVersion`** -- a version record containing `template_id`, `version`, and its `metadata`.

### `TemplateStore`

Abstract contract for template persistence. Accepts an optional `config` mapping in its constructor:

- `list_templates() -> list[Template]`
- `get_template(template_id) -> Template`
- `create_template(template_id)`
- `list_template_versions(template_id) -> list[TemplateVersion]`
- `get_template_version(template_id, version) -> TemplateVersion`
- `create_version(template_id, version, metadata?, *, strategy, content?)`
- `get_template_version_content(template_id, version) -> str`

`PromptVersion` accepts semantic versions (`SemanticVersion`) or plain strings.

### `PromptRenderer`

Abstract base renderer with:

- `template`
- `config`
- `from_template(...)` constructor helper
- Required `render(context: Mapping[str, Any]) -> str`

### `CreationStrategy`

Version creation behavior:

- `CreationStrategy.EMPTY` -- create with empty template file content
- `CreationStrategy.FROM_PREVIOUS_VERSION` -- copy content from the latest existing version
- `CreationStrategy.WITH_CONTENT` -- create with explicitly provided content

### `PromptDepotManager`

Composes a `TemplateStore` and a `PromptRenderer` class into a single API:

- `get_prompt(template_id, version, context) -> str`

Behavior:

- Fetches template content from the store on first use of a `(template_id, version)` pair
- Instantiates the renderer with `from_template(...)`
- Caches renderers by `(template_id, version)`
- Accepts `context` as `Mapping[str, Any]`
- Performs a shallow copy of `default_config` so renderer-side mutations to top-level keys do not leak

## Prompt Metadata Schema

`LocalTemplateStore` expects a `metadata.yml` per version that validates to `TemplateVersionMetadata`:

- `template_id`: string matching the parent directory name
- `version`: semantic version of this prompt version
- `created_at`: datetime (defaults to `datetime.now()` when creating)
- `description`: optional
- `author`: optional
- `tags`: set of strings (default empty)
- `model`: optional model hint
- `changelog`: list of strings (default empty)

### Expected on-disk layout

```text
<base_path>/
  <template_id>/
    <version>/
      metadata.yml
      template.md
```

Example `metadata.yml`:

```yaml
template_id: support_agent
version: 1.0.0
created_at: 2025-01-15T10:30:00
description: Support triage prompt
author: Your Name
tags: [support, prod]
model: gpt-4
changelog:
  - Initial release
```

## Using `LocalTemplateStore`

`LocalTemplateStore` accepts a `StoreConfig` TypedDict:

```python
from pathlib import Path

from promptdepot.stores.local import LocalTemplateStore, StoreConfig

config: StoreConfig = {
    "base_path": Path("prompts"),
    "initial_version": None,       # defaults to 1.0.0
    "template_file_name": None,    # defaults to "template.md"
    "metadata_file_name": None,    # defaults to "metadata.yml"
}

store = LocalTemplateStore(config=config)
```

### Get a template (latest version info)

```python
template = store.get_template("support_agent")

print(template.id)               # "support_agent"
print(template.latest_version)   # SemanticVersion
```

### Get a specific template version

```python
version = store.get_template_version("support_agent", "1.0.0")

print(version.template_id)
print(version.version)
print(version.metadata.description)
print(version.metadata.author)
```

### Get template content

```python
content = store.get_template_version_content("support_agent", "1.0.0")
print(content)
```

### List templates

```python
templates = store.list_templates()
for template in templates:
    print(template.id, template.latest_version)
```

### List all versions for a template

```python
versions = store.list_template_versions("support_agent")
for version in versions:
    print(version.version, version.metadata.description)
```

### Create a new template

Creates the template directory with an initial empty version (defaults to `1.0.0`):

```python
store.create_template(template_id="support_agent")
```

### Create a new version

```python
from promptdepot.stores.core import CreationStrategy

# Copy content from the latest version
store.create_version(
    template_id="support_agent",
    version="1.1.0",
    strategy=CreationStrategy.FROM_PREVIOUS_VERSION,
)

# Create with empty content
store.create_version(
    template_id="support_agent",
    version="2.0.0",
    strategy=CreationStrategy.EMPTY,
)

# Create with explicit content
store.create_version(
    template_id="support_agent",
    version="2.1.0",
    strategy=CreationStrategy.WITH_CONTENT,
    content="Hello ${name}, how can I help you today?",
)
```

## Using Renderers

### Mako renderer

```python
from promptdepot.renderers.mako import MakoPromptRenderer

renderer = MakoPromptRenderer(
    template="Hello ${name}!",
    config={"lookup": None},
)

result = renderer.render(context={"name": "World"})
print(result)  # Hello World!
```

### Jinja2 renderer

```python
from promptdepot.renderers.jinja2 import Jinja2PromptRenderer

renderer = Jinja2PromptRenderer(
    template="Hello {{ name }}!",
    config={"environment": None},
)

result = renderer.render(context={"name": "World"})
print(result)  # Hello World!
```

### Generic renderer construction pattern

```python
renderer = SomeRenderer.from_template(template="...", config={...})
output = renderer.render(context={"key": "value"})
```

## Using `PromptDepotManager`

```python
from pathlib import Path

from promptdepot.manager import PromptDepotManager
from promptdepot.renderers.jinja2 import Jinja2PromptRenderer
from promptdepot.stores.local import LocalTemplateStore

store = LocalTemplateStore(config={
    "base_path": Path("prompts"),
    "initial_version": None,
    "template_file_name": None,
    "metadata_file_name": None,
})

manager = PromptDepotManager(
    store=store,
    renderer=Jinja2PromptRenderer,
    default_config={"environment": None},
)

output = manager.get_prompt(
    template_id="support_agent",
    version="1.0.0",
    context={"user_name": "Aryan", "priority": "high"},
)

print(output)
```

## CLI

Prompt Depot includes a CLI built with [Typer](https://typer.tiangolo.com/). After installation, the `promptdepot` command is available:

```bash
promptdepot --help
```

The CLI reads its configuration from `[tool.promptdepot]` in your project's `pyproject.toml` (see [Configuration](#configuration)).

### Templates

#### Create a template

Prompts for a template ID interactively:

```bash
promptdepot templates create
```

#### List all templates

```bash
promptdepot templates ls
```

Displays a table with each template's ID and latest version.

#### Show a template

```bash
promptdepot templates show <template_id>
```

Displays all versions of the given template with their descriptions.

### Versions

#### Create a version

```bash
# Copy content from the latest version (default)
promptdepot versions create <template_id> --version 2.0.0

# Copy from previous explicitly
promptdepot versions create <template_id> --version 2.0.0 --from-previous

# Create with empty content
promptdepot versions create <template_id> --version 2.0.0 --empty

# Create with explicit content
promptdepot versions create <template_id> --version 2.0.0 --with-content --content "Hello \${name}!"
```

If `--version` is omitted, the CLI shows the current latest version and prompts for input. If `--with-content` is used without `--content`, the CLI prompts for the content interactively.

#### List versions

```bash
promptdepot versions ls <template_id>
```

Displays a table with version, description, created_at, author, tags, model, and changelog.

#### Show a version

```bash
promptdepot versions show <template_id> <version>
```

Displays full metadata and content for a specific version.

## Configuration

The CLI reads settings from the `[tool.promptdepot]` section in `pyproject.toml`:

```toml
[tool.promptdepot]
store_path = "promptdepot.stores.local.LocalTemplateStore"

[tool.promptdepot.store.config]
base_path = "prompts"
```

| Key | Description | Default |
|---|---|---|
| `store_path` | Dotted import path to the `TemplateStore` class | `promptdepot.stores.local.LocalTemplateStore` |
| `store.config` | Dictionary passed as `config` to the store constructor | `{}` |

For `LocalTemplateStore`, the recognized config keys are:

| Key | Description | Default |
|---|---|---|
| `base_path` | Path to the root directory containing templates | (required) |
| `initial_version` | Version string for `create_template` | `1.0.0` |
| `template_file_name` | Name of the template file in each version directory | `template.md` |
| `metadata_file_name` | Name of the metadata file in each version directory | `metadata.yml` |

## Error Handling

`LocalTemplateStore` may raise:

- `TemplateNotFoundError` -- template id, version, metadata file, or template file not found
- `VersionAlreadyExistsError` -- creating a version that already exists
- `ValidationError` -- Pydantic validation failure on metadata

Mako/Jinja2 constructors can raise syntax errors on invalid templates:

- Mako: `mako.exceptions.SyntaxException`
- Jinja2: `jinja2.TemplateSyntaxError`

## Testing

Run all tests:

```bash
uv run pytest tests
```

Run specific files:

```bash
uv run pytest tests/test_stores_local.py
uv run pytest tests/test_cli_templates.py
```

Run a single test:

```bash
uv run pytest tests/test_stores_local.py::test_local_template_store_init__should_set_class_properly_when_path_is_string -v -s
```

## Coverage

Run tests with coverage:

```bash
uv run pytest tests --cov=promptdepot --cov-report=term-missing --cov-report=html
```

Open HTML report (macOS):

```bash
open htmlcov/index.html
```

## CI/CD

The repository includes a GitHub Actions workflow at `.github/workflows/ci.yml`.

On `push` (all branches) and `pull_request` (targeting `main`), it runs:

- Ruff lint: `ruff check .`
- Ruff format check: `ruff format --check .`
- Type checks: `ty check src`
- Test matrix on Python `3.10`, `3.11`, `3.12`, and `3.13`

On `release: published` (targeting `main`), after CI passes, it:

- Builds distributions with `uv build`
- Publishes to PyPI via Trusted Publishing (OIDC)

For PyPI publication, configure Trusted Publishing in your PyPI project settings for this repository/workflow.

## Development Notes

- Linting and formatting are configured with Ruff in `pyproject.toml`
- The project uses static typing with a `py.typed` marker (PEP 561)
- Fixtures in `tests/test_prompts/` illustrate accepted and invalid store structures
- Optional renderer packages (`mako`, `jinja2`) are separated from core dependencies
- CLI dependencies (`typer`, `rich`, `pydantic-settings`) are part of the core package
