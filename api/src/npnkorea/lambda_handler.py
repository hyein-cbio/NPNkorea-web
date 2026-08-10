"""AWS Lambda handler for the HTTP API (API Gateway HTTP API payload v2)."""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from .constants import MAX_BATCH_SIZE
from .core import to_npn, to_wgs
from .exceptions import NPNKoreaError
from .types import LonLat


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json",
            "access-control-allow-origin": "*",
        },
        "body": json.dumps(body, ensure_ascii=False, separators=(",", ":")),
    }


def _request_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if body is None:
        return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body, validate=True).decode("utf-8")
    if isinstance(body, dict):  # useful for direct Lambda invocation
        return body
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("JSON body must be an object")
    return parsed


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle /health, /to-npn, and /to-wgs requests."""
    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})
    method = event.get("httpMethod") or http.get("method", "GET")
    path = event.get("rawPath") or event.get("path", "/")

    if method == "OPTIONS":
        return _response(204, {})
    if method == "GET" and path.endswith("/health"):
        return _response(200, {"status": "ok"})
    if method != "POST":
        return _response(404, {"detail": "Not found"})

    try:
        body = _request_body(event)
        if path.endswith("/to-npn"):
            raw_points = body["points"]
            if not isinstance(raw_points, list):
                raise ValueError("`points` must be a JSON array")
            if len(raw_points) > MAX_BATCH_SIZE:
                return _response(413, {"detail": f"`points` cannot contain more than {MAX_BATCH_SIZE} items."})
            points = [LonLat(lon=float(p["lon"]), lat=float(p["lat"])) for p in raw_points]
            results = to_npn(points, output=body.get("output", "han"))
            return _response(200, {"results": [results] if isinstance(results, str) else results})

        if path.endswith("/to-wgs"):
            codes = body["codes"]
            if not isinstance(codes, list):
                raise ValueError("`codes` must be a JSON array")
            if len(codes) > MAX_BATCH_SIZE:
                return _response(413, {"detail": f"`codes` cannot contain more than {MAX_BATCH_SIZE} items."})
            results = to_wgs(codes)
            points = [results] if isinstance(results, LonLat) else results
            return _response(200, {"results": [{"lon": p.lon, "lat": p.lat} for p in points]})

        return _response(404, {"detail": "Not found"})
    except NPNKoreaError as exc:
        return _response(422, {"detail": str(exc)})
    except (binascii.Error, KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
        return _response(400, {"detail": f"Invalid request: {exc}"})
