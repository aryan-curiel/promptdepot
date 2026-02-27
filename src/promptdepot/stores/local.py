import logging
from pathlib import Path
from typing import TypedDict

from pydantic import ValidationError
from pydantic_extra_types.semantic_version import SemanticVersion
from yaml import safe_dump, safe_load

from promptdepot.stores.core import (
    CreationStrategy,
    PromptVersion,
    Template,
    TemplateStore,
    TemplateVersion,
    TemplateVersionMetadata,
)


class TemplateNotFoundError(FileNotFoundError):
    """Raised when a template or template version is not found."""

    pass


class VersionAlreadyExistsError(FileExistsError):
    """Raised when trying to create a template version that already exists."""

    pass


class StoreConfig(TypedDict):
    base_path: Path | str
    initial_version: SemanticVersion | None
    template_file_name: str | None
    metadata_file_name: str | None


class LocalTemplateStore(TemplateStore):
    def __init__(self, *, config: StoreConfig):
        super().__init__(config=config)
        self.base_path: Path = (
            Path(config["base_path"])
            if isinstance(config["base_path"], str)
            else config["base_path"]
        )
        self.initial_version = config.get("initial_version") or SemanticVersion(major=1)
        self.template_file_name: str = config.get("template_file_name") or "template.md"
        self.metadata_file_name: str = (
            config.get("metadata_file_name") or "metadata.yml"
        )
        self.logger = logging.getLogger(self.__class__.__name__)

    def _read_prompt_metadata(self, metadata_path: Path) -> TemplateVersionMetadata:
        if not metadata_path.exists():
            raise TemplateNotFoundError(f"Metadata file not found at '{metadata_path}'")

        metadata_content = metadata_path.read_text()
        metadata_dict = safe_load(metadata_content)
        return TemplateVersionMetadata.model_validate(metadata_dict)

    def _get_template_path(self, template_id: str, version: PromptVersion) -> Path:
        version_str = str(version)
        return self.base_path / template_id / version_str / self.template_file_name

    def _get_metadata_path(self, template_id: str, version: PromptVersion) -> Path:
        version_str = str(version)
        return self.base_path / template_id / version_str / self.metadata_file_name

    def get_template(self, template_id: str) -> Template:
        try:
            latest_version = self.get_latest_version(template_id)
            return Template(id=template_id, latest_version=latest_version.version)
        except TemplateNotFoundError as e:
            raise TemplateNotFoundError(f"Template '{template_id}' not found") from e

    def get_template_version(
        self,
        template_id: str,
        version: PromptVersion,
    ) -> TemplateVersion:
        version = (
            SemanticVersion.parse(version) if isinstance(version, str) else version
        )
        metadata_path = self._get_metadata_path(template_id, version)
        metadata = self._read_prompt_metadata(metadata_path)
        template_path = self._get_template_path(template_id, version)
        if not template_path.exists():
            raise TemplateNotFoundError(
                f"Template file not found at '{template_path}' for template '{template_id}' version '{version}'"
            )
        return TemplateVersion(
            template_id=template_id,
            version=version,
            metadata=metadata,
        )

    def list_templates(self) -> list[Template]:
        templates: list[Template] = []
        for template_dir in sorted(
            self.base_path.iterdir(), key=lambda path: path.name
        ):
            if not template_dir.is_dir():
                continue
            template_id = template_dir.name
            try:
                latest_version = self.get_latest_version(template_id)
                templates.append(
                    Template(id=template_id, latest_version=latest_version.version)
                )
            except TemplateNotFoundError:
                self.logger.warning(
                    f"No valid versions found for template '{template_id}'. Skipping."
                )
            except (ValidationError, ValueError, OSError) as e:
                self.logger.error(
                    f"Error reading template '{template_id}': {e}. Skipping."
                )
        return templates

    def list_template_versions(self, template_id: str) -> list[TemplateVersion]:
        template_dir = self.base_path / template_id
        if not template_dir.exists() or not template_dir.is_dir():
            raise TemplateNotFoundError(f"Template '{template_id}' not found")

        versions: list[TemplateVersion] = []
        for version_dir in sorted(template_dir.iterdir(), key=lambda path: path.name):
            if not version_dir.is_dir():
                continue
            version = version_dir.name
            try:
                template_version = self.get_template_version(template_id, version)
                versions.append(template_version)
            except TemplateNotFoundError:
                continue
            except (ValidationError, ValueError, OSError) as e:
                self.logger.error(
                    f"Error reading template '{template_id}' version '{version}': {e}"
                )
        return versions

    def get_latest_version(self, template_id: str) -> TemplateVersion:
        versions = self.list_template_versions(template_id)
        if not versions:
            raise TemplateNotFoundError(
                f"No versions found for template '{template_id}'"
            )
        latest_version = max(versions, key=lambda x: x.version)
        return latest_version

    def create_version(
        self,
        template_id: str,
        version: PromptVersion,
        metadata: TemplateVersionMetadata | None = None,
        *,
        strategy: CreationStrategy = CreationStrategy.FROM_PREVIOUS_VERSION,
        content: str | None = None,
    ) -> None:
        template_content = ""
        if content is not None and strategy != CreationStrategy.WITH_CONTENT:
            self.logger.warning(
                "Content provided will be ignored because of the creation strategy."
            )

        if strategy == CreationStrategy.WITH_CONTENT:
            if content is None:
                self.logger.warning(
                    "Creation strategy 'WITH_CONTENT' specified but no content provided. Creating version with empty content."
                )
            else:
                template_content = content
        elif strategy == CreationStrategy.FROM_PREVIOUS_VERSION:
            try:
                latest_template = self.get_latest_version(template_id)
                template_path = self._get_template_path(
                    template_id, latest_template.version
                )
                template_content = template_path.read_text()
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

        metadata = metadata or TemplateVersionMetadata(
            template_id=template_id,
            version=SemanticVersion.parse(version)
            if isinstance(version, str)
            else version,
        )  # ty:ignore[missing-argument]
        metadata_content = safe_dump(metadata.model_dump(mode="json"))
        self._get_metadata_path(template_id, version).write_text(metadata_content)

        self._get_template_path(template_id, version).write_text(template_content)

    def create_template(
        self,
        template_id: str,
    ) -> None:
        self.create_version(
            template_id=template_id,
            version=self.initial_version,
            strategy=CreationStrategy.EMPTY,
        )

    def get_template_version_content(
        self, template_id: str, version: PromptVersion
    ) -> str:
        return self._get_template_path(template_id, version).read_text()
