"""Core conversion helpers for NPNkorea."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from functools import lru_cache

from .constants import (
    ABC_CODES_SORTED,
    ABC_TO_DIGIT,
    DIGIT_TO_ABC,
    DIGIT_TO_HAN,
    HAN_TO_DIGIT,
    VALID_DIGITS,
)
from .exceptions import NPNKoreaError
from .types import LonLat, ParsedNPN

PointBatch = LonLat | Sequence[LonLat]
StringBatch = str | Sequence[str]

_HANGUL_PATTERN = re.compile(r"^([가-힣])([가-힣])(\d{4})(\d{4})$")
_ABC_PATTERN = re.compile(
    r"^({})({})(\d{{4}})(\d{{4}})$".format(
        "|".join(ABC_CODES_SORTED),
        "|".join(ABC_CODES_SORTED),
    ),
    re.IGNORECASE,
)


def to_wgs(values: StringBatch) -> LonLat | list[LonLat]:
    """Convert one or many NPN strings to WGS84 coordinates."""

    items, single = _normalize_strings(values)
    if not items:
        return []

    transformer = _get_transformer(5179, 4326)
    output: list[LonLat] = []

    for item in items:
        parsed = _parse_npn_string(item)
        # NPN stores a 100 km band pair plus 10 m offsets within that band.
        x = (parsed.x_digit - 1) * 100_000 + 10 * parsed.x_pos
        y = (parsed.y_digit - 1) * 100_000 + 10 * parsed.y_pos
        # Convert from internal NPN offsets into EPSG:5179 projected coordinates.
        x = x + 1_000_000 - 300_000
        y = y + 2_000_000 - 700_000
        lon, lat = transformer.transform(x, y)
        point = LonLat(lon=lon, lat=lat)
        try:
            _validate_lonlat(point)
        except NPNKoreaError as exc:
            raise NPNKoreaError(
                "`values` contains an NPN code outside the supported Korea bounds."
            ) from exc
        output.append(point)

    return output[0] if single else output


def to_npn(points: PointBatch, output: str = "han") -> str | list[str]:
    """Convert one or many WGS84 coordinate pairs to NPN strings."""

    if output not in {"han", "abc"}:
        raise NPNKoreaError("`output` must be either 'han' or 'abc'.")

    items, single = _normalize_points(points)
    if not items:
        return "" if single else []

    transformer = _get_transformer(4326, 5179)
    lookup = DIGIT_TO_HAN if output == "han" else DIGIT_TO_ABC
    results: list[str] = []

    for point in items:
        _validate_lonlat(point)
        x, y = transformer.transform(point.lon, point.lat)
        x = round(x - 1_000_000 + 300_000, 6)
        y = round(y - 2_000_000 + 700_000, 6)

        x_digit = math.floor(x / 100_000) + 1
        y_digit = math.floor(y / 100_000) + 1
        if x_digit not in VALID_DIGITS or y_digit not in VALID_DIGITS:
            raise NPNKoreaError(
                "`points` contains coordinates outside the supported NPN grid after projection."
            )

        x_pos = math.floor((x % 100_000) / 10)
        y_pos = math.floor((y % 100_000) / 10)
        if not (0 <= x_pos <= 9_999 and 0 <= y_pos <= 9_999):
            raise NPNKoreaError(
                "`points` contains coordinates outside the supported NPN grid after projection."
            )

        results.append(f"{lookup[x_digit]}{lookup[y_digit]} {x_pos:04d} {y_pos:04d}")

    return results[0] if single else results


def _normalize_strings(values: StringBatch) -> tuple[list[str], bool]:
    if isinstance(values, str):
        return [values], True

    if values is None:
        raise NPNKoreaError("`values` must be a string or a sequence of strings.")

    try:
        items = list(values)
    except TypeError as exc:
        raise NPNKoreaError("`values` must be a string or a sequence of strings.") from exc

    if any(not isinstance(item, str) for item in items):
        raise NPNKoreaError("`values` must contain only strings.")

    return items, False


def _normalize_points(points: PointBatch) -> tuple[list[LonLat], bool]:
    if isinstance(points, LonLat):
        return [points], True

    if points is None:
        raise NPNKoreaError("`points` must be a LonLat or a sequence of LonLat values.")

    if not isinstance(points, Sequence) or isinstance(points, (str, bytes)):
        raise NPNKoreaError("`points` must be a LonLat or a sequence of LonLat values.")

    if any(not isinstance(item, LonLat) for item in points):
        raise NPNKoreaError("Batch inputs must contain only LonLat values.")

    items = list(points)

    return items, False


def _validate_lonlat(point: LonLat) -> None:
    if not math.isfinite(point.lon) or not math.isfinite(point.lat):
        raise NPNKoreaError("`lon` and `lat` must be finite.")

    # This package intentionally targets Korea's NPN coverage, not global WGS84.
    if point.lon <= 124 or point.lon >= 133:
        raise NPNKoreaError("`lon` must be between 124 and 133.")

    if point.lat <= 32 or point.lat >= 39:
        raise NPNKoreaError("`lat` must be between 32 and 39.")


def _parse_npn_string(value: str) -> ParsedNPN:
    compact = re.sub(r"\s+", "", value.strip())
    if not compact:
        raise NPNKoreaError(
            "`values` entries must be valid NPN strings like '다사 5396 5207' or 'DaSa53965207'."
        )

    if re.search(r"[가-힣]", compact):
        match = _HANGUL_PATTERN.fullmatch(compact)
        if not match:
            raise NPNKoreaError(
                "`values` entries must be valid NPN strings like '다사 5396 5207' or 'DaSa53965207'."
            )
        x_digit = HAN_TO_DIGIT.get(match.group(1))
        y_digit = HAN_TO_DIGIT.get(match.group(2))
    else:
        upper = compact.upper()
        match = _ABC_PATTERN.fullmatch(upper)
        if not match:
            raise NPNKoreaError(
                "`values` entries must be valid NPN strings like '다사 5396 5207' or 'DaSa53965207'."
            )
        x_digit = ABC_TO_DIGIT.get(match.group(1).upper())
        y_digit = ABC_TO_DIGIT.get(match.group(2).upper())

    if x_digit is None or y_digit is None:
        raise NPNKoreaError("`values` entries must use valid NPN letter pairs.")

    return ParsedNPN(
        x_digit=x_digit,
        y_digit=y_digit,
        x_pos=int(match.group(3)),
        y_pos=int(match.group(4)),
    )


@lru_cache(maxsize=2)
def _get_transformer(source_epsg: int, target_epsg: int):
    try:
        from pyproj import Transformer
    except ImportError as exc:
        raise RuntimeError(
            "pyproj is required for CRS transformation. Install it with `python -m pip install pyproj`."
        ) from exc

    return Transformer.from_crs(
        f"EPSG:{source_epsg}",
        f"EPSG:{target_epsg}",
        always_xy=True,
    )
