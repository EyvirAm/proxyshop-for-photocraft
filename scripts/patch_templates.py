#!/usr/bin/env python3
"""Add the missing Planeswalker Transform front ``convertdfc`` icon.

The downloaded ``pw-tf-front.psd`` and ``pw-tf-front-extended.psd`` templates
do not contain the hidden ``convertdfc`` layer that ``PlaneswalkerTFTemplate``
expects for cards using the generic transform icon (for example Arlinn Kord,
INR #230).  This script adds it using the upward white triangle from
``tf-front.psd``.

The script is idempotent: templates that already have the layer are skipped.
A ``<name>.psd.bak`` backup is created before a template is modified.

Usage:
    python scripts/patch_templates.py
    python scripts/patch_templates.py --check
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable

from psd_tools import PSDImage

TARGET_FILES = ("pw-tf-front.psd", "pw-tf-front-extended.psd")
SOURCE_FILE = "tf-front.psd"
FALLBACK_POSITION = (307, 291)  # left, top
LAYER_NAME = "convertdfc"


def find_layer(container: Iterable[Any], name: str) -> Any | None:
    """Return the first layer with ``name`` in ``container``, recursively."""
    for layer in container:
        if layer.name == name:
            return layer
        if layer.is_group():
            found = find_layer(layer, name)
            if found is not None:
                return found
    return None


def get_front_group(psd: Any, path: Path) -> Any:
    """Return the ``Transform/Front`` group of a template."""
    transform = find_layer(psd, "Transform")
    if transform is None or not transform.is_group():
        raise ValueError(f"{path}: missing 'Transform' group")
    front = find_layer(transform, "Front")
    if front is None or not front.is_group():
        raise ValueError(f"{path}: missing 'Transform/Front' group")
    return front


def load_source_icon(templates_dir: Path) -> Any:
    """Load the front-facing convert icon from ``tf-front.psd``."""
    source_path = templates_dir / SOURCE_FILE
    if not source_path.is_file():
        raise FileNotFoundError(
            f"Source template not found: {source_path}. "
            f"It is needed for the front-facing {LAYER_NAME} icon."
        )

    source_psd = PSDImage.open(source_path)
    source_layer = find_layer(source_psd, LAYER_NAME)
    if source_layer is None:
        raise ValueError(f"{source_path}: missing '{LAYER_NAME}' layer")

    icon = source_layer.topil()
    if icon is None:
        raise ValueError(f"{source_path}: could not rasterize '{LAYER_NAME}'")

    # Do not use pw-tf-back.psd here: its convertdfc icon points down and is
    # intended for back faces.
    return icon.convert("RGBA")


def target_position(front: Any) -> tuple[int, int]:
    """Match the position of the other transform icons when possible."""
    reference = find_layer(front, "originpwdfc") or find_layer(
        front, "compasslanddfc"
    )
    if reference is not None and reference.left is not None:
        return reference.left, reference.top
    return FALLBACK_POSITION


def check_target(path: Path) -> bool:
    """Return True if ``path`` already contains the convertdfc layer."""
    if not path.is_file():
        print(f"[missing] {path.name}: file not found")
        return False

    psd = PSDImage.open(path)
    try:
        front = get_front_group(psd, path)
    except ValueError as exc:
        print(f"[error] {exc}")
        return False

    layer = find_layer(front, LAYER_NAME)
    if layer is None:
        print(f"[missing] {path.name}: no '{LAYER_NAME}' layer")
        return False

    print(f"[ok] {path.name}: '{LAYER_NAME}' at {layer.bbox}")
    return True


def patch_target(path: Path, icon: Any) -> bool:
    """Add the icon to ``path``. Return True if a change was made."""
    if not path.is_file():
        print(f"[error] {path.name}: file not found")
        return False

    psd = PSDImage.open(path)
    front = get_front_group(psd, path)

    if (existing := find_layer(front, LAYER_NAME)) is not None:
        print(f"[ok] {path.name}: '{LAYER_NAME}' already present at {existing.bbox}")
        return False

    left, top = target_position(front)
    layer = psd.create_pixel_layer(icon, name=LAYER_NAME, top=top, left=left)
    layer.visible = False
    front.append(layer)

    backup = path.with_name(f"{path.name}.bak")
    if not backup.exists():
        shutil.copy2(path, backup)
        print(f"[backup] {backup.name}")

    temp = path.with_name(f"{path.name}.tmp")
    try:
        psd.save(temp)
        temp.replace(path)
    except Exception:
        temp.unlink(missing_ok=True)
        raise

    print(f"[patched] {path.name}: '{LAYER_NAME}' at {layer.bbox}")
    return True


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--templates-dir",
        type=Path,
        default=repo_root / "templates",
        help="Directory containing the downloaded .psd templates "
        "(default: repository's templates/ directory).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only verify the patches; exit non-zero if any is missing.",
    )
    args = parser.parse_args()

    templates_dir: Path = args.templates_dir
    if not templates_dir.is_dir():
        parser.error(f"templates directory not found: {templates_dir}")

    targets = [templates_dir / name for name in TARGET_FILES]

    if args.check:
        results = [check_target(path) for path in targets]
        if not all(results):
            print(
                "\nRun 'python scripts/patch_templates.py' to apply the "
                "missing patches.",
                file=sys.stderr,
            )
            return 1
        print("\nAll template patches are present.")
        return 0

    missing = [path for path in targets if not path.is_file()]
    if missing:
        for path in missing:
            print(f"[error] {path.name}: file not found", file=sys.stderr)
        return 1

    icon = load_source_icon(templates_dir)
    changed = False
    for path in targets:
        changed |= patch_target(path, icon)

    if changed:
        print("\nTemplate patches applied. Verify with a render or run "
              "'python scripts/patch_templates.py --check'.")
    else:
        print("\nNothing to do: all template patches are already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
