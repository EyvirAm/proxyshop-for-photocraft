"""
* Utils: UXP Paths

Create Photoshop paths from point descriptors.
"""
from __future__ import annotations
from collections.abc import Iterable
from functools import cached_property
from typing import NotRequired, TypedDict

from .base import uxp


class PointConf(TypedDict):
    """Fields of ``PointConf``."""
    x: float | int
    y: float | int


class PathPointConf(PointConf):
    """Path point configuration for UXP paths."""
    left: NotRequired[PointConf]
    right: NotRequired[PointConf]


class _PathCache:
    @cached_property
    def create_path_template_script(self) -> str:
        """Create path template script."""
        return uxp.read_script("createPath.js")


_cache = _PathCache()


def create_path(points: Iterable[PathPointConf]) -> None:
    """Creates a path layer according to the given points."""
    uxp.run_script(_cache.create_path_template_script, points)
