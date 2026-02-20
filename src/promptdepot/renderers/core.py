from abc import ABC, abstractmethod
from typing import Self


class PromptRenderer[_Template, _ConfigDict](ABC):
    def __init__(self, template: _Template, *, config: _ConfigDict):
        self.template = template
        self.config = config

    @classmethod
    def from_template(cls, template: _Template, *, config: _ConfigDict) -> Self:
        return cls(template=template, config=config)

    @abstractmethod
    def render(self, *, context: dict) -> str: ...
