"""
* Utils: UXP BatchPlay

Build and run batchPlay action descriptors.
"""
from __future__ import annotations
from functools import cached_property
from typing import Literal, NotRequired, TypedDict

from .base import uxp


class ActionTarget(TypedDict):
    """Fields of ``ActionTarget``."""
    _ref: str


class ActionTargetID(ActionTarget):
    """Target a batchPlay action by numeric ID."""
    _id: int


class ActionTargetName(ActionTarget):
    """Target a batchPlay action by name."""
    _name: str


class ActionTargetIndex(ActionTarget):
    """Target a batchPlay action by index."""
    _index: int


class ActionTargetEnumeration(ActionTarget):
    """Target a batchPlay action by enumeration value."""
    _enum: NotRequired[str]
    _value: NotRequired[str]


class ActionTargetProperty(ActionTarget):
    """Target a batchPlay action property."""
    _property: str


class OptionsDescriptor(TypedDict):
    """Fields of ``OptionsDescriptor``."""
    dialogOptions: NotRequired[Literal["silent", "dontDisplay", "display"]]
    suppressProgressBar: NotRequired[bool]


class ActionDescriptor(TypedDict):
    """Fields of ``ActionDescriptor``."""
    _target: NotRequired[
        list[
            ActionTarget
            | ActionTargetID
            | ActionTargetName
            | ActionTargetIndex
            | ActionTargetEnumeration
            | ActionTargetProperty
        ]
    ]
    _options: NotRequired[OptionsDescriptor]


class _Cache:
    @cached_property
    def batch_play_template_script(self) -> str:
        """Batch play template script."""
        return uxp.read_script("batchPlay.js")


_cache = _Cache()


def batch_play(*descriptors: ActionDescriptor) -> None:
    """Runs a batch play script in Photoshop."""
    uxp.run_script(_cache.batch_play_template_script, descriptors)
