"""Runnable FastAPI entrypoint for NPNkorea."""

from __future__ import annotations

from .fastapi_app import create_app

app = create_app()


def main() -> None:
    """Run the local development API server."""

    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError(
            "Running the API server requires `uvicorn`. Install it with `pip install .[api]`."
        ) from exc

    uvicorn.run("npnkorea.web.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
