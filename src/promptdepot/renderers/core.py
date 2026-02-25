from abc import ABC, abstractmethod
from typing import Self


class PromptRenderer[Template, ConfigDict](ABC):
    def __init__(self, template: Template, *, config: ConfigDict):
        self.template = template
        self.config = config

    @classmethod
    def from_template(cls, template: Template, *, config: ConfigDict) -> Self:
        return cls(template=template, config=config)

    @abstractmethod
    def render(self, *, context: dict) -> str: ...
