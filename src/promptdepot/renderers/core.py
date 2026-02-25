from abc import ABC, abstractmethod
from typing import Generic, TypeVar


TemplateT = TypeVar("TemplateT")
ConfigDictT = TypeVar("ConfigDictT")
PromptRendererT = TypeVar("PromptRendererT", bound="PromptRenderer")


class PromptRenderer(Generic[TemplateT, ConfigDictT], ABC):
    def __init__(self, template: TemplateT, *, config: ConfigDictT):
        self.template = template
        self.config = config

    @classmethod
    def from_template(
        cls: type[PromptRendererT],
        template: TemplateT,
        *,
        config: ConfigDictT,
    ) -> PromptRendererT:
        return cls(template=template, config=config)

    @abstractmethod
    def render(self, *, context: dict) -> str: ...
