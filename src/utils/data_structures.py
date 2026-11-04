"""
* Utils: Data Structures

Model parsing/dumping and collection search helpers.
"""
from __future__ import annotations
import tomllib
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

import yaml
from pydantic import BaseModel


def first[T](iterable: Iterable[T]) -> T:
    """Return the first item of ``iterable``."""
    return next(iter(iterable))


def get_item[T](sequence: Sequence[T], idx: int) -> T | None:
    """Return the item at ``idx``, or None when out of range."""
    return sequence[idx] if -1 < idx < len(sequence) else None


def find_item[T](iterable: Iterable[T], condition: Callable[[T], bool]) -> T | None:
    """Return the first item matching ``condition``."""
    for item in iterable:
        if condition(item):
            return item
    return None


def find_index[T](iterable: Iterable[T], condition: Callable[[T], bool]) -> int:
    """Return the index of the first match, or -1."""
    for idx, item in enumerate(iterable):
        if condition(item):
            return idx
    return -1


def find_last_index[T](sequence: Sequence[T], condition: Callable[[T], bool]) -> int:
    """Return the index of the last match, or -1."""
    for idx, item in enumerate(reversed(sequence)):
        if condition(item):
            return len(sequence) - 1 - idx
    return -1


def parse_model[T: BaseModel](path: Path, model: type[T]) -> T:
    """Parse a JSON, TOML or YAML file into ``model``."""
    if path.suffix == ".json":
        return model.model_validate_json(path.read_bytes())
    elif path.suffix == ".toml":
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return model.model_validate(data)
    elif path.suffix in (".yaml", ".yml"):
        with open(path, "rb") as f:
            data = yaml.safe_load(f)
        return model.model_validate(data)
    raise NotImplementedError(
        f"{
            model
        } can be parsed only from .json, .toml, .yaml and .yml files. Got file: {path}"
    )


def dump_model(path: Path, model: BaseModel) -> None:
    """Dump model."""
    with open(path, "w", encoding="utf-8") as f:
        if path.suffix == ".json":
            f.write(model.model_dump_json())
        elif path.suffix in (".yaml", ".yml"):
            yaml.dump(model.model_dump(), stream=f)
        else:
            raise NotImplementedError(
                f"{
                    type(model)
                } can be dumped only to .json, .yaml and .yml files. Got path: {path}"
            )
