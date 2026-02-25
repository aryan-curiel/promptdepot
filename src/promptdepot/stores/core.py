from abc import ABC, abstractmethod
from enum import Enum
from typing import Generic, TypeAlias, TypeVar

from pydantic_extra_types.semantic_version import SemanticVersion

PromptVersion: TypeAlias = SemanticVersion | str
TID = TypeVar("TID")
TTemplate = TypeVar("TTemplate")


class CreationStrategy(Enum):
    FROM_PREVIOUS_VERSION = "from_previous_version"
    EMPTY = "empty"


class TemplateStore(Generic[TID, TTemplate], ABC):
    @abstractmethod
    def get_template(self, template_id: TID, version: PromptVersion) -> TTemplate: ...

    @abstractmethod
    def list_templates(self) -> list[tuple[TID, TTemplate]]: ...

    @abstractmethod
    def list_template_versions(
        self, template_id: TID
    ) -> list[tuple[SemanticVersion, TTemplate]]: ...

    @abstractmethod
    def create_version(
        self,
        template_id: TID,
        version: PromptVersion,
        template: TTemplate,
        strategy: CreationStrategy = CreationStrategy.FROM_PREVIOUS_VERSION,
    ) -> None: ...

    @abstractmethod
    def create_template(
        self,
        template_id: TID,
        template: TTemplate,
    ) -> None: ...

    @abstractmethod
    def get_template_content(
        self, template_id: TID, version: PromptVersion
    ) -> str: ...
