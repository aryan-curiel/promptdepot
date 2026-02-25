from typing import TypedDict

from jinja2 import Environment

from promptdepot.renderers.core import PromptRenderer


class Jinja2PromptRendererConfig(TypedDict):
    environment: Environment | None


class Jinja2PromptRenderer(PromptRenderer[str, Jinja2PromptRendererConfig]):
    def __init__(self, template: str, *, config: Jinja2PromptRendererConfig):
        super().__init__(template=template, config=config)
        self.env = config.get("environment") or Environment(autoescape=True)
        self.compiled_template = self.env.from_string(template)

    def render(self, *, context: dict) -> str:
        return self.compiled_template.render(**context)
