# Template patches

Proxyshop's `.psd` templates are large binary assets downloaded through the app.
They are **not stored in this repository**, so any fix made directly to a
template has to be reapplied whenever the template bundle is updated (or bundled
with a release).

This page records those fixes. Run `python scripts/patch_templates.py --check`
before packaging a fork/release to verify they are present.

## Template source folder

Templates are downloaded from the shared Google Drive folder set in
`TEMPLATES_DRIVE_FOLDER` (default:
`1CkgrLFTh1lDQ1mgzustL_893IDJ8EQ3a`, the [fork template folder](https://drive.google.com/drive/folders/1CkgrLFTh1lDQ1mgzustL_893IDJ8EQ3a)).

Files are matched by name, so re-uploading a template with the same name is
enough to publish a new version; the updater picks it up without editing
`src/data/manifest.yml`. Files that are not present in the folder keep using
the ID recorded in the manifest. Folder listing requires `API_GOOGLE`.

> **Note:** the updater uses the file's Drive **description** as its version
> when it is set; otherwise it falls back to the file's **modification time**,
> so replacing a template automatically publishes a new version. To publish a
> readable version, set the description in Drive (for example `v1.0.1`).

## Planeswalker Transform front: missing `convertdfc` icon

The two copies currently in the shared Drive folder already include this layer;
run `python scripts/patch_templates.py --check` to confirm.

**Files:** `templates/pw-tf-front.psd`, `templates/pw-tf-front-extended.psd`

**Symptom:** the transform icon in the top-left circle is empty for transform
planeswalkers whose layout falls back to the generic convert icon, for example
**Arlinn Kord** (`INR` #230). Cards with a dedicated icon (`originpwdfc`,
`sunmoondfc`, etc.) are unaffected.

**Cause:** `PlaneswalkerTFTemplate` looks up `Transform/Front/<transform_icon>`.
For those cards `NormalLayout.transform_icon` is `TransformIcons.CONVERT`, i.e.
the layer name `convertdfc`. Unpatched front template bundles only contain
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
