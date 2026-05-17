from __future__ import annotations

import sys

__version__ = "10.1.2"

# v11.5 Docker runtime compatibility:
# The application is loaded as src.socmint.* in Docker/Gunicorn, while a number of
# legacy v7-v10 product modules still use absolute imports such as
# `import socmint` or `from socmint.foo import bar`. Expose the current package
# under the historical top-level name so those legacy modules register cleanly
# without requiring broad invasive rewrites in every archived smoke/module file.
sys.modules.setdefault("socmint", sys.modules[__name__])
