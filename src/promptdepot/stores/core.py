from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import datetime
from enum import Enum
from typing import Annotated, Any, TypeAlias

from pydantic import BaseModel, Field
from pydantic_extra_types.semantic_version import SemanticVersion

PromptVersion: TypeAlias = SemanticVersion | str


class CreationStrategy(Enum):
    FROM_PREVIOUS_VERSION = "from_previous_version"
    EMPTY = "empty"
    WITH_CONTENT = "with_content"


class Template(BaseModel):
    id: str
    latest_version: SemanticVersion


class TemplateVersionMetadata(BaseModel):
    template_id: str
    version: SemanticVersion
    created_at: Annotated[datetime, Field(default_factory=datetime.now)]
    description: str | None = None
    author: str | None = None
    tags: set[str] = set()
    model: str | None = None
    changelog: list[str] = []


class TemplateVersion(BaseModel):
    template_id: str
    version: SemanticVersion
    metadata: TemplateVersionMetadata


class TemplateStore(ABC):
    def __init__(self, *, config: Mapping[str, Any] | None = None):
        self.config: Mapping[str, Any] = config or {}

    @abstractmethod
    def list_templates(self) -> list[Template]: ...

    @abstractmethod
    def get_template(self, template_id: str) -> Template: ...

    @abstractmethod
    def create_template(
        self,
        template_id: str,
    ) -> None: ...

    @abstractmethod
    def list_template_versions(self, template_id: str) -> list[TemplateVersion]: ...

    @abstractmethod
    def get_template_version(
        self, template_id: str, version: PromptVersion
    ) -> TemplateVersion: ...

    @abstractmethod
    def create_version(
        self,
        template_id: str,
        version: PromptVersion,
        metadata: TemplateVersionMetadata | None = None,
        *,
        strategy: CreationStrategy = CreationStrategy.FROM_PREVIOUS_VERSION,
        content: str | None = None,
    ) -> None: ...

    @abstractmethod
    def get_template_version_content(
        self, template_id: str, version: PromptVersion
    ) -> str: ...
