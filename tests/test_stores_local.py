from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

import promptdepot.stores.local as local_store_module
from promptdepot.stores.core import (
    CreationStrategy,
    Template,
    TemplateVersion,
    TemplateVersionMetadata,
)
from promptdepot.stores.local import (
    LocalTemplateStore,
    StoreConfig,
    TemplateNotFoundError,
    VersionAlreadyExistsError,
)


def _make_config(base_path: Path | str) -> StoreConfig:
    return StoreConfig(
        base_path=base_path,
        initial_version=None,
        template_file_name=None,
        metadata_file_name=None,
    )


@pytest.fixture
def local_store() -> LocalTemplateStore:
    return LocalTemplateStore(config=_make_config(Path("tests/test_prompts")))


@pytest.fixture
def temp_local_store(tmp_path: Path) -> LocalTemplateStore:
    return LocalTemplateStore(config=_make_config(tmp_path / "prompts"))


def test_local_template_store_init__should_set_class_properly_when_path_is_string():
    path_str = "/tmp/prompts"
    store = LocalTemplateStore(config=_make_config(path_str))
    assert store.base_path == Path(path_str)


def test_local_template_store_init__should_set_class_properly_when_path_is_path():
    path_obj = Path("/tmp/prompts")
    store = LocalTemplateStore(config=_make_config(path_obj))
    assert store.base_path == path_obj


def test_local_template_store_read_prompt_metadata__should_raise_when_file_does_not_exist(
    local_store: LocalTemplateStore,
):
    non_existent_file = local_store.base_path / "non_existent_metadata.yml"
    with pytest.raises(TemplateNotFoundError):
        local_store._read_prompt_metadata(non_existent_file)


def assert_metadata_equal(
    metadata: TemplateVersionMetadata,
    expected: dict,
):
    assert metadata.template_id == expected["template_id"]
    assert str(metadata.version) == expected["version"]
    assert metadata.created_at == expected["created_at"]
    assert metadata.description == expected["description"]
    assert metadata.author == expected["author"]
    assert metadata.tags == expected["tags"]
    assert metadata.model == expected["model"]
    assert metadata.changelog == expected["changelog"]


def test_local_template_store_read_prompt_metadata__should_read_and_parse_metadata_correctly(
    local_store: LocalTemplateStore,
):
    metadata: TemplateVersionMetadata = local_store._read_prompt_metadata(
        local_store.base_path / "testing_prompt" / "1.0.0" / "metadata.yml"
    )
    expected_metadata = {
        "template_id": "testing_prompt",
        "version": "1.0.0",
        "created_at": datetime.fromisoformat("2024-01-15T10:30:00"),
        "description": "A test prompt for validation purposes",
        "author": "Aryan Curiel",
        "tags": {"test", "example", "validation"},
        "model": "gpt-4",
        "changelog": ["Initial release", "Added validation tests"],
    }
    assert_metadata_equal(metadata, expected_metadata)


def test_local_template_store_get_template__should_raise_when_template_does_not_exist(
    local_store: LocalTemplateStore,
):
    with pytest.raises(TemplateNotFoundError):
        local_store.get_template("non_existent_template")


def test_local_template_store_get_template__should_return_template_when_it_exists(
    local_store: LocalTemplateStore,
):
    template = local_store.get_template("testing_prompt")
    assert template is not None
    assert isinstance(template, Template)
    assert template.id == "testing_prompt"


def test_local_template_store_get_template__should_return_latest_version(
    local_store: LocalTemplateStore,
):
    template = local_store.get_template("testing_prompt")
    assert str(template.latest_version) == "1.1.0"


def test_local_template_store_get_template_version__should_raise_when_template_does_not_exist(
    local_store: LocalTemplateStore,
):
    with pytest.raises(TemplateNotFoundError):
        local_store.get_template_version("non_existent_template", "1.0.0")


def test_local_template_store_get_template_version__should_raise_when_template_incomplete(
    local_store: LocalTemplateStore,
):
    with pytest.raises(TemplateNotFoundError):
        local_store.get_template_version("testing_prompt_incomplete", "1.0.0")


def test_local_template_store_get_template_version__should_raise_when_version_does_not_exist(
    local_store: LocalTemplateStore,
):
    with pytest.raises(TemplateNotFoundError):
        local_store.get_template_version("testing_prompt", "999.0.0")


