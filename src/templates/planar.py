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
            psd.enable_mask(psd.getLayerSet(LAYERS.TEXTBOX))
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

    def fit_planar_text(self) -> None:
        """Keep both rules-text layers inside the brown textbox with margins.

        The template ships with a textbox wide enough for the short text of the
        original Planechase cards. Newer Planes have much longer rules text, so
        we size the paragraph boxes to the visible brown panel and shrink both
        fonts together until the stacked text fits above the collector line.
        """
        static = self.text_layer_static_ability
        chaos = self.text_layer_chaos_ability
        if not static:
            return

        # Keep clear of the collector info and of the curved textbox border.
        # The panel's opaque edge is about 60px inside the group bounds, and
        # italic glyphs can overhang the paragraph box a little further.
        side_margin = 120
        bottom_margin = 40
        gap = 24
        textbox = self.textbox_group
        left = static.bounds[0]
        right = (textbox.bounds[2] if textbox else self.docref.width) - side_margin
        top = static.bounds[1]
        bottom = self.legal_group.bounds[1] - bottom_margin
        available = bottom - top
        if available <= 0 or right <= left:
            return

        # Use a tall box while measuring: a paragraph box that is too short
        # clips the overflowing lines, which would hide the overflow from the
        # height measurement below.
        measure_bottom = max(bottom, self.docref.height * 2)
        self._set_text_box(static, left, right, top, measure_bottom)
        if chaos and chaos.visible:
            self._set_text_box(
                chaos, chaos.bounds[0], right, chaos.bounds[1], measure_bottom
            )

        def heights() -> tuple[float, float]:
            return (
                get_layer_height(static),
                get_layer_height(chaos) if chaos and chaos.visible else 0.0,
            )

        layers = [layer for layer in (static, chaos) if layer and layer.visible]
        original_sizes = {id(layer): float(layer.textItem.size) for layer in layers}

        # Shrinking changes the line breaks, so measure and repeat a few times.
        for _ in range(5):
            static_height, chaos_height = heights()
            required = static_height + chaos_height + (gap if chaos_height else 0)
            if required <= available:
                break
            factor = max(0.1, available / required)
            for layer in layers:
                # `get_font_size` includes the template's layer transform,
                # while the setter expects the untransformed point size.
                size = float(layer.textItem.size) * factor
                set_text_size_and_leading(layer, size, size)

        # A smaller font can reflow to fewer lines. Use that free space to grow
        # the text back towards its template size, without exceeding it.
        for _ in range(6):
            static_height, chaos_height = heights()
            required = static_height + chaos_height + (gap if chaos_height else 0)
            if available - required < 4:
                break
            current = {id(layer): float(layer.textItem.size) for layer in layers}
            max_grow = min(
                original_sizes[id(layer)] / current[id(layer)] for layer in layers
            )
            grow = min(1.08, available / required, max_grow)
            if grow <= 1.001:
                break
            for layer in layers:
                size = current[id(layer)] * grow
                set_text_size_and_leading(layer, size, size)
            static_height, chaos_height = heights()
            if static_height + chaos_height + (gap if chaos_height else 0) > available:
                for layer in layers:
                    size = current[id(layer)]
                    set_text_size_and_leading(layer, size, size)
                break

        if chaos and chaos.visible:
            static_height, _ = heights()
            offset = (top + static_height + gap) - chaos.bounds[1]
            chaos.translate(0, offset)
            if symbol := self.text_layer_chaos_symbol:
                symbol.translate(0, offset)

    def paste_scryfall_scan(
        self, rotate: bool = False, visible: bool = False
    ) -> ArtLayer | None:
        """Ensure we rotate the scan for Planar cards."""
        return super().paste_scryfall_scan(rotate=True, visible=visible)
