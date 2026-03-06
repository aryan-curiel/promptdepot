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


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from content. Returns (frontmatter_dict, body)."""
    if not content.startswith("---\n"):
        return {}, content
    rest = content[4:]
    # Look for a closing delimiter on its own line: "\n---\n"
    end_idx = rest.find("\n---\n")
    if end_idx != -1:
        yaml_block = rest[:end_idx]
        body = rest[end_idx + 5 :]
    elif rest.endswith("\n---"):
        # Frontmatter with no body: closing delimiter at end of content
        yaml_block = rest[: -4]
        body = ""
    else:
        # No valid closing delimiter; treat as if there is no frontmatter
        return {}, content
    if body.startswith("\n"):
        body = body[1:]
    return safe_load(yaml_block) or {}, body


class LocalTemplateStore(TemplateStore):
    def __init__(self, *, config: StoreConfig):
        super().__init__(config=config)
        self.base_path: Path = (
            Path(config["base_path"])
            if isinstance(config["base_path"], str)
            else config["base_path"]
        )
        self.initial_version = config.get("initial_version") or SemanticVersion(major=1)
        self.logger = logging.getLogger(self.__class__.__name__)

    def _read_prompt_metadata(self, template_path: Path) -> TemplateVersionMetadata:
        if not template_path.exists():
            raise TemplateNotFoundError(f"Template file not found at '{template_path}'")

        content = template_path.read_text()
        frontmatter, _ = _parse_frontmatter(content)
        if not frontmatter:
            raise TemplateNotFoundError(
                f"No frontmatter found in template file '{template_path}'"
            )
        return TemplateVersionMetadata.model_validate(frontmatter)

    def _get_template_path(self, template_id: str, version: PromptVersion) -> Path:
        return self.base_path / template_id / f"{version}.md"

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
        template_path = self._get_template_path(template_id, version)
        metadata = self._read_prompt_metadata(template_path)
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
        for version_file in sorted(template_dir.iterdir(), key=lambda path: path.name):
            if not version_file.is_file() or version_file.suffix != ".md":
                continue
            version = version_file.stem
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
                template_content = self.get_template_version_content(
                    template_id, latest_template.version
                )
            except TemplateNotFoundError:
                self.logger.warning(
                    f"No existing versions found for template '{template_id}'. Creating new version with empty content."
                )
                template_content = ""

        template_file = self._get_template_path(template_id, version)
        if template_file.exists():
            raise VersionAlreadyExistsError(
                f"Version '{version}' for template '{template_id}' already exists"
            )
        template_file.parent.mkdir(parents=True, exist_ok=True)

        metadata = metadata or TemplateVersionMetadata(
            template_id=template_id,
            version=SemanticVersion.parse(version)
            if isinstance(version, str)
            else version,
        )  # ty:ignore[missing-argument]
        yaml_block = safe_dump(metadata.model_dump(mode="json"))
        file_content = f"---\n{yaml_block}---\n{template_content}"
        template_file.write_text(file_content)

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
        template_path = self._get_template_path(template_id, version)
        try:
            content = template_path.read_text()
        except FileNotFoundError as e:
            raise TemplateNotFoundError(
                f"Template file not found for template '{template_id}', "
                f"version '{version}', at path '{template_path}'"
            ) from e
        _, body = _parse_frontmatter(content)
        return body
