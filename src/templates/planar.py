"""
* PLANAR TEMPLATES
"""
from __future__ import annotations

from collections.abc import Callable
from functools import cached_property

from photoshop.api._artlayer import ArtLayer

import src.helpers as psd
import src.text_layers as text_classes
from src.enums.layers import LAYERS
from src.helpers.bounds import get_layer_height
from src.helpers.text import set_text_size_and_leading
from src.layouts import NormalLayout
from src.templates._core import StarterTemplate

"""
* Template Classes
"""


class PlanarTemplate(StarterTemplate):
    """Planar template for Planar and Phenomenon cards introduced in the Planechase block.

    Todo:
        Needs a complete rework and a 'Modifier' class.
    """

    def __init__(self, layout: NormalLayout):
        super().__init__(layout)
        self.config.exit_early = True

    @cached_property
    def text_layer_static_ability(self) -> ArtLayer | None:
        return psd.getLayer(LAYERS.STATIC_ABILITY, self.text_group)

    @cached_property
    def text_layer_chaos_ability(self) -> ArtLayer | None:
        return psd.getLayer(LAYERS.CHAOS_ABILITY, self.text_group)

    @cached_property
    def text_layer_chaos_symbol(self) -> ArtLayer | None:
        return psd.getLayer(LAYERS.CHAOS_SYMBOL, self.text_group)

    @cached_property
    def has_dark_band(self) -> bool:
        """Whether the official frame for this card has a dark chaos band.

        Classic Planechase frames do; Phenomenon cards and the special PUNK
        and PSSC frames do not.
        """
        return (
            self.layout.type_line != LAYERS.PHENOMENON
            and (self.layout.set or "").lower() not in {"punk", "pssc"}
        )

    def basic_text_layers(self):
        """No mana cost, don't scale name layer."""
        if self.text_layer_name:
            self.text.append(
                text_classes.TextField(
                    layer=self.text_layer_name, contents=self.layout.name
                )
            )
        if self.text_layer_type:
            self.text.append(
                text_classes.ScaledTextField(
                    layer=self.text_layer_type,
                    contents=self.layout.type_line,
                    reference=self.type_reference,
                )
            )

    def rules_text_and_pt_layers(self):
        if self.has_dark_band:
            psd.enable_mask(psd.getLayerSet(LAYERS.TEXTBOX))
        else:
            psd.disable_mask(psd.getLayerSet(LAYERS.TEXTBOX))

        # Phenomenon card?
        if self.layout.type_line == LAYERS.PHENOMENON:
            # Insert oracle text into static ability layer and disable chaos ability & layer mask on textbox
            if self.text_layer_static_ability:
                self.text.append(
                    text_classes.FormattedTextField(
                        layer=self.text_layer_static_ability,
                        contents=self.layout.oracle_text,
                    )
                )
            if layer := psd.getLayer(LAYERS.CHAOS_SYMBOL, self.text_group):
                layer.visible = False
            if self.text_layer_chaos_ability:
                self.text_layer_chaos_ability.visible = False

        else:
            # Split oracle text on last line break, insert everything before into static, the rest into chaos
            linebreak_index = self.layout.oracle_text.rindex("\n")
            if self.text_layer_static_ability:
                self.text.append(
                    text_classes.FormattedTextField(
                        layer=self.text_layer_static_ability,
                        contents=self.layout.oracle_text[0:linebreak_index],
                    )
                )
            if self.text_layer_chaos_ability:
                self.text.append(
                    text_classes.FormattedTextField(
                        layer=self.text_layer_chaos_ability,
                        contents=self.layout.oracle_text[linebreak_index + 1 :],
                    )
                )

    @cached_property
    def textbox_group(self) -> psd.LayerSet:
        """LayerSet: The brown textbox panel behind the rules text."""
        return psd.getLayerSet(LAYERS.TEXTBOX)

    @cached_property
    def post_text_methods(self) -> list[Callable[[], None]]:
        """Fit the static and chaos text inside the shared Planar textbox."""
        return [*super().post_text_methods, self.fit_planar_text]

    def _set_text_box(
        self, layer: ArtLayer, left: float, right: float, top: float, bottom: float
    ) -> None:
        """Set a text layer's paragraph box using document coordinates."""
        tr = getattr(layer, "_transform", [1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
        scale_x = abs(float(tr[0])) or 1.0
        scale_y = abs(float(tr[3])) or 1.0
        layer._set_text_box(
            left,
            top,
            max(1.0, (right - left) / scale_x),
            max(1.0, (bottom - top) / scale_y),
        )

    def _fit_layer_to_height(
        self, layer: ArtLayer, max_height: float, original_size: float
    ) -> None:
        """Shrink a text layer to fit, then use any spare room to grow it back."""
        for _ in range(6):
            height = get_layer_height(layer)
            if height <= max_height:
                break
            factor = max(0.5, max_height / height)
            if factor >= 0.999:
                break
            size = float(layer.textItem.size) * factor
            set_text_size_and_leading(layer, size, size)

        for _ in range(6):
            height = get_layer_height(layer)
            current = float(layer.textItem.size)
            if current >= original_size - 1e-3:
                break
            if max_height - height < 4:
                break
            grow = min(1.08, max_height / height, original_size / current)
            if grow <= 1.001:
                break
            set_text_size_and_leading(layer, current * grow, current * grow)
            if get_layer_height(layer) > max_height:
                set_text_size_and_leading(layer, current, current)
                break

    def _textbox_mask_top(self) -> float | None:
        """Return the document-space top of the textbox's layer mask."""
        textbox = self.textbox_group
        if not textbox:
            return None
        result = textbox._exec_photocraft(
            "edit.transform",
            {"layer": textbox.id, "dx": 0, "dy": 0, "target": "mask"},
        )
        rect = result.get("rect") if isinstance(result, dict) else None
        if not rect:
            return None
        return float(rect[1])

    def fit_planar_text(self) -> None:
        """Keep both rules-text layers inside the brown textbox and its dark band.

        The dark band is a gradient on the textbox group's mask.  Keep it at
        the template's position and reserve it for the chaos block; the static
        block lives above it.  Both blocks are scaled together because the
        official cards use one font size for the whole rules panel.
        """
        static = self.text_layer_static_ability
        chaos = self.text_layer_chaos_ability
        if not static:
            return

        has_chaos = bool(chaos and chaos.visible)
        side_margin = 120
        bottom_margin = 20
        gap = 24
        textbox = self.textbox_group
        left = static.bounds[0]
        right = (textbox.bounds[2] if textbox else self.docref.width) - side_margin
        static_top = static.bounds[1]
        safe_bottom = self.legal_group.bounds[1] - bottom_margin
        if right <= left or safe_bottom <= static_top:
            return

        # Measure against a box taller than the document: PhotoCraft clips
        # overflowing lines to the paragraph box, hiding the overflow.
        measure_bottom = max(safe_bottom, self.docref.height * 2)
        self._set_text_box(static, left, right, static_top, measure_bottom)
        static_size = float(static.textItem.size)
        static_height = get_layer_height(static)

        if has_chaos:
            self._set_text_box(
                chaos, chaos.bounds[0], right, chaos.bounds[1], measure_bottom
            )
            chaos_size = float(chaos.textItem.size)
            chaos_height = get_layer_height(chaos)

            if self.has_dark_band:
                # The template's mask already puts the dark band where the
                # official frame has it.  Keep that position and fit both
                # blocks into their own regions: static above the band, chaos
                # inside it.  They share a font size on the real cards.
                band_top = self._textbox_mask_top()
                if band_top is None:
                    band_top = safe_bottom - 120
                static_max = max(1.0, band_top - gap - static_top)
                chaos_max = max(1.0, safe_bottom - band_top - gap)
                limit = min(
                    static_max / max(1.0, static_height),
                    chaos_max / max(1.0, chaos_height),
                )
                if limit < 0.999:
                    factor = max(0.5, limit)
                    for layer in (static, chaos):
                        size = float(layer.textItem.size) * factor
                        set_text_size_and_leading(layer, size, size)

                # Use any spare room to restore the template's size, but never
                # push either block out of its region.
                for _ in range(6):
                    static_height = get_layer_height(static)
                    chaos_height = get_layer_height(chaos)
                    grow = min(
                        static_max / max(1.0, static_height),
                        chaos_max / max(1.0, chaos_height),
                        static_size / float(static.textItem.size),
                        chaos_size / float(chaos.textItem.size),
                        1.08,
                    )
                    if grow <= 1.001:
                        break
                    for layer in (static, chaos):
                        size = float(layer.textItem.size) * grow
                        set_text_size_and_leading(layer, size, size)
                    if (
                        get_layer_height(static) > static_max
                        or get_layer_height(chaos) > chaos_max
                    ):
                        for layer in (static, chaos):
                            size = float(layer.textItem.size) / grow
                            set_text_size_and_leading(layer, size, size)
                        break

                chaos_height = get_layer_height(chaos)
                chaos_top = safe_bottom - chaos_height
                if abs(chaos.bounds[1] - chaos_top) >= 0.5:
                    offset = chaos_top - chaos.bounds[1]
                    chaos.translate(0, offset)
                    if symbol := self.text_layer_chaos_symbol:
                        symbol.translate(0, offset)

            else:
                # No band: use the whole panel and let the chaos block continue
                # directly below the static text, like a normal rules box.
                static_max = safe_bottom - static_top
                for _ in range(8):
                    static_height = get_layer_height(static)
                    chaos_height = get_layer_height(chaos)
                    total = static_height + chaos_height + gap
                    if total <= static_max:
                        break
                    factor = max(0.5, static_max / total)
                    if factor >= 0.999:
                        break
                    for layer in (static, chaos):
                        size = float(layer.textItem.size) * factor
                        set_text_size_and_leading(layer, size, size)

                static_height = get_layer_height(static)
                chaos_height = get_layer_height(chaos)
                chaos_top = static_top + static_height + gap
                if chaos_top + chaos_height > safe_bottom:
                    chaos_top = safe_bottom - chaos_height
                if abs(chaos.bounds[1] - chaos_top) >= 0.5:
                    offset = chaos_top - chaos.bounds[1]
                    chaos.translate(0, offset)
                    if symbol := self.text_layer_chaos_symbol:
                        symbol.translate(0, offset)

        else:
            static_max = safe_bottom - static_top
            self._fit_layer_to_height(static, static_max, static_size)

        self._set_text_box(
            static, left, right, static_top, static_top + max(1.0, static_max)
        )

    def paste_scryfall_scan(
        self, rotate: bool = False, visible: bool = False
    ) -> ArtLayer | None:
        """Ensure we rotate the scan for Planar cards."""
        return super().paste_scryfall_scan(rotate=True, visible=visible)
