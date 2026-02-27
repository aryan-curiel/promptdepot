from collections.abc import Mapping
from typing import Any, Generic, TypeVar, cast

from promptdepot.renderers import PromptRenderer
from promptdepot.stores import PromptVersion, TemplateStore

ConfigDictT = TypeVar("ConfigDictT", bound=Mapping[str, Any])


class PromptDepotManager(Generic[ConfigDictT]):
    def __init__(
        self,
        store: TemplateStore,
        renderer: type[PromptRenderer[str, ConfigDictT]],
        *,
        default_config: ConfigDictT | None = None,
    ):
        self.store = store
        self.renderer_cls = renderer
        self.renderer_cache: dict[
            tuple[str, str], PromptRenderer[str, ConfigDictT]
        ] = {}
        self.default_config: ConfigDictT = (
            cast(ConfigDictT, dict(default_config))
            if default_config is not None
            else cast(ConfigDictT, {})
        )

    def get_prompt(
        self,
        template_id: str,
        version: PromptVersion,
        context: Mapping[str, Any],
    ) -> str:
        versioned_template_id = (template_id, str(version))
        renderer = self.renderer_cache.get(versioned_template_id)
        if renderer is None:
            template_content = self.store.get_template_version_content(
                template_id, version
            )
            renderer = self.renderer_cls.from_template(
                template_content,
                config=cast(ConfigDictT, dict(self.default_config)),
            )
            self.renderer_cache[versioned_template_id] = renderer

        return renderer.render(context=context)
