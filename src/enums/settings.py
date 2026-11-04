"""
* Enums: Settings
"""
from __future__ import annotations

from enum import StrEnum

"""
* App Settings
"""


class OutputFileType(StrEnum):
    """``OutputFileType`` options."""
    JPG = "jpg"
    PNG = "png"
    PSD = "psd"


class ScryfallSorting(StrEnum):
    """``ScryfallSorting`` options."""
    Released = "released"
    Set = "set"
    Rarity = "rarity"
    USD = "usd"
    EUR = "eur"
    EDHRec = "edhrec"
    Artist = "artist"


class ScryfallUnique(StrEnum):
    """``ScryfallUnique`` options."""
    Prints = "prints"
    Arts = "arts"


"""
* Base Settings
"""


class CollectorMode(StrEnum):
    """``CollectorMode`` options."""
    Normal = "default"
    Modern = "modern"
    Minimal = "minimal"
    ArtistOnly = "artist"
    Custom = "custom"


class BorderColor(StrEnum):
    """``BorderColor`` options."""
    Black = "black"
    White = "white"
    Silver = "silver"
    Gold = "gold"


class CollectorPromo(StrEnum):
    """``CollectorPromo`` options."""
    Automatic = "automatic"
    Always = "always"
    Never = "never"


class WatermarkMode(StrEnum):
    """``WatermarkMode`` options."""
    Disabled = "Disabled"
    Automatic = "Automatic"
    Fallback = "Fallback"
    Forced = "Forced"


class FillMode(StrEnum):
    """``FillMode`` options."""
    NO_FILL = "No Fill"
    CONTENT_AWARE_FILL = "Content-Aware Fill"
    GENERATIVE_FILL = "Generative Fill"
    REMOVE_CONTENT_FILL = "Remove Content Fill"


class NicknameShorten(StrEnum):
    """``NicknameShorten`` options."""
    NO = "No"
    ALL_BUT_FIRST = "All but first"
    ALL = "All"


"""
* Template: Borderless
"""


class BorderlessColorMode(StrEnum):
    """``BorderlessColorMode`` options."""
    All = "All"
    Twins_And_PT = "Twins and PT"
    Textbox = "Textbox"
    Twins = "Twins"
    PT = "PT Box"
    Disabled = "None"


class BorderlessTextbox(StrEnum):
    """``BorderlessTextbox`` options."""
    Automatic = "Automatic"
    Textless = "Textless"
    Normal = "Normal"
    Medium = "Medium"
    Short = "Short"
    Tall = "Tall"


"""
* Template: Modern Classic
"""


class ModernClassicCrown(StrEnum):
    """``ModernClassicCrown`` options."""
    Pinlines = "Pinlines"
    TexturePinlines = "Texture Pinlines"
    TextureBackground = "Texture Background"
