from datetime import datetime
from unittest.mock import MagicMock

import pytest
from pydantic_extra_types.semantic_version import SemanticVersion
from typer.testing import CliRunner

import promptdepot.cli.templates as templates_module
from promptdepot.cli.main import app
from promptdepot.stores.core import (
    Template,
    TemplateVersion,
    TemplateVersionMetadata,
)


def _build_template(template_id: str, latest_version: str = "1.0.0") -> Template:
    return Template(
        id=template_id, latest_version=SemanticVersion.parse(latest_version)
    )


def _build_template_version(
    template_id: str,
    version: str = "1.0.0",
    *,
    description: str | None = "A test prompt",
) -> TemplateVersion:
    sv = SemanticVersion.parse(version)
    return TemplateVersion(
        template_id=template_id,
        version=sv,
        metadata=TemplateVersionMetadata(
            template_id=template_id,
            version=sv,
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            description=description,
            author="tester",
            tags={"test"},
            model="gpt-4",
            changelog=["initial"],
        ),
    )


runner = CliRunner()


# --- templates create ---


def test_templates_create__should_create_template_successfully(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.create_template = MagicMock(return_value=None)
    monkeypatch.setattr(templates_module, "get_store", lambda: mock_store)

    result = runner.invoke(app, ["templates", "create"], input="my-prompt\n")

    assert result.exit_code == 0
    assert "my-prompt" in result.output
    assert "created successfully" in result.output
    mock_store.create_template.assert_called_once_with(template_id="my-prompt")


def test_templates_create__should_print_error_when_template_already_exists(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.create_template = MagicMock(side_effect=FileExistsError("exists"))
    monkeypatch.setattr(templates_module, "get_store", lambda: mock_store)

    result = runner.invoke(app, ["templates", "create"], input="my-prompt\n")

    assert result.exit_code == 0
    assert "already exists" in result.output


# --- templates ls ---


def test_templates_ls__should_list_templates(
    monkeypatch: pytest.MonkeyPatch,
):
    templates = [
        _build_template("prompt-a", "1.0.0"),
        _build_template("prompt-b", "2.1.0"),
    ]
    mock_store = MagicMock()
    mock_store.list_templates = MagicMock(return_value=templates)
    monkeypatch.setattr(templates_module, "get_store", lambda: mock_store)

    result = runner.invoke(app, ["templates", "ls"])

    assert result.exit_code == 0
    assert "prompt-a" in result.output
    assert "prompt-b" in result.output
    assert "1.0.0" in result.output
    assert "2.1.0" in result.output


def test_templates_ls__should_show_empty_table_when_no_templates(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.list_templates = MagicMock(return_value=[])
    monkeypatch.setattr(templates_module, "get_store", lambda: mock_store)

    result = runner.invoke(app, ["templates", "ls"])

    assert result.exit_code == 0
    assert "Prompt Templates" in result.output


# --- templates show ---


def test_templates_show__should_show_template_with_versions(
    monkeypatch: pytest.MonkeyPatch,
):
    template = _build_template("my-prompt", "2.0.0")
    versions = [
        _build_template_version("my-prompt", "1.0.0", description="First version"),
        _build_template_version("my-prompt", "2.0.0", description="Second version"),
    ]
    mock_store = MagicMock()
    mock_store.get_template = MagicMock(return_value=template)
    mock_store.list_template_versions = MagicMock(return_value=versions)
    monkeypatch.setattr(templates_module, "get_store", lambda: mock_store)

    result = runner.invoke(app, ["templates", "show", "my-prompt"])

    assert result.exit_code == 0
    assert "my-prompt" in result.output
    assert "1.0.0" in result.output
    assert "2.0.0" in result.output
    assert "First version" in result.output
    assert "Second version" in result.output


def test_templates_show__should_handle_version_with_no_description(
    monkeypatch: pytest.MonkeyPatch,
):
    template = _build_template("my-prompt", "1.0.0")
    versions = [
        _build_template_version("my-prompt", "1.0.0", description=None),
    ]
    mock_store = MagicMock()
    mock_store.get_template = MagicMock(return_value=template)
    mock_store.list_template_versions = MagicMock(return_value=versions)
    monkeypatch.setattr(templates_module, "get_store", lambda: mock_store)

    result = runner.invoke(app, ["templates", "show", "my-prompt"])

    assert result.exit_code == 0
    assert "1.0.0" in result.output
