from collections.abc import Mapping
from typing import Any

import pytest
from promptdepot.manager import PromptDepotManager
from promptdepot.renderers.core import PromptRenderer
from promptdepot.stores.core import (
    CreationStrategy,
    PromptVersion,
    Template,
    TemplateStore,
    TemplateVersion,
    TemplateVersionMetadata,
)


class StubStore(TemplateStore):
    def __init__(self) -> None:
        super().__init__()
        self.get_template_version_content_calls: list[tuple[str, str]] = []

    def get_template(self, template_id: str) -> Template:
        return Template(id=template_id, latest_version="1.0.0")

    def get_template_version(
        self, template_id: str, version: PromptVersion
    ) -> TemplateVersion:
        metadata = TemplateVersionMetadata(
            template_id=template_id, version=str(version)
        )
        return TemplateVersion(
            template_id=template_id, version=str(version), metadata=metadata
        )

    def list_templates(self) -> list[Template]:
        return []

    def list_template_versions(self, template_id: str) -> list[TemplateVersion]:
        return []

    def create_version(
        self,
        template_id: str,
        version: PromptVersion,
        metadata: TemplateVersionMetadata | None = None,
        *,
        strategy: CreationStrategy = CreationStrategy.FROM_PREVIOUS_VERSION,
        content: str | None = None,
    ) -> None:
        return None

    def create_template(self, template_id: str) -> None:
        return None

    def get_template_version_content(
        self, template_id: str, version: PromptVersion
    ) -> str:
        version_str = str(version)
        self.get_template_version_content_calls.append((template_id, version_str))
        return f"{template_id}:{version_str}"


class RecordingRenderer(PromptRenderer[str, dict[str, Any]]):
    created_configs: list[dict[str, Any]] = []

    def __init__(self, template: str, *, config: dict[str, Any]):
        super().__init__(template=template, config=config)
        RecordingRenderer.created_configs.append(config)
        self.config["mutated_by_renderer"] = True

    def render(self, *, context: Mapping[str, Any]) -> str:
        return f"{self.template}|{context['name']}"


@pytest.fixture(autouse=True)
def reset_recording_renderer_configs() -> None:
    RecordingRenderer.created_configs = []


def test_prompt_depot_manager_get_prompt__should_cache_renderer_by_template_and_version():
    store = StubStore()
    manager = PromptDepotManager(
        store=store,
        renderer=RecordingRenderer,
        default_config={"flag": "x"},
    )

    first = manager.get_prompt("welcome", "1.0.0", {"name": "Alice"})
    second = manager.get_prompt("welcome", "1.0.0", {"name": "Bob"})
    third = manager.get_prompt("welcome", "1.1.0", {"name": "Cara"})

    assert first == "welcome:1.0.0|Alice"
    assert second == "welcome:1.0.0|Bob"
    assert third == "welcome:1.1.0|Cara"

    assert store.get_template_version_content_calls == [
        ("welcome", "1.0.0"),
        ("welcome", "1.1.0"),
    ]


def test_prompt_depot_manager_get_prompt__should_copy_default_config_per_renderer_creation():
    store = StubStore()
    external_default_config = {"flag": "x"}
    manager = PromptDepotManager(
        store=store,
        renderer=RecordingRenderer,
        default_config=external_default_config,
    )

    manager.get_prompt("welcome", "1.0.0", {"name": "Alice"})
    manager.get_prompt("welcome", "1.1.0", {"name": "Bob"})

    assert external_default_config == {"flag": "x"}

    assert len(RecordingRenderer.created_configs) == 2
    first_config, second_config = RecordingRenderer.created_configs
    assert first_config is not second_config
    assert first_config == {"flag": "x", "mutated_by_renderer": True}
    assert second_config == {"flag": "x", "mutated_by_renderer": True}


def test_prompt_depot_manager_get_prompt__should_accept_mapping_context():
    store = StubStore()
    manager = PromptDepotManager(
        store=store,
        renderer=RecordingRenderer,
        default_config={"flag": "x"},
    )

    context: Mapping[str, Any] = {"name": "Dana"}
    result = manager.get_prompt("welcome", "1.0.0", context)

    assert result == "welcome:1.0.0|Dana"
