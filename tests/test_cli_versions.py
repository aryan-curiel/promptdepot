from datetime import datetime
from unittest.mock import MagicMock

import pytest
from pydantic_extra_types.semantic_version import SemanticVersion
from typer.testing import CliRunner

import promptdepot.cli.versions as versions_module
from promptdepot.cli.main import app
from promptdepot.stores.core import (
    CreationStrategy,
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
    author: str | None = "tester",
    tags: set[str] | None = None,
    model: str | None = "gpt-4",
    changelog: list[str] | None = None,
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
            author=author,
            tags=tags or {"test"},
            model=model,
            changelog=changelog or ["initial"],
        ),
    )


runner = CliRunner()


# --- versions create: strategy branches ---


def test_versions_create__should_create_version_with_from_previous_flag(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.create_version = MagicMock(return_value=None)
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(
        app,
        ["versions", "create", "my-prompt", "--version", "2.0.0", "--from-previous"],
    )

    assert result.exit_code == 0
    assert "created successfully" in result.output
    mock_store.create_version.assert_called_once_with(
        template_id="my-prompt",
        version="2.0.0",
        strategy=CreationStrategy.FROM_PREVIOUS_VERSION,
        content=None,
    )


def test_versions_create__should_create_version_with_empty_flag(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.create_version = MagicMock(return_value=None)
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(
        app,
        ["versions", "create", "my-prompt", "--version", "2.0.0", "--empty"],
    )

    assert result.exit_code == 0
    assert "created successfully" in result.output
    mock_store.create_version.assert_called_once_with(
        template_id="my-prompt",
        version="2.0.0",
        strategy=CreationStrategy.EMPTY,
        content=None,
    )


def test_versions_create__should_create_version_with_content_flag_and_content(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.create_version = MagicMock(return_value=None)
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(
        app,
        [
            "versions",
            "create",
            "my-prompt",
            "--version",
            "2.0.0",
            "--with-content",
            "--content",
            "Hello ${name}",
        ],
    )

    assert result.exit_code == 0
    assert "created successfully" in result.output
    mock_store.create_version.assert_called_once_with(
        template_id="my-prompt",
        version="2.0.0",
        strategy=CreationStrategy.WITH_CONTENT,
        content="Hello ${name}",
    )


def test_versions_create__should_default_to_from_previous_when_no_strategy_flag(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.create_version = MagicMock(return_value=None)
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(
        app,
        ["versions", "create", "my-prompt", "--version", "2.0.0"],
    )

    assert result.exit_code == 0
    mock_store.create_version.assert_called_once_with(
        template_id="my-prompt",
        version="2.0.0",
        strategy=CreationStrategy.FROM_PREVIOUS_VERSION,
        content=None,
    )


# --- versions create: version prompt ---


def test_versions_create__should_prompt_for_version_when_not_provided(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.get_template = MagicMock(
        return_value=_build_template("my-prompt", "1.0.0")
    )
    mock_store.create_version = MagicMock(return_value=None)
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(
        app,
        ["versions", "create", "my-prompt"],
        input="2.0.0\n",
    )

    assert result.exit_code == 0
    assert "1.0.0" in result.output  # shows current version in prompt
    assert "created successfully" in result.output
    mock_store.create_version.assert_called_once_with(
        template_id="my-prompt",
        version="2.0.0",
        strategy=CreationStrategy.FROM_PREVIOUS_VERSION,
        content=None,
    )


# --- versions create: content prompt for WITH_CONTENT ---


def test_versions_create__should_prompt_for_content_when_with_content_and_no_content_provided(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.create_version = MagicMock(return_value=None)
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(
        app,
        [
            "versions",
            "create",
            "my-prompt",
            "--version",
            "2.0.0",
            "--with-content",
        ],
        input="My template content\n",
    )

    assert result.exit_code == 0
    assert "created successfully" in result.output
    mock_store.create_version.assert_called_once_with(
        template_id="my-prompt",
        version="2.0.0",
        strategy=CreationStrategy.WITH_CONTENT,
        content="My template content",
    )


# --- versions create: content warning ---


def test_versions_create__should_warn_when_content_provided_with_non_with_content_strategy(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.create_version = MagicMock(return_value=None)
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(
        app,
        [
            "versions",
            "create",
            "my-prompt",
            "--version",
            "2.0.0",
            "--from-previous",
            "--content",
            "ignored content",
        ],
    )

    assert result.exit_code == 0
    assert "Warning" in result.output
    assert "ignored" in result.output


# --- versions create: FileExistsError ---


def test_versions_create__should_print_error_when_version_already_exists(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.create_version = MagicMock(side_effect=FileExistsError("exists"))
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(
        app,
        ["versions", "create", "my-prompt", "--version", "1.0.0"],
    )

    assert result.exit_code == 0
    assert "already exists" in result.output


# --- versions ls ---


def test_versions_ls__should_list_versions_with_metadata(
    monkeypatch: pytest.MonkeyPatch,
):
    versions = [
        _build_template_version(
            "my-prompt",
            "1.0.0",
            description="First",
            author="alice",
            tags={"tag1", "tag2"},
            model="gpt-4",
            changelog=["init", "update"],
        ),
        _build_template_version(
            "my-prompt",
            "2.0.0",
            description="Second",
            author="bob",
            tags=None,
            model=None,
            changelog=None,
        ),
    ]
    mock_store = MagicMock()
    mock_store.list_template_versions = MagicMock(return_value=versions)
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(app, ["versions", "ls", "my-prompt"])

    assert result.exit_code == 0
    assert "1.0.0" in result.output
    assert "2.0.0" in result.output
    assert "First" in result.output
    assert "Second" in result.output


def test_versions_ls__should_show_empty_table_when_no_versions(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    mock_store.list_template_versions = MagicMock(return_value=[])
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(app, ["versions", "ls", "my-prompt"])

    assert result.exit_code == 0
    assert "my-prompt" in result.output


# --- versions show ---


def test_versions_show__should_display_version_details(
    monkeypatch: pytest.MonkeyPatch,
):
    version = _build_template_version(
        "my-prompt",
        "1.0.0",
        description="A great prompt",
        author="alice",
        tags={"tag1"},
        model="gpt-4",
        changelog=["initial release"],
    )
    mock_store = MagicMock()
    mock_store.get_template_version = MagicMock(return_value=version)
    mock_store.get_template_version_content = MagicMock(return_value="Hello ${name}!")
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(app, ["versions", "show", "my-prompt", "1.0.0"])

    assert result.exit_code == 0
    assert "my-prompt" in result.output
    assert "1.0.0" in result.output
    assert "A great prompt" in result.output
    assert "alice" in result.output
    assert "gpt-4" in result.output
    assert "initial release" in result.output
    assert "Hello ${name}!" in result.output


# --- versions create: mutually exclusive flags ---


def test_versions_create__should_raise_when_multiple_strategy_flags_provided(
    monkeypatch: pytest.MonkeyPatch,
):
    mock_store = MagicMock()
    monkeypatch.setattr(versions_module, "get_store", lambda: mock_store)

    result = runner.invoke(
        app,
        [
            "versions",
            "create",
            "my-prompt",
            "--version",
            "2.0.0",
            "--from-previous",
            "--empty",
        ],
    )

    assert result.exit_code != 0
    assert "mutually exclusive" in result.output
