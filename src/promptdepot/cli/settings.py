import sys
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    TomlConfigSettingsSource,
)


class StoreSettings(BaseModel):
    """Store-related settings."""

    config: Annotated[dict[str, Any], Field(default_factory=dict)]


class PyprojectTomlSource(TomlConfigSettingsSource):
    """Reads settings from the ``[tool.promptdepot]`` table in pyproject.toml."""

    def _read_file(self, file_path: Path) -> dict[str, Any]:
        if sys.version_info < (3, 11):
            import tomli as toml_lib  # noqa: S403  # ty:ignore[unresolved-import]
        else:
            import tomllib as toml_lib  # type: ignore[no-redef]

        with file_path.open(mode="rb") as f:
            data = toml_lib.load(f)

        return data.get("tool", {}).get("promptdepot", {})


class Settings(BaseSettings):
    """CLI settings read from ``[tool.promptdepot]`` in pyproject.toml."""

    store_path: str = "promptdepot.stores.local.LocalTemplateStore"
    store: StoreSettings = StoreSettings()  # ty:ignore[missing-argument]

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            PyprojectTomlSource(settings_cls, toml_file=Path("pyproject.toml")),
        )


settings = Settings()
