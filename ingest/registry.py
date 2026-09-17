"""
Finds every exchange automatically.

It looks inside ingest/exchanges/, opens each file, and picks up any
exchange defined there. This is why adding an exchange never requires
editing the worker - dropping in the file is enough.
"""

import importlib
import pkgutil

from ingest import exchanges as exchanges_package
from ingest.base import Exchange


def load_exchanges():
    """Returns {slug: exchange} for every exchange file found."""
    found = {}
    for module_info in pkgutil.iter_modules(exchanges_package.__path__):
        if module_info.name.startswith("_"):
            continue  # files starting with _ are ignored, e.g. a draft
        module = importlib.import_module(f"{exchanges_package.__name__}.{module_info.name}")
        for value in vars(module).values():
            if isinstance(value, type) and issubclass(value, Exchange) and value is not Exchange:
                value.check_setup()
                if value.SLUG in found:
                    raise ValueError(f"Two exchange files both use the slug '{value.SLUG}'")
                found[value.SLUG] = value()
    return dict(sorted(found.items()))
