"""
* Photocraft Compatibility Enumerations (matching photoshop.api.enumerations)
"""
from __future__ import annotations

from enum import IntEnum


class DialogModes(IntEnum):
    """How Photoshop dialogs are displayed while running actions."""

    DisplayAllDialogs = 1
    DisplayErrorDialogs = 2
    DisplayNoDialogs = 3


class Units(IntEnum):
    """Document measurement units."""

    Pixels = 1
    Inches = 2
    CM = 3
    MM = 4
    Points = 5
    Picas = 6
    Percent = 7


class TypeUnits(IntEnum):
    """Units used for text measurements."""

    TypePixels = 1
    TypeMM = 4
    TypePoints = 5


class ElementPlacement(IntEnum):
    """Placement of a layer relative to another element."""

    PlaceInside = 0
    PlaceAtBeginning = 1
    PlaceAtEnd = 2
    PlaceBefore = 3
    PlaceAfter = 4


class AnchorPosition(IntEnum):
    """Anchor point used by transforms and canvas resizes."""

    TopLeft = 1
    TopCenter = 2
    TopRight = 3
    MiddleLeft = 4
    MiddleCenter = 5
    MiddleRight = 6
    BottomLeft = 7
    BottomCenter = 8
    BottomRight = 9


class AutoKernType(IntEnum):
    """Kerning mode applied to text."""

    NoAutoKern = 1
    Metrics = 2
    Optical = 3


class BlendMode(IntEnum):
    """Layer blend modes exposed by Photoshop."""

    PassThrough = 1
    NormalBlend = 2
    Dissolve = 3
    Darken = 4
    Multiply = 5
    ColorBurn = 6
    LinearBurn = 7
    Lighten = 8
    Screen = 9
    ColorDodge = 10
    LinearDodge = 11
    Overlay = 12
    SoftLight = 13
    HardLight = 14
    VividLight = 15
    LinearLight = 16
    PinLight = 17
    HardMix = 18
    Difference = 19
    Exclusion = 20
    Hue = 21
    SaturationBlend = 22
    ColorBlend = 23
    Luminosity = 24
    DarkerColor = 25
    LighterColor = 26
    Subtract = 27
    Divide = 28


class ColorBlendMode(IntEnum):
    """Blend modes specific to fill/stroke operations."""

    NormalBlendColor = 2
    BehindBlend = 29
    ClearBlend = 30


class ColorModel(IntEnum):
    """Color models supported by Photoshop."""

    GrayscaleModel = 1
    RGBModel = 2
    CMYKModel = 3
    LabModel = 4
    HSBModel = 5
    NoColorModel = 50


class DescValueType(IntEnum):
    """Action descriptor value types."""

    IntegerType = 1
    DoubleType = 2
    UnitDouble = 3
    StringType = 4
    BooleanType = 5
    ListType = 6
    ObjectType = 7
    EnumeratedType = 8
    ReferenceType = 9
    ClassType = 10
    AliasType = 11
    RawType = 12
    LargeIntegerType = 13


class FormatOptionsType(IntEnum):
    """JPEG save baseline options."""

    StandardBaseline = 1
    OptimizedBaseline = 2
    Progressive = 3


class Justification(IntEnum):
    """Paragraph alignment options."""

    Left = 1
    Center = 2
    Right = 3
    LeftJustified = 4
    CenterJustified = 5
    RightJustified = 6
    FullyJustified = 7


class Language(IntEnum):
    """Text language used for spelling and hyphenation."""

    EnglishUSA = 1
    EnglishUK = 2


class LayerKind(IntEnum):
    """Kinds of layers supported by Photoshop."""

    NormalLayer = 1
    TextLayer = 2
    grouped = 3
    SmartObjectLayer = 17
    SolidFillLayer = 4
    GradientFillLayer = 5
    PatternFillLayer = 6
    LevelsLayer = 7
    CurvesLayer = 8
    ColorBalanceLayer = 9
    BrightnessContrastLayer = 10
    HueSaturationLayer = 11
    SelectiveColorLayer = 12
    ChannelMixerLayer = 13
    GradientMapLayer = 14
    InversionLayer = 15
    ThresholdLayer = 16
    PosterizeLayer = 18


class PointKind(IntEnum):
    """Path point interpolation kind."""

    SmoothPoint = 1
    CornerPoint = 2


class PurgeTarget(IntEnum):
    """Photoshop caches that can be purged."""

    UndoCaches = 1
    HistoryCaches = 2
    ClipboardCache = 3
    AllCaches = 4


class RasterizeType(IntEnum):
    """What part of a layer gets rasterized."""

    TextContents = 1
    Shape = 2
    FillContent = 3
    LayerClippingPath = 4
    EntireLayer = 5
    LinkedLayers = 6


class SaveOptions(IntEnum):
    """Whether closing a document saves its changes."""

    SaveChanges = 1
    DoNotSaveChanges = 2
    PromptToSaveChanges = 3
