import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, ValidationError
from pydantic_extra_types.semantic_version import SemanticVersion
from yaml import safe_dump, safe_load

from promptdepot.stores.core import (
    CreationStrategy,
    PromptVersion,
    TemplateStore,
)


class TemplateNotFoundError(FileNotFoundError):
    """Raised when a template or template version is not found."""

    pass


class VersionAlreadyExistsError(FileExistsError):
    """Raised when trying to create a template version that already exists."""

    pass


class PromptMetadata(BaseModel):
    schema_version: SemanticVersion = SemanticVersion(major=1)
    version: SemanticVersion
    created_at: datetime
    name: str
    description: str | None = None
    author: str | None = None
    template_file: str = "template.mako"
    readme_file: str = "README.md"
    tags: Annotated[set[str], Field(default_factory=set)]
    model: str | None = None
    changelog: Annotated[list[str], Field(default_factory=list)]


class PromptTemplate(BaseModel):
    metadata: PromptMetadata
    template_path: Path


class LocalTemplateStore(TemplateStore[str, PromptTemplate]):
    def __init__(self, *, base_path: Path | str):
        self.base_path = Path(base_path) if isinstance(base_path, str) else base_path
        self.logger = logging.getLogger(self.__class__.__name__)

    def _read_prompt_metadata(self, metadata_path: Path) -> PromptMetadata:
        if not metadata_path.exists():
            raise TemplateNotFoundError(f"Metadata file not found at '{metadata_path}'")

        metadata_content = metadata_path.read_text()
        metadata_dict = safe_load(metadata_content)
        return PromptMetadata.model_validate(metadata_dict)

    def get_template(
        self,
        template_id: str,
        version: PromptVersion,
    ) -> PromptTemplate:
        version_path = self.base_path / template_id / str(version)
        metadata_path = version_path / "metadata.yml"
        metadata = self._read_prompt_metadata(metadata_path)
        template_path = version_path / metadata.template_file
        if not template_path.exists():
            raise TemplateNotFoundError(
                f"Template file not found at '{template_path}' for template '{template_id}' version '{version}'"
            )
        return PromptTemplate(metadata=metadata, template_path=template_path)

    def list_templates(self) -> list[tuple[str, PromptTemplate]]:
        templates = []
        for template_dir in sorted(
            self.base_path.iterdir(), key=lambda path: path.name
        ):
            if not template_dir.is_dir():
                continue
            template_id = template_dir.name
            try:
                latest_version = self.get_latest_version(template_id)
                templates.append((template_id, latest_version))
            except TemplateNotFoundError:
                self.logger.warning(
                    f"No valid versions found for template '{template_id}'. Skipping."
                )
            except (ValidationError, ValueError, OSError) as e:
                self.logger.error(
                    f"Error reading template '{template_id}': {e}. Skipping."
                )
        return templates

    def list_template_versions(
        self, template_id: str
    ) -> list[tuple[SemanticVersion, PromptTemplate]]:
        template_dir = self.base_path / template_id
        if not template_dir.exists() or not template_dir.is_dir():
            raise TemplateNotFoundError(f"Template '{template_id}' not found")

        versions = []
        for version_dir in sorted(template_dir.iterdir(), key=lambda path: path.name):
            if not version_dir.is_dir():
                continue
            version = version_dir.name
            try:
                template = self.get_template(template_id, version)
                versions.append((SemanticVersion.parse(version), template))
            except TemplateNotFoundError:
                continue
            except (ValidationError, ValueError, OSError) as e:
                self.logger.error(
                    f"Error reading template '{template_id}' version '{version}': {e}"
                )
        return versions

    def get_latest_version(self, template_id: str) -> PromptTemplate:
        versions = self.list_template_versions(template_id)
        if not versions:
            raise TemplateNotFoundError(
                f"No versions found for template '{template_id}'"
            )
        latest_version = max(versions, key=lambda x: x[0])
        return latest_version[1]

    def create_version(
        self,
        template_id: str,
        version: PromptVersion,
        template: PromptTemplate,
        strategy: CreationStrategy = CreationStrategy.FROM_PREVIOUS_VERSION,
    ) -> None:
        template_content = ""
        if strategy == CreationStrategy.FROM_PREVIOUS_VERSION:
            try:
                latest_template = self.get_latest_version(template_id)
                template_content = latest_template.template_path.read_text()
            except TemplateNotFoundError:
                self.logger.warning(
                    f"No existing versions found for template '{template_id}'. Creating new version with empty content."
                )
                template_content = ""
        version_path = self.base_path / template_id / str(version)
        if version_path.exists():
            raise VersionAlreadyExistsError(
                f"Version '{version}' for template '{template_id}' already exists"
            )
        version_path.mkdir(parents=True, exist_ok=False)

        metadata_path = version_path / "metadata.yml"
        metadata_content = safe_dump(template.metadata.model_dump(mode="json"))
        metadata_path.write_text(metadata_content)

        template_dest_path = version_path / template.metadata.template_file

        template_dest_path.write_text(template_content)

    def create_template(
        self,
        template_id: str,
        template: PromptTemplate,
    ) -> None:
        self.create_version(
            template_id=template_id,
            version=template.metadata.version,
            template=template,
            strategy=CreationStrategy.EMPTY,
        )

    def get_template_content(self, template_id: str, version: PromptVersion) -> str:
        template = self.get_template(template_id, version)
        return template.template_path.read_text()
