# Documentation plan

This plan tracks the incremental documentation of the Proxyshop fork. It is a
living document: update the status boxes and the progress log as modules are
documented.

## Goals

1. Every Python module has a docstring describing its responsibility.
2. Every public class, method, property and function documents what it does,
   its arguments, return value and raised exceptions when relevant.
3. Existing documentation (README, `docs/`, docstrings) stays accurate as the
   code changes.
4. No behavior changes: documentation passes only add docstrings, comments and
   type annotations.

## Conventions

- Documentation is written in **English**, matching the existing repo.
- Module headers keep the repository style:
  ```python
  """
  * Area: Module Name

  Short description of the module's responsibility.
  """
  ```
- Use Google-style sections (`Args:`, `Keyword Args:`, `Returns:`, `Raises:`)
  for non-trivial callables; one-line summaries are enough for simple
  properties and overrides.
- Document **what** and **why**, not a line-by-line restatement of the code.
- Type-only declarations and nested closures are excluded from coverage:
  - `@overload` stubs
  - protocol/abstract methods whose body is only `...`
  - functions defined inside another function
- Do not reflow unrelated code, rename symbols or change signatures (return
  annotations may be added when the implementation already matches).

## Measuring progress

`scripts/check_docs.py` reports module and public-API coverage:

```bash
python scripts/check_docs.py            # summary + worst files
python scripts/check_docs.py --top 30   # longer ranking
python scripts/check_docs.py --missing src/layouts.py
```

Verification after each batch:

```bash
python -m compileall -q src scripts photoshop plugins tests
python -m pytest -q --ignore=tests/test_photocraft_backend.py
```

## Current baseline

- Modules with a docstring: **141 / 141**
- Public classes/functions documented: **2492 / 2492**

## Phases

### Phase 1 — Domain core (highest priority)

These modules define the card data model, settings and text formatting used by
everything else.

- [x] `src/text_layers.py` — text fields, formatted text, fitting and dividers
- [x] `src/_config.py` — settings schemas, config handlers and app config
- [x] `src/layouts.py` — card layouts and layout-specific data
- [x] `src/cards.py`, `src/enums/mtg.py`, `src/enums/settings.py` — card
      parsing and enumerations
- [x] `src/utils/scryfall.py`, `src/utils/hexapi.py` — card data sources

### Phase 2 — Template engine (complete)

- [x] `src/templates/_core.py` — base template workflow
- [x] `src/templates/normal.py` — normal frame variants
- [x] `src/templates/saga.py`, `planeswalker.py`, `classes.py` — specialised
      templates
- [x] `src/templates/transform.py`, `planar.py`, `case.py`, `station.py`,
      `adventure.py`, `battle.py`, `leveler.py`, `split.py`, `prepare.py`,
      `token.py`
- [x] `src/templates/_cosmetic.py`, `_vector.py` helpers

### Phase 3 — Photoshop API adapter (complete)

- [x] `photoshop/api/__init__.py` — public API surface
- [x] `photoshop/api/_document.py`
- [x] `photoshop/api/_layer.py`
- [x] `photoshop/api/_selection.py`
- [x] `photoshop/api/_artlayer.py`, `_layerSet.py`
- [x] `photoshop/api/enumerations.py`, `text_item.py`, `path_item.py`

### Phase 4 — Utilities and integrations (complete)

- [x] `src/utils/adobe.py` — Photoshop/PhotoCraft handler
- [x] `src/utils/uxp/*` — UXP batchPlay/path/shape/text helpers
- [x] `src/helpers/*` — layer, text, bounds, color and position helpers
- [x] Remaining `src/utils/*` (git, github, inputs, images, threading, ...)

### Phase 5 — GUI models (complete)

- [x] `src/gui/qml/models/pydantic_q_list_model.py`
- [x] `src/gui/qml/models/message_dialog_content_model.py`
- [x] `src/gui/qml/models/render_operations_model.py`
- [x] `src/gui/qml/models/batch_rendering_model.py`, `settings_model.py`,
      `template_list_model.py` and the remaining models

### Phase 6 — Plugins and maintenance scripts (complete)

- [x] `plugins/Investigamer/py/*` and `plugins/SilvanMTG/py/*`
- [x] `scripts/*` (build, compress, patch, doc audit)
- [x] Test helpers that still lack docstrings

## Definition of done per module

A module is marked done when:

1. `python scripts/check_docs.py --missing <module>` prints nothing.
2. `python -m compileall -q <module>` succeeds.
3. The relevant tests still pass.
4. Any README/`docs/` statements about that module were checked and corrected
   if needed.

## Progress log

### Iteration 1

- Added module docstrings to all Python modules (141/141).
- Documented the new Google Drive template source and version resolution:
  `src/utils/download.py`, `src/_loader.py`, `src/_state.py`,
  `src/startup.py`, `src/gui/qml/models/template_updater_model.py`.
- Documented `src/text_layers.py` (text fields, formatted text, areas).
- Documented `src/_config.py` (settings models, `ConfigHandler`, `AppConfig`).
- Started `src/layouts.py`: typed data models and `NormalLayout` core/panorama
  properties documented; layout-specific properties still pending.
- Reviewed and corrected `README.md`, `docs/template-patches.md` and the
  `scripts/patch_templates.py` docstring to match the Drive folder workflow.
- Added `scripts/check_docs.py` to measure coverage.
- Next up: finish `src/layouts.py`, then `src/templates/_core.py` and
  `src/templates/normal.py`.

### Iteration 2

- Completed `src/layouts.py` (all layout classes and their properties).
- Completed the template engine: `_core.py`, `normal.py`, `saga.py`,
  `planeswalker.py`, `classes.py`, `transform.py`, `planar.py`, `case.py`,
  `station.py`, `adventure.py`, `battle.py`, `leveler.py`, `split.py`,
  `prepare.py`, `token.py`, `_cosmetic.py` and `_vector.py`.
- Documented most of the Photoshop API adapter: `_document.py`, `_layer.py`,
  `_selection.py`, `_artlayer.py`, `_layerSet.py`, `enumerations.py`,
  `text_item.py` and `path_item.py`.
- Coverage moved from 1530 to 1924 documented public APIs.
- Next up: `photoshop/api/__init__.py` (111 pending), then Phase 4
  (`src/utils/adobe.py`, `src/utils/uxp/*`, helpers).

### Iteration 3

- Finished the Photoshop API adapter, including `photoshop/api/__init__.py`.
- Documented all remaining utilities, helpers, integrations, GUI models,
  plugins, scripts and test helpers.
- Public API coverage reached **2492 / 2492** with **141 / 141** modules
  documented.
- Verified with `compileall` and the test suite.

### Iteration 4 — expanded documentation

- Added `docs/architecture.md`: pipeline overview, repository map, layouts,
  templates, configuration, download/update flow, GUI, tests and extension
  points.
- Added file-level comments to all 26 QML files (main window, components,
  dialogs, tools and views).
- Added JSDoc/file headers to the four TypeScript files under `src_js/` and
  `scripts_js/`.
- Linked the architecture page and this plan from `README.md`.
