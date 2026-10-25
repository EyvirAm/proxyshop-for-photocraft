"""
* Tests: Photocraft Backend Integration
"""
from __future__ import annotations

from pathlib import Path

from src import APP
from src.helpers.colors import get_rgb, get_rgb_from_hex
from src.helpers.document import (
    check_active_document,
    close_document,
    get_layer_tree,
    get_leaf_layers,
    import_art_into_new_layer,
    save_document_jpeg,
    save_document_png,
)
from src.helpers.layers import create_new_layer, getLayer, getLayerSet
from src.utils.adobe import PhotoshopHandler, ReferenceLayer
from src.utils.photocraft import PhotocraftHandler


class TestPhotocraftBackend:
    """End-to-end tests for the Photocraft backend adapter in Proxyshop."""

    def test_handler_initialization(self) -> None:
        handler = PhotoshopHandler()
        assert isinstance(handler, PhotocraftHandler)
        assert handler.has_cli_binary() is True
        assert handler.check_connection() is True
        assert handler.is_running() is True

        # Test direct CLI inspection on showcase.psd
        psd_path = Path("templates/tools/showcase.psd").resolve()
        info = handler.inspect_document(psd_path)
        assert isinstance(info, dict)
        assert info.get("width", 0) > 0 and info.get("height", 0) > 0

    def test_load_psd_and_inspect_hierarchy(self) -> None:
        psd_path = Path("templates/tools/showcase.psd").resolve()
        assert psd_path.exists()

        doc = APP.instance.load(psd_path)
        assert check_active_document() is True
        assert doc.width > 0
        assert doc.height > 0

        tree = get_layer_tree(doc)
        assert isinstance(tree, dict)
        assert len(tree) > 0

        leaves = get_leaf_layers(doc)
        assert len(leaves) > 0

        ref = ReferenceLayer(leaves[0])
        dims = ref.dims
        assert "width" in dims and "height" in dims
        assert "center_x" in dims and "center_y" in dims

        close_document(save=False, docref=doc)

    def test_layer_manipulation_and_export(self, tmp_path: Path) -> None:
        psd_path = Path("templates/tools/showcase.psd").resolve()
        doc = APP.instance.load(psd_path)

        # Create a new layer and edit properties
        layer = create_new_layer("Photocraft Test Layer")
        assert layer.name == "Photocraft Test Layer"
        layer.opacity = 85.0
        assert layer.opacity == 85.0
        layer.visible = False
        assert layer.visible is False
        layer.visible = True

        # Edit text item
        layer.textItem.contents = "Lightning Bolt"
        layer.textItem.size = 24.0
        layer.textItem.color = get_rgb_from_hex("#FF3300")
        assert layer.textItem.contents == "Lightning Bolt"
        assert layer.textItem.color.rgb.red == 255.0

        # Import test artwork into a new layer
        test_art = Path("src/img/test.jpg").resolve()
        art_layer = import_art_into_new_layer(test_art, name="Card Art", docref=doc)
        assert art_layer.name == "Card Art"
        art_layer.translate(10, 20)

        # Export to PNG and JPEG
        out_png = tmp_path / "render_out.png"
        out_jpg = tmp_path / "render_out.jpg"
        save_document_png(out_png, docref=doc)
        save_document_jpeg(out_jpg, docref=doc)

        assert out_png.exists() and out_png.stat().st_size > 0
        assert out_jpg.exists() and out_jpg.stat().st_size > 0

        close_document(save=False, docref=doc)
