# Prompt Depot

Prompt Depot is a Python library for storing, versioning, loading, and rendering prompt templates for LLM workflows.

It provides:

- A versioned local filesystem store (`LocalTemplateStore`) for prompt templates and metadata
- A renderer abstraction (`PromptRenderer`) for pluggable template engines
- Built-in renderer implementations for Mako and Jinja2
- A manager abstraction (`PromptDepotManager`) that coordinates store + renderer with version-aware caching

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
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Coverage](#coverage)
- [CI/CD](#cicd)
- [Development Notes](#development-notes)

## Features

- Semantic-versioned prompt storage
- Metadata validation using Pydantic models
- List templates and list versions per template
- Create new templates and versions (empty or cloned from latest)
- Renderer abstraction to support multiple template engines
- Manager API to fetch + render prompts through one call
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
uv sync --dev
```

If you prefer creating a fresh project with `uv` first:

```bash
uv init
uv add promptdepot
```

## Project Structure

```text
src/promptdepot/
  manager.py
  renderers/
    core.py
    mako.py
    jinja2.py
  stores/
    core.py
    local.py
.github/workflows/
  ci.yml
tests/
  test_manager.py
  test_renderers_core.py
  test_renderers_mako.py
  test_renderers_jinja2.py
  test_stores_local.py
```

## Core Concepts

### 1) `TemplateStore`

Abstract contract for template persistence:

- `get_template(template_id, version)`
- `list_templates()`
- `list_template_versions(template_id)`
- `create_version(template_id, version, template, strategy)`
- `create_template(template_id, template)`

`PromptVersion` accepts semantic versions (`SemanticVersion`) or strings.

### 2) `PromptRenderer`

Abstract base renderer with:

- `template`
- `config`
- `from_template(...)` constructor helper
- Required `render(context: Mapping[str, Any]) -> str`

### 3) `CreationStrategy`

Version creation behavior:

- `CreationStrategy.EMPTY`: create empty template file content
- `CreationStrategy.FROM_PREVIOUS_VERSION`: copy content from latest existing version

### 4) `PromptDepotManager`

`PromptDepotManager` composes a `TemplateStore` and a `PromptRenderer` class into a single API:

- `get_prompt(template_id, version, context) -> str`

Behavior:

- Fetches template data from the store on first use of a `(template_id, version)` pair
- Instantiates renderer with `from_template(...)`
- Caches renderers by `(template_id, version)`
- Accepts `context` as `Mapping[str, Any]`
- Defensively copies `default_config` so renderer-side mutations do not leak

## Prompt Metadata Schema

`LocalTemplateStore` expects a `metadata.yml` that validates to `PromptMetadata`:

- `schema_version`: semantic version (default major version `1`)
- `version`: semantic version of this prompt version
- `created_at`: datetime
- `name`: prompt display name
- `description`: optional
- `author`: optional
- `template_file`: defaults to `template.mako`
- `readme_file`: defaults to `README.md`
- `tags`: set of strings
- `model`: optional model hint
- `changelog`: list of strings

### Expected on-disk layout

```text
<base_path>/
  <template_id>/
    <version>/
      metadata.yml
      template.mako
      README.md
```

Example:

```yaml
schema_version: 1.0.0
version: 1.0.0
created_at: 2024-01-15T10:30:00
name: Example Prompt
description: Example description
author: Your Name
template_file: template.mako
readme_file: README.md
tags: [example, prod]
model: gpt-4
changelog:
  - Initial release
```

## Using `LocalTemplateStore`

```python
from pathlib import Path

from promptdepot.stores.local import LocalTemplateStore

store = LocalTemplateStore(base_path=Path("prompts"))
```

### Get a specific template version

```python
template = store.get_template("support_agent", "1.0.0")

print(template.metadata.name)
print(template.template_path.read_text())
```

### List templates (latest version per template id)

```python
templates = store.list_templates()
for template_id, prompt_template in templates:
    print(template_id, prompt_template.metadata.version)
```

### List all versions for one template

```python
versions = store.list_template_versions("support_agent")
for version, prompt_template in versions:
    print(version, prompt_template.template_path)
```

### Create a new template version

```python
from datetime import datetime
from pathlib import Path

from promptdepot.stores.local import (
    CreationStrategy,
    PromptMetadata,
    PromptTemplate,
)

metadata = PromptMetadata(
    schema_version="1.0.0",
    version="1.1.0",
    created_at=datetime.utcnow(),
    name="Support Agent Prompt",
    description="Prompt used by support triage workflow",
    author="Team AI",
    template_file="template.mako",
    readme_file="README.md",
    tags={"support", "triage"},
    model="gpt-4",
    changelog=["Added escalation instructions"],
)

prompt_template = PromptTemplate(
    metadata=metadata,
    template_path=Path("/tmp/ignored-by-store.mako"),
)

store.create_version(
    template_id="support_agent",
    version="1.1.0",
    template=prompt_template,
    strategy=CreationStrategy.FROM_PREVIOUS_VERSION,
)
```

Note: `create_version(...)` writes metadata and template file into the target directory. For `FROM_PREVIOUS_VERSION`, template file content is copied from the latest version if available.

### Create a brand new template

```python
store.create_template(
    template_id="support_agent",
    template=prompt_template,
)
```

This uses `CreationStrategy.EMPTY` and creates an empty template file.

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

store = LocalTemplateStore(base_path=Path("prompts"))

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

## Error Handling

`LocalTemplateStore` may raise:

- `TemplateNotFoundError`: template id/version/metadata/template file not found
- `VersionAlreadyExistsError`: creating a version that already exists
- `ValidationError` (indirectly during metadata validation paths)

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
uv run pytest tests/test_manager.py
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

- Linting is configured with Ruff in `pyproject.toml`
- The project uses static typing + runtime validation patterns
- Fixtures in `tests/test_prompts/` illustrate accepted and invalid store structures
- Optional renderer packages are intentionally separated from core dependencies
