from collections.abc import Mapping
from typing import Any, Generic, TypeVar, cast

from promptdepot.stores import TemplateStore, PromptVersion
from promptdepot.renderers import PromptRenderer

TID = TypeVar("TID")
TemplateT = TypeVar("TemplateT")
ConfigDictT = TypeVar("ConfigDictT", bound=dict)


class PromptDepotManager(Generic[TID, TemplateT, ConfigDictT]):
    def __init__(
        self,
        store: TemplateStore[TID, TemplateT],
        renderer: type[PromptRenderer[TemplateT, ConfigDictT]],
        *,
        default_config: ConfigDictT | None = None,
    ):
        self.store = store
        self.renderer_cls = renderer
        self.renderer_factory: dict[
            tuple[TID, str], PromptRenderer[TemplateT, ConfigDictT]
        ] = {}
        self.default_config: ConfigDictT = (
            cast(ConfigDictT, dict(default_config))
            if default_config is not None
            else cast(ConfigDictT, {})
        )

    def get_prompt(
        self,
        template_id: TID,
        version: PromptVersion,
        context: Mapping[str, Any],
    ) -> str:
        versioned_template_id = (template_id, str(version))
        renderer = self.renderer_factory.get(versioned_template_id)
        if not renderer:
            template = self.store.get_template(template_id, version)
            renderer = self.renderer_cls.from_template(
                template,
                config=cast(ConfigDictT, dict(self.default_config)),
            )
            self.renderer_factory[versioned_template_id] = renderer

        return renderer.render(context=dict(context))
