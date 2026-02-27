# AGENTS.md

Guidelines for AI coding agents working in the `promptdepot` repository.

## Project Overview

Python library (>=3.10) for storing, versioning, loading, and rendering LLM prompt templates. Uses Pydantic for data validation, YAML for metadata, and pluggable template engines (Mako, Jinja2). Package manager is `uv`.

## Build, Lint, Test Commands

```bash
# Install all dependencies (dev + all extras)
uv sync --frozen --all-extras --group dev

# Lint
uvx ruff check .

# Format check
uvx ruff format --check .

# Auto-format
uvx ruff format .

# Type check
uvx ty check src

# Run all tests
uv run pytest tests

# Run a single test file
uv run pytest tests/test_stores_local.py

# Run a single test function
uv run pytest tests/test_stores_local.py::test_local_template_store_init__should_set_class_properly_when_path_is_string

# Run a single test with verbose output
uv run pytest tests/test_stores_local.py::test_local_template_store_init__should_set_class_properly_when_path_is_string -v -s

# Run tests with coverage
uv run pytest tests --cov=promptdepot --cov-report=term-missing --cov-report=html

# Build distributions
uv build
```

Always run `uvx ruff check .` and `uvx ruff format --check .` before committing. CI runs these plus `uvx ty check src` and `uv run pytest tests` across Python 3.10-3.13.

## Project Structure

```
src/promptdepot/
  __init__.py           # Empty (no top-level re-exports)
  py.typed              # PEP 561 typed package marker
  manager.py            # PromptDepotManager (coordinates store + renderer)
  stores/
    __init__.py         # Re-exports: TemplateStore, CreationStrategy, PromptVersion
    core.py             # Abstract TemplateStore, CreationStrategy enum, PromptVersion alias
    local.py            # LocalTemplateStore, PromptMetadata, PromptTemplate, exceptions
  renderers/
    __init__.py         # Re-exports: PromptRenderer
    core.py             # Abstract PromptRenderer base class
    mako.py             # MakoPromptRenderer
    jinja2.py           # Jinja2PromptRenderer
tests/
  test_manager.py
  test_stores_local.py
  test_renderers_core.py
  test_renderers_mako.py
  test_renderers_jinja2.py
  test_prompts/         # Fixture data (prompt template directories)
```

## Code Style

### Formatting and Linting

- **Ruff** is the sole linter and formatter. All config is in `pyproject.toml`.
- Enabled rule sets: `E4`, `E7`, `E9`, `F`, `B` (bugbear), `S` (bandit/security), `PERF`, `T20` (no print), `LOG`, `ASYNC`, `C90` (max complexity 15), `UP` (pyupgrade).
- `B` fixes are unfixable (must be fixed manually).
- Print statements are **banned** in production code (`T20`). Allowed in tests.
- `assert` is allowed in test files (`S101` ignored for `test_*.py`).
- Max cyclomatic complexity: 15.

### Imports

- **Standard library first, then third-party, then local** (PEP 8 order, enforced by Ruff).
- Prefer `from X import Y` over bare `import X`.
- Use **relative imports only in `__init__.py`** files for re-exports:
  ```python
  # stores/__init__.py
  from .core import CreationStrategy, PromptVersion, TemplateStore
  ```
- All other local imports use **absolute package paths**:
  ```python
  from promptdepot.stores.core import CreationStrategy, PromptVersion, TemplateStore
  from promptdepot.renderers.core import PromptRenderer
  ```
- Re-export public symbols via `__all__` in `__init__.py` files.
- Use `collections.abc` for abstract types (`Mapping`, `Hashable`), not `typing`.

### Type Annotations

- This is a **fully typed** package (`py.typed` marker present). All public methods must have return type annotations.
- Use **PEP 604 union syntax**: `str | None`, not `Optional[str]` or `Union[str, None]`.
- Use `Annotated[T, Field(...)]` for Pydantic fields with default factories.
- Use `TypedDict` for config dictionaries, `BaseModel` for data models.
- Use `typing_extensions.Self` for classmethod return types.
- Abstract method bodies use the ellipsis: `def method(self) -> T: ...`
- Enforce **keyword-only arguments** with `*` in constructors:
  ```python
  def __init__(self, *, base_path: Path | str): ...
  def __init__(self, template: TemplateT, *, config: ConfigDictT): ...
  ```
- Use `cast()` explicitly when narrowing types.

### Naming Conventions

| Element            | Convention   | Example                                    |
| ------------------ | ------------ | ------------------------------------------ |
| Files              | `snake_case` | `local.py`, `core.py`                      |
| Classes            | `PascalCase` | `LocalTemplateStore`, `PromptMetadata`     |
| Functions/methods  | `snake_case` | `get_template`, `list_templates`            |
| Private methods    | `_prefix`    | `_read_prompt_metadata`                    |
| Variables          | `snake_case` | `template_id`, `version_path`              |
| TypeVars           | Short upper  | `TID`, `TTemplate`, `ConfigDictT`          |
| Type aliases       | `PascalCase` | `PromptVersion`                            |
| Exceptions         | `PascalCase` | `TemplateNotFoundError`                    |
| Test files         | `test_*.py`  | `test_stores_local.py`                     |
| Test fixtures      | `snake_case` | `local_store`, `temp_local_store`           |
| Test helpers       | `_prefix`    | `_build_template`, `_build_validation_error`|

### Test Naming Convention

Test functions follow a strict pattern with double underscore separating subject from behavior:

```
test_<class_or_module>_<method>__should_<expected_behavior>
```

Examples:
```python
def test_local_template_store_init__should_set_class_properly_when_path_is_string():
def test_mako_prompt_renderer_render__should_render_simple_template():
def test_prompt_depot_manager_get_prompt__should_cache_renderer_by_template_and_version():
```

Fixtures annotate their return type. Test functions do not annotate return types.

### Error Handling

- Define **custom exceptions inheriting from built-in exceptions**:
  ```python
  class TemplateNotFoundError(FileNotFoundError): ...
  class VersionAlreadyExistsError(FileExistsError): ...
  ```
- Use **f-string messages with context** (template_id, version, path).
- In batch operations, use **catch-log-continue**: `TemplateNotFoundError` logs a `warning`; `ValidationError`, `ValueError`, `OSError` log an `error`.
- Let Pydantic `ValidationError` and template engine errors (Mako `SyntaxException`, Jinja2 `TemplateSyntaxError`) propagate to the caller.
- In tests, use `pytest.raises` with optional `match` parameter.

### Pydantic Models

- Use `BaseModel` with modern annotations. Use `model_validate()` for parsing, `model_dump(mode="json")` for serialization.
- Default values directly on fields. Use `Annotated[T, Field(default_factory=...)]` for mutable defaults.
- Metadata is stored as YAML (`pyyaml` `safe_load`/`safe_dump`).

## Dependencies

- Core: `pydantic`, `pydantic-extra-types`, `pyyaml`, `semver`, `typing-extensions`
- Optional extras: `mako`, `jinja2`, `cli` (typer, rich, pydantic-settings)
- Dev: `pytest`, `pytest-cov`, `coverage`
