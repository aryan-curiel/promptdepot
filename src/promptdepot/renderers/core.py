from collections.abc import Mapping
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any
from typing_extensions import Self


TemplateT = TypeVar("TemplateT")
ConfigDictT = TypeVar("ConfigDictT")


class PromptRenderer(Generic[TemplateT, ConfigDictT], ABC):
    def __init__(self, template: TemplateT, *, config: ConfigDictT):
        self.template = template
        self.config = config

    @classmethod
    def from_template(
        cls,
        template: TemplateT,
        *,
        config: ConfigDictT,
    ) -> Self:
        return cls(template=template, config=config)

    @abstractmethod
    def render(self, *, context: Mapping[str, Any]) -> str: ...
