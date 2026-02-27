import importlib

from promptdepot.cli.settings import settings
from promptdepot.stores.core import TemplateStore


def get_store() -> TemplateStore:
    """Get the template store instance based on CLI settings."""
    store_path = settings.store_path
    store_config = settings.store.config

    module_path, class_name = store_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    store_cls = getattr(module, class_name)
    return store_cls(config=store_config)