def test_local_template_store_get_template_version__should_return_correct_template_version(
    local_store: LocalTemplateStore,
):
    expected_metadata = {
        "template_id": "testing_prompt",
        "version": "1.0.0",
        "created_at": datetime.fromisoformat("2024-01-15T10:30:00"),
        "description": "A test prompt for validation purposes",
        "author": "Aryan Curiel",
        "tags": {"test", "example", "validation"},
        "model": "gpt-4",
        "changelog": ["Initial release", "Added validation tests"],
    }
    template_version = local_store.get_template_version(
        "testing_prompt", expected_metadata["version"]
    )
    assert isinstance(template_version, TemplateVersion)
    assert template_version.template_id == "testing_prompt"
    assert str(template_version.version) == "1.0.0"
    assert_metadata_equal(template_version.metadata, expected_metadata)


def test_local_template_store_list_templates__should_return_empty_list_when_base_path_has_no_dirs(
    temp_local_store: LocalTemplateStore,
):
    temp_local_store.base_path.mkdir(parents=True, exist_ok=True)

    templates = temp_local_store.list_templates()

    assert templates == []


def _build_template_version(
    template_id: str = "testing_prompt",
    version: str = "1.0.0",
) -> TemplateVersion:
    metadata = TemplateVersionMetadata(
        template_id=template_id,
        version=version,
        created_at=datetime.fromisoformat("2024-01-15T10:30:00"),
        description="A test prompt for create_version",
        author="Aryan Curiel",
        tags={"test"},
        model="gpt-4",
        changelog=["create_version test"],
    )
    return TemplateVersion(
        template_id=template_id,
        version=version,
        metadata=metadata,
    )


def test_local_template_store_list_templates__should_skip_non_directory_entries(
    temp_local_store: LocalTemplateStore,
    monkeypatch: pytest.MonkeyPatch,
):
    temp_local_store.base_path.mkdir(parents=True, exist_ok=True)
    (temp_local_store.base_path / "not_a_template.txt").write_text("ignore me")
    (temp_local_store.base_path / "template_a").mkdir()

    calls: list[str] = []

    def _fake_get_latest_version(template_id: str) -> TemplateVersion:
        calls.append(template_id)
        return _build_template_version(template_id=template_id, version="1.0.0")

    monkeypatch.setattr(
        temp_local_store, "get_latest_version", _fake_get_latest_version
    )

    templates = temp_local_store.list_templates()

    assert len(templates) == 1
    assert templates[0].id == "template_a"
    assert calls == ["template_a"]


def test_local_template_store_list_templates__should_return_templates_sorted_by_template_id(
    temp_local_store: LocalTemplateStore,
    monkeypatch: pytest.MonkeyPatch,
):
    temp_local_store.base_path.mkdir(parents=True, exist_ok=True)
    (temp_local_store.base_path / "z_template").mkdir()
    (temp_local_store.base_path / "a_template").mkdir()

    def _fake_get_latest_version(template_id: str) -> TemplateVersion:
        return _build_template_version(template_id=template_id, version="1.0.0")

    monkeypatch.setattr(
        temp_local_store, "get_latest_version", _fake_get_latest_version
    )

    templates = temp_local_store.list_templates()
    template_ids = [t.id for t in templates]

    assert template_ids == ["a_template", "z_template"]


