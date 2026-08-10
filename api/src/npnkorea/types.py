"""Shared types used by the package."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LonLat:
    """WGS84 longitude/latitude coordinate pair."""

    lon: float
    lat: float


@dataclass(frozen=True)
class ParsedNPN:
    """Parsed NPN components before projection math."""

    x_digit: int
    y_digit: int
    x_pos: int
    y_pos: int
