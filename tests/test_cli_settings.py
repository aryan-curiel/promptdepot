from pathlib import Path
from typing import Any

from promptdepot.cli.settings import (
    PyprojectTomlSource,
    Settings,
    StoreSettings,
)


def test_store_settings_init__should_have_empty_config_by_default():
    store = StoreSettings()  # ty:ignore[missing-argument]
    assert store.config == {}


def test_store_settings_init__should_accept_config():
    store = StoreSettings(config={"base_path": "/tmp"})
    assert store.config == {"base_path": "/tmp"}


def test_settings_init__should_have_defaults():
    s = Settings(
        _env_file=None,  # type: ignore[call-arg]
    )
    assert s.store_path == "promptdepot.stores.local.LocalTemplateStore"
    assert isinstance(s.store, StoreSettings)


def test_settings_init__should_accept_store_path():
    s = Settings(
        store_path="custom.module.CustomStore",
        _env_file=None,  # type: ignore[call-arg]
    )
    assert s.store_path == "custom.module.CustomStore"


def test_pyproject_toml_source_read_file__should_extract_tool_promptdepot_section(
    tmp_path: Path,
):
    toml_content = """\
[tool.promptdepot]
store_path = "my.custom.Store"

[tool.promptdepot.store.config]
base_path = "/my/prompts"
"""
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text(toml_content)

    source = PyprojectTomlSource(Settings, toml_file=toml_file)
    data: dict[str, Any] = source._read_file(toml_file)

    assert data["store_path"] == "my.custom.Store"
    assert data["store"]["config"]["base_path"] == "/my/prompts"


def test_pyproject_toml_source_read_file__should_return_empty_dict_when_no_promptdepot_section(
    tmp_path: Path,
):
    toml_content = """\
[tool.other]
key = "value"
"""
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text(toml_content)

    source = PyprojectTomlSource(Settings, toml_file=toml_file)
    data: dict[str, Any] = source._read_file(toml_file)

    assert data == {}


def test_pyproject_toml_source_read_file__should_return_empty_dict_when_no_tool_section(
    tmp_path: Path,
):
    toml_content = """\
[project]
name = "test"
"""
    toml_file = tmp_path / "pyproject.toml"
    toml_file.write_text(toml_content)

    source = PyprojectTomlSource(Settings, toml_file=toml_file)
    data: dict[str, Any] = source._read_file(toml_file)

    assert data == {}


def test_settings_settings_customise_sources__should_include_pyproject_toml_source():
    sources = Settings.settings_customise_sources(
        Settings,
        init_settings=None,  # type: ignore[arg-type]
        env_settings=None,  # type: ignore[arg-type]
        dotenv_settings=None,  # type: ignore[arg-type]
        file_secret_settings=None,  # type: ignore[arg-type]
    )
    assert len(sources) == 3
    assert sources[0] is None  # init_settings
    assert sources[1] is None  # env_settings
    assert isinstance(sources[2], PyprojectTomlSource)
