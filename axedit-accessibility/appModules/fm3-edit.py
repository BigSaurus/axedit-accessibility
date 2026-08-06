# Axe-Edit III Accessibility - NVDA app module
# Copyright (C) 2026 Big Saurus
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2, as published by the
# Free Software Foundation. This program is distributed WITHOUT ANY WARRANTY.
# See the LICENSE file (GNU GPL v2) distributed with this add-on for details.

"""
appModules/fm3-edit.py

Binds the shared Fractal editor support to FM3-Edit (FM3).

UNTESTED -- see the notes in ``fm9-edit.py``, which apply identically here.
The executable name ``FM3-Edit.exe`` comes from Fractal's macOS bundle
``FM3-Edit.app``.

Press NVDA+Shift+D with FM3-Edit focused to save a diagnostic dump to the
Desktop.
"""

try:
    from .fractalEditCore import AppModule  # noqa: F401
except ImportError:  # pragma: no cover - defensive; package context varies
    from appModules.fractalEditCore import AppModule  # noqa: F401
