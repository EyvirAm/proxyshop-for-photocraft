# Architecture

This page describes how Proxyshop turns card data into a rendered image. It is
meant as an entry point for contributors; each module carries its own
docstrings for the details.

## Pipeline overview

```text
art file + tags
      │
      ▼
src/cards.py ──────────────► Scryfall / Hexproof data
      │                       (src/utils/scryfall.py, src/utils/hexapi.py)
      ▼
src/layouts.py ────────────► NormalLayout (or a layout subclass)
      │                       card text, colors, frame data, faces
      ▼
src/render/setup.py ───────► RenderOperation
      │                       layout + template class + config
      ▼
src/templates/_core.py ────► BaseTemplate.execute()
      │                       frame layers → text layers → post-text → save
      ▼
photoshop/api + src/utils/adobe.py
      │                       PhotoCraft compatibility layer
      ▼
rendered JPG / PNG / PSD
```

The render queue (`src/render/render_queue.py`) owns pending `RenderOperation`
objects and can pause, resume, cancel or skip an operation. `before_render`
hooks and manual editing pauses live in the operation/template layer.

## Repository layout

| Path | Responsibility |
| --- | --- |
| `src/cards.py` | Parse art file names/tags and turn Scryfall data into card details. |
| `src/layouts.py` | Map Scryfall layouts to `NormalLayout` subclasses and expose card text, frame colors and faces. |
| `src/frame_logic.py` | Decide frame colors, twins, pinlines and special rarities. |
| `src/text_layers.py` | Text fields, formatted text, scaling/fitting and dividers. |
| `src/templates/` | Template classes and modifiers that drive Photoshop layers. |
| `src/render/` | Render operations, queueing and pause/cancel handling. |
| `src/_loader.py` | Plugin and template loading, manifest parsing, update checks. |
| `src/_config.py` | Settings schemas, INI persistence and `AppConfig`. |
| `src/gui/qml/` | QML views, dialogs and tools. |
| `src/gui/qml/models/` | Python Qt models exposed to QML. |
| `photoshop/api/` | PhotoCraft-backed stand-in for `photoshop-python-api`. |
| `src/utils/adobe.py` | Photoshop/PhotoCraft handler and reference layers. |
| `src/utils/uxp/` | UXP batchPlay, path, shape and text helpers. |
| `scripts/` | Build, compress, template patch and documentation audit tools. |
| `docs/` | Template patch notes, documentation plan and this page. |

## Card data and layouts

`assign_layout()` in `src/layouts.py` fetches Scryfall data, optionally lets the
user edit it, processes card details and instantiates the layout class mapped to
`scryfall.layout`. Every layout subclasses `NormalLayout`, which exposes:

- card text (`name`, `oracle_text`, `type_line`, `flavor_text`, power/toughness),
- colors and frame data (`pinlines`, `twins`, `background`, `identity`),
- collector info (`set`, `rarity`, `collector_data`, `artist`),
- face helpers (`other_face_*`, transform/MDFC flags, panorama data).

`SplitLayout` additionally exposes per-half lists (`names`, `type_lines`,
`oracle_texts`, …) and `join_dual_card_layouts()` merges the two halves of a
split card before rendering.

## Templates

A template maps a manifest entry (`src/data/manifest.yml`) to a Python class and
the layouts it supports:

```yaml
normal.psd:
  id: "<drive-file-id>"
  templates:
    Normal:
      M15Template:
        - normal
```

`AppTemplate` resolves the PSD path, config handlers, Drive ID and version.
`NamedTemplate`/`AssembledTemplate` group the same display name across template
classes.

`BaseTemplate.execute()` runs the render in stages:

1. `load_frame_layers()` / `enable_frame_layers()` — choose frame textures and
   color layers.
2. `basic_text_layers()` — mana, name, type line.
3. `rules_text_and_pt_layers()` — rules, flavor and power/toughness.
4. `post_text_methods` — dividers, icons, Saga/Planeswalker positioning, etc.
5. Save the document and emit the result.

Template modifiers (`NyxMod`, `CompanionMod`, `FullartMod`, `VectorMod`,
`TransformMod`, `SagaMod`, …) override single steps and are composed through
multiple inheritance. `NormalTemplate` is the usual base for raster templates;
`VectorTemplate` adds generated color layers and shape masks.

## Configuration

Defaults are declared in `src/data/config/app.toml` and
`src/data/config/base.toml`; saved values live in `src/data/config_ini/*.ini`.
`ConfigHandler` validates values against the schema and persists them.
`AppConfig` merges app-wide and template-specific settings and exposes typed
properties (`lang`, `scry_sorting`, `fill_mode`, …) used during rendering.

Environment settings (`API_GOOGLE`, `TEMPLATES_DRIVE_FOLDER`, …) come from
`src/data/env.yml`, then `env.default.yml`, then OS environment variables.

## Template download and updates

Templates are not tracked in the repository. They are resolved by file name in
the shared Google Drive folder configured by `TEMPLATES_DRIVE_FOLDER`; files
missing from the folder fall back to the IDs in `src/data/manifest.yml`.

`AppTemplate.check_for_update()` uses the Drive file description as the version
when present, otherwise its modification time. `update_template()` downloads the
file (and extracts a `.7z` archive when needed). See
[Template patches](template-patches.md) for the manual PSD fixes that must be
reapplied after a template bundle update.

## GUI

`src/gui/qml/App.qml` is the main window. Views, dialogs and tools under
`src/gui/qml/{views,dialogs,tools,components}/` are thin QML layers over the Qt
models in `src/gui/qml/models/`. Those models wrap the template library, render
queue, settings, plugin manager and file/message dialogs. Python objects are
exposed to QML with Qt properties, slots and signals; the models keep the
Pydantic data structures in sync with the UI.

## Testing and documentation

- `pytest -q` runs the API, card, text and PhotoCraft integration tests.
- Render test cases live in `src/data/tests/` and are queued from the Tests menu.
- `python scripts/check_docs.py` reports docstring coverage; the plan and
  progress log are in [Documentation plan](documentation-plan.md).

## Extending the project

- **New template**: add its entry to `src/data/manifest.yml`, implement the
  template class/modifier in `src/templates/`, then add a preview and (optional)
  config schema.
- **New plugin**: create `plugins/<Name>/` with `manifest.yml` and `py/`; the
  plugin manifest uses the same file table as the built-in manifest.
- **New layout**: add the Scryfall layout name to `layout_map` and subclass
  `NormalLayout` (or an existing layout) with the required properties.
