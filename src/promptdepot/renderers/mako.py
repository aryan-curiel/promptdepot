from collections.abc import Mapping
from typing import TypedDict, Any

from mako.lookup import TemplateLookup
from mako.template import Template

from promptdepot.renderers.core import PromptRenderer


class MakoPromptRendererConfig(TypedDict):
    lookup: TemplateLookup | None


class MakoPromptRenderer(PromptRenderer[str, MakoPromptRendererConfig]):
    def __init__(self, template: str, *, config: MakoPromptRendererConfig):
        super().__init__(template=template, config=config)
        self.compiled_template = Template(template, lookup=config.get("lookup"))  # noqa: S702

    def render(self, *, context: Mapping[str, Any]) -> str:
        return self.compiled_template.render(**context)
