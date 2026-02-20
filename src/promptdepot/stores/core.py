from abc import ABC, abstractmethod
from enum import Enum

from pydantic_extra_types.semantic_version import SemanticVersion

type PromptVersion = SemanticVersion | str


class CreationStrategy(Enum):
    FROM_PREVIOUS_VERSION = "from_previous_version"
    EMPTY = "empty"


class TemplateStore[_TID, _TTemplate](ABC):
    @abstractmethod
    def get_template(self, template_id: _TID, version: PromptVersion) -> _TTemplate: ...

    @abstractmethod
    def list_templates(self) -> list[tuple[_TID, _TTemplate]]: ...

    @abstractmethod
    def list_template_versions(
        self, template_id: _TID
    ) -> list[tuple[PromptVersion, _TTemplate]]: ...

    @abstractmethod
    def create_version(
        self,
        template_id: _TID,
        version: PromptVersion,
        template: _TTemplate,
        strategy: CreationStrategy = CreationStrategy.FROM_PREVIOUS_VERSION,
    ) -> None: ...

    @abstractmethod
    def create_template(
        self,
        template_id: _TID,
        template: _TTemplate,
    ) -> None: ...
