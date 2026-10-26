# Template patches

Proxyshop's `.psd` templates are large binary assets downloaded through the app.
They are **not stored in this repository**, so any fix made directly to a
template has to be reapplied whenever the template bundle is updated (or bundled
with a release).

This page records those fixes. Run `python scripts/patch_templates.py --check`
before packaging a fork/release to verify they are present.

## Planeswalker Transform front: missing `convertdfc` icon

**Files:** `templates/pw-tf-front.psd`, `templates/pw-tf-front-extended.psd`

**Symptom:** the transform icon in the top-left circle is empty for transform
planeswalkers whose layout falls back to the generic convert icon, for example
**Arlinn Kord** (`INR` #230). Cards with a dedicated icon (`originpwdfc`,
`sunmoondfc`, etc.) are unaffected.

**Cause:** `PlaneswalkerTFTemplate` looks up `Transform/Front/<transform_icon>`.
For those cards `NormalLayout.transform_icon` is `TransformIcons.CONVERT`, i.e.
the layer name `convertdfc`. The current front templates only contain
`compasslanddfc`, `originpwdfc`, `mooneldrazidfc` and `sunmoondfc`, so
`psd.getLayer(...)` returns `None` and no icon is shown.

**Fix:** add a hidden pixel layer named `convertdfc` to `Transform/Front`:

| Property | Value |
| --- | --- |
| Position | aligned with `originpwdfc`, currently `left=307`, `top=291` |
| Size | 214×214 px |
| Visibility | hidden (the template code enables it per card) |
| Artwork | the **upward** white triangle from `templates/tf-front.psd` |

> **Important:** use the `convertdfc` asset from `tf-front.psd`, not the one
> from `pw-tf-back.psd`. The back template contains the **downward** triangle
> used on the back face; copying it to the front produces an inverted icon.

Apply the patch with:

```bash
python scripts/patch_templates.py
```

The script is idempotent, backs up each modified template as
`<name>.psd.bak`, and skips files that already contain the layer. To verify
without changing anything:

```bash
python scripts/patch_templates.py --check
```

## Verification

1. Render **Arlinn Kord** (`INR` #230) with both `PlaneswalkerTFTemplate`
   (Normal) and `PlaneswalkerTFBorderlessTemplate` (Borderless). Both should
   show a white upward triangle inside the icon circle.
2. Render **Nicol Bolas, the Arisen** (`M19` #218) and confirm it still shows
   its planeswalker (`originpwdfc`) icon.
3. Run `pytest -q`.
