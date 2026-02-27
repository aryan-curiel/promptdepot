from pathlib import Path

import pytest

import promptdepot.cli.utils as utils_module
from promptdepot.cli.settings import Settings, StoreSettings
from promptdepot.cli.utils import get_store
from promptdepot.stores.local import LocalTemplateStore


def test_get_store__should_return_local_template_store_with_default_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    fake_settings = Settings(
        store_path="promptdepot.stores.local.LocalTemplateStore",
        store=StoreSettings(config={"base_path": str(tmp_path)}),
        _env_file=None,  # type: ignore[call-arg]
    )
    monkeypatch.setattr(utils_module, "settings", fake_settings)

    store = get_store()

    assert isinstance(store, LocalTemplateStore)
    assert store.base_path == tmp_path


def test_get_store__should_pass_config_to_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    fake_settings = Settings(
        store_path="promptdepot.stores.local.LocalTemplateStore",
        store=StoreSettings(
            config={
                "base_path": str(tmp_path),
                "template_file_name": "prompt.txt",
                "metadata_file_name": "meta.yaml",
            }
        ),
        _env_file=None,  # type: ignore[call-arg]
    )
    monkeypatch.setattr(utils_module, "settings", fake_settings)

    store = get_store()

    assert isinstance(store, LocalTemplateStore)
    assert store.template_file_name == "prompt.txt"
    assert store.metadata_file_name == "meta.yaml"


def test_get_store__should_raise_when_store_path_module_not_found(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_settings = Settings(
        store_path="nonexistent.module.FakeStore",
        _env_file=None,  # type: ignore[call-arg]
    )
    monkeypatch.setattr(utils_module, "settings", fake_settings)

    with pytest.raises(ModuleNotFoundError):
        get_store()


def test_get_store__should_raise_when_store_class_not_found(
    monkeypatch: pytest.MonkeyPatch,
):
    fake_settings = Settings(
        store_path="promptdepot.stores.local.NonExistentStore",
        _env_file=None,  # type: ignore[call-arg]
    )
    monkeypatch.setattr(utils_module, "settings", fake_settings)

    with pytest.raises(AttributeError):
        get_store()
