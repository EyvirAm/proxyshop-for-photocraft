"""
Photocraft-backed compatibility layer for the `photoshop` Python package.
Allows Proxyshop to run without Adobe Photoshop COM by routing operations
to Photocraft (`photocraft-cli` / headless engine) and native Python PSD/image tools.
"""
from __future__ import annotations

from photoshop import api

__all__ = ["api"]