def test_local_template_store_list_templates__should_skip_template_and_log_warning_on_template_not_found(
    temp_local_store: LocalTemplateStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    temp_local_store.base_path.mkdir(parents=True, exist_ok=True)
    (temp_local_store.base_path / "valid_template").mkdir()
    (temp_local_store.base_path / "missing_template").mkdir()

    def _fake_get_latest_version(template_id: str) -> TemplateVersion:
        if template_id == "missing_template":
            raise TemplateNotFoundError("not found")
        return _build_template_version(template_id=template_id, version="1.0.0")

    monkeypatch.setattr(
        temp_local_store, "get_latest_version", _fake_get_latest_version
    )

    with caplog.at_level("WARNING"):
        templates = temp_local_store.list_templates()

    template_ids = [t.id for t in templates]
    assert template_ids == ["valid_template"]
    assert (
        "No valid versions found for template 'missing_template'. Skipping."
        in caplog.text
    )


def _build_validation_error() -> ValidationError:
    try:
        TemplateVersionMetadata.model_validate({})
    except ValidationError as exc:
        return exc
    raise AssertionError("Expected ValidationError to be raised")


@pytest.mark.parametrize(
    "error",
    [
        ValueError("invalid value"),
        OSError("io error"),
        _build_validation_error(),
    ],
)
def test_local_template_store_list_templates__should_skip_template_and_log_error_on_read_errors(
    temp_local_store: LocalTemplateStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
):
    temp_local_store.base_path.mkdir(parents=True, exist_ok=True)
    (temp_local_store.base_path / "ok_template").mkdir()
    (temp_local_store.base_path / "bad_template").mkdir()

    def _fake_get_latest_version(template_id: str) -> TemplateVersion:
        if template_id == "bad_template":
            raise error
        return _build_template_version(template_id=template_id, version="1.0.0")

    monkeypatch.setattr(
        temp_local_store, "get_latest_version", _fake_get_latest_version
    )

    with caplog.at_level("ERROR"):
        templates = temp_local_store.list_templates()

    template_ids = [t.id for t in templates]
    assert template_ids == ["ok_template"]
    assert "Error reading template 'bad_template':" in caplog.text


def test_local_template_store_list_template_versions__should_raise_when_template_does_not_exist(
    local_store: LocalTemplateStore,
):
    with pytest.raises(TemplateNotFoundError):
        local_store.list_template_versions("non_existent_template")


def test_local_template_store_list_template_versions__should_return_list_of_versions(
    local_store: LocalTemplateStore,
):
    versions = local_store.list_template_versions("testing_prompt")
    assert isinstance(versions, list)
    assert len(versions) == 2


def test_local_template_store_list_template_versions__should_return_correct_versions_when_folder_correct(
    local_store: LocalTemplateStore,
):
    versions = local_store.list_template_versions("testing_prompt")
    version_strings = {str(v.version) for v in versions}
    assert "1.0.0" in version_strings
    assert "1.1.0" in version_strings


@pytest.mark.parametrize(
    "error",
    [
        ValueError("invalid value"),
        OSError("io error"),
        _build_validation_error(),
    ],
)
def test_local_template_store_list_template_versions__should_skip_version_and_log_error_on_read_errors(
    temp_local_store: LocalTemplateStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
):
    temp_local_store.base_path.mkdir(parents=True, exist_ok=True)
    template_dir = temp_local_store.base_path / "testing_prompt"
    template_dir.mkdir()

    (template_dir / "1.0.0").mkdir()
    (template_dir / "1.1.0").mkdir()
    (template_dir / "1.2.0").mkdir()

    def _fake_get_template_version(template_id: str, version: str) -> TemplateVersion:
        if version == "1.1.0":
            raise error
        return _build_template_version(template_id=template_id, version=version)

    monkeypatch.setattr(
        temp_local_store, "get_template_version", _fake_get_template_version
    )

    with caplog.at_level("ERROR"):
        versions = temp_local_store.list_template_versions("testing_prompt")

    version_strings = [str(v.version) for v in versions]
    assert version_strings == ["1.0.0", "1.2.0"]
    assert "Error reading template 'testing_prompt' version '1.1.0':" in caplog.text


def test_local_template_store_list_template_versions__should_skip_unexpected_folders(
    local_store: LocalTemplateStore,
):
    versions = local_store.list_template_versions("testing_prompt_unexpected_folder")
    version_strings = {str(v.version) for v in versions}
    assert "1.0.0" in version_strings


def test_local_template_store_list_template_versions__should_skip_unexpected_files(
    local_store: LocalTemplateStore,
):
    versions = local_store.list_template_versions("testing_prompt_unexpected_file")
    version_strings = {str(v.version) for v in versions}
    assert "1.0.0" in version_strings


def test_local_template_store_list_templates__should_handle_multiple_templates_with_mixed_errors(
    temp_local_store: LocalTemplateStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    temp_local_store.base_path.mkdir(parents=True, exist_ok=True)
    (temp_local_store.base_path / "template_good_1").mkdir()
    (temp_local_store.base_path / "template_value_error").mkdir()
    (temp_local_store.base_path / "template_os_error").mkdir()
    (temp_local_store.base_path / "template_validation_error").mkdir()
    (temp_local_store.base_path / "template_good_2").mkdir()

    def _fake_get_latest_version(template_id: str) -> TemplateVersion:
        if template_id == "template_value_error":
            raise ValueError("value error")
        elif template_id == "template_os_error":
            raise OSError("os error")
        elif template_id == "template_validation_error":
            raise _build_validation_error()
        return _build_template_version(template_id=template_id, version="1.0.0")

    monkeypatch.setattr(
        temp_local_store, "get_latest_version", _fake_get_latest_version
    )

    with caplog.at_level("ERROR"):
        templates = temp_local_store.list_templates()

    template_ids = [t.id for t in templates]
    assert template_ids == ["template_good_1", "template_good_2"]
    assert "Error reading template 'template_value_error':" in caplog.text
    assert "Error reading template 'template_os_error':" in caplog.text
    assert "Error reading template 'template_validation_error':" in caplog.text


def test_local_template_store_get_latest_version__should_raise_when_no_versions_exist(
    local_store: LocalTemplateStore,
):
    with pytest.raises(TemplateNotFoundError):
        local_store.get_latest_version("testing_prompt_no_versions")


def test_local_template_store_get_latest_version__should_return_latest_version(
    local_store: LocalTemplateStore,
):
    latest = local_store.get_latest_version("testing_prompt")
    assert str(latest.version) == "1.1.0"


def test_local_template_store_create_version__should_create_files_with_empty_content_when_strategy_empty(
    temp_local_store: LocalTemplateStore,
):
    temp_local_store.create_version(
        template_id="testing_prompt",
        version="1.0.0",
        strategy=CreationStrategy.EMPTY,
    )

    version_path = temp_local_store.base_path / "testing_prompt" / "1.0.0"
    metadata_path = version_path / "metadata.yml"
    template_path = version_path / "template.md"

    assert version_path.exists()
    assert metadata_path.exists()
    assert template_path.exists()
    assert template_path.read_text() == ""


def test_local_template_store_create_version__should_raise_when_version_already_exists(
    temp_local_store: LocalTemplateStore,
):
    version_path = temp_local_store.base_path / "testing_prompt" / "1.0.0"
    version_path.mkdir(parents=True, exist_ok=False)

    with pytest.raises(VersionAlreadyExistsError):
        temp_local_store.create_version(
            template_id="testing_prompt",
            version="1.0.0",
            strategy=CreationStrategy.EMPTY,
        )


def test_local_template_store_create_version__should_copy_latest_template_content_when_strategy_from_previous(
    temp_local_store: LocalTemplateStore,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    previous_version = _build_template_version(
        template_id="testing_prompt", version="0.9.0"
    )
    monkeypatch.setattr(
        temp_local_store, "get_latest_version", lambda _: previous_version
    )
    previous_template_path = temp_local_store._get_template_path(
        "testing_prompt", previous_version.version
    )
    previous_template_path.parent.mkdir(parents=True, exist_ok=True)
    previous_template_path.write_text("previous content")

    temp_local_store.create_version(
        template_id="testing_prompt",
        version="1.0.0",
        strategy=CreationStrategy.FROM_PREVIOUS_VERSION,
    )

    created_template_path = (
        temp_local_store.base_path / "testing_prompt" / "1.0.0" / "template.md"
    )
    assert created_template_path.read_text() == "previous content"


def test_local_template_store_create_version__should_fallback_to_empty_content_when_no_previous_version(
    temp_local_store: LocalTemplateStore,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    def _raise_not_found(_: str):
        raise TemplateNotFoundError("not found")

    monkeypatch.setattr(temp_local_store, "get_latest_version", _raise_not_found)

    with caplog.at_level("WARNING"):
        temp_local_store.create_version(
            template_id="testing_prompt",
            version="1.0.0",
            strategy=CreationStrategy.FROM_PREVIOUS_VERSION,
        )

    created_template_path = (
        temp_local_store.base_path / "testing_prompt" / "1.0.0" / "template.md"
    )
    assert created_template_path.read_text() == ""
    assert "No existing versions found for template 'testing_prompt'" in caplog.text


def test_local_template_store_create_version__should_dump_metadata_using_model_dump_json_mode(
    temp_local_store: LocalTemplateStore,
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict = {}

    def _fake_safe_dump(data):
        captured["data"] = data
        return "serialized-metadata"

    monkeypatch.setattr(local_store_module, "safe_dump", _fake_safe_dump)

    metadata = TemplateVersionMetadata(
        template_id="testing_prompt",
        version="1.0.0",
        created_at=datetime.fromisoformat("2024-01-15T10:30:00"),
        description="A test prompt for create_version",
        author="Aryan Curiel",
        tags={"test"},
        model="gpt-4",
        changelog=["create_version test"],
    )
    temp_local_store.create_version(
        template_id="testing_prompt",
        version="1.0.0",
        metadata=metadata,
        strategy=CreationStrategy.EMPTY,
    )

    metadata_path = (
        temp_local_store.base_path / "testing_prompt" / "1.0.0" / "metadata.yml"
    )
    assert captured["data"] == metadata.model_dump(mode="json")
    assert metadata_path.read_text() == "serialized-metadata"


def test_local_template_store_create_template__should_create_files(
    temp_local_store: LocalTemplateStore,
):
    temp_local_store.create_template(
        template_id="testing_prompt",
    )

    version_path = temp_local_store.base_path / "testing_prompt" / "1.0.0"
    metadata_path = version_path / "metadata.yml"
    template_path = version_path / "template.md"

    assert version_path.exists()
    assert metadata_path.exists()
    assert template_path.exists()
    assert template_path.read_text() == ""


def test_local_template_store_create_version__should_create_with_content_when_strategy_with_content(
    temp_local_store: LocalTemplateStore,
):
    temp_local_store.create_version(
        template_id="testing_prompt",
        version="1.0.0",
        strategy=CreationStrategy.WITH_CONTENT,
        content="Hello, world!",
    )

    template_path = (
        temp_local_store.base_path / "testing_prompt" / "1.0.0" / "template.md"
    )
    assert template_path.read_text() == "Hello, world!"


def test_local_template_store_create_version__should_warn_when_content_provided_but_strategy_not_with_content(
    temp_local_store: LocalTemplateStore,
    caplog: pytest.LogCaptureFixture,
):
    with caplog.at_level("WARNING"):
        temp_local_store.create_version(
            template_id="testing_prompt",
            version="1.0.0",
            strategy=CreationStrategy.EMPTY,
            content="this will be ignored",
        )

    assert (
        "Content provided will be ignored because of the creation strategy."
        in caplog.text
    )
    template_path = (
        temp_local_store.base_path / "testing_prompt" / "1.0.0" / "template.md"
    )
    assert template_path.read_text() == ""


def test_local_template_store_create_version__should_warn_when_with_content_strategy_but_no_content(
    temp_local_store: LocalTemplateStore,
    caplog: pytest.LogCaptureFixture,
):
    with caplog.at_level("WARNING"):
        temp_local_store.create_version(
            template_id="testing_prompt",
            version="1.0.0",
            strategy=CreationStrategy.WITH_CONTENT,
        )

    assert (
        "Creation strategy 'WITH_CONTENT' specified but no content provided."
        in caplog.text
    )
    template_path = (
        temp_local_store.base_path / "testing_prompt" / "1.0.0" / "template.md"
    )
    assert template_path.read_text() == ""


def test_local_template_store_get_template_version_content__should_return_content(
    temp_local_store: LocalTemplateStore,
):
    temp_local_store.create_version(
        template_id="testing_prompt",
        version="1.0.0",
        strategy=CreationStrategy.WITH_CONTENT,
        content="Hello from template!",
    )

    content = temp_local_store.get_template_version_content("testing_prompt", "1.0.0")
    assert content == "Hello from template!"


def test_local_template_store_get_template_path__should_return_correct_path(
    local_store: LocalTemplateStore,
):
    path = local_store._get_template_path("testing_prompt", "1.0.0")
    expected = local_store.base_path / "testing_prompt" / "1.0.0" / "template.md"
    assert path == expected


def test_local_template_store_get_metadata_path__should_return_correct_path(
    local_store: LocalTemplateStore,
):
    path = local_store._get_metadata_path("testing_prompt", "1.0.0")
    expected = local_store.base_path / "testing_prompt" / "1.0.0" / "metadata.yml"
    assert path == expected


def test_local_template_store_list_template_versions__should_skip_version_dir_without_metadata(
    temp_local_store: LocalTemplateStore,
):
    """A version directory that exists but has no metadata.yml should be silently skipped."""
    template_dir = temp_local_store.base_path / "testing_prompt"
    template_dir.mkdir(parents=True, exist_ok=True)

    # Create a valid version directory
    valid_version_dir = template_dir / "1.0.0"
    valid_version_dir.mkdir()
    (valid_version_dir / "metadata.yml").write_text(
        "template_id: testing_prompt\n"
        "version: 1.0.0\n"
        "created_at: '2025-01-01T00:00:00'\n"
        "description: valid\n"
        "changelog:\n  - init\n"
    )
    (valid_version_dir / "template.md").write_text("Hello")

    # Create an invalid version directory (no metadata.yml)
    invalid_version_dir = template_dir / "2.0.0"
    invalid_version_dir.mkdir()

    versions = temp_local_store.list_template_versions("testing_prompt")
    assert len(versions) == 1
    assert str(versions[0].version) == "1.0.0"
