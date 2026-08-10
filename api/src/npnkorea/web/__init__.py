"""Web-facing entrypoints for the NPNkorea API."""

from .fastapi_app import create_app

__all__ = ["create_app"]
