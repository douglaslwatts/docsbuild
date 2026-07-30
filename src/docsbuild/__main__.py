"""Entry point for ``python -m docsbuild``.

The installed ``docsbuild`` command is the usual way in. This module exists so the tool
also runs straight from a checkout, before anything is installed.
"""

from __future__ import annotations

from docsbuild import main

if __name__ == "__main__":
    main()
