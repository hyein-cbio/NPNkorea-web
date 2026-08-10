"""Optional FastAPI application for NPNkorea."""

from typing import Literal

from ..constants import MAX_BATCH_SIZE
from ..core import to_npn, to_wgs
from ..exceptions import NPNKoreaError
from ..types import LonLat


def create_app():
    """Create a FastAPI app if FastAPI is installed."""

    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError(
            "FastAPI support requires `fastapi` and `uvicorn`. Install them with `pip install .[api]`."
        ) from exc

    class PointModel(BaseModel):
        lon: float
        lat: float

    class ToNPNRequest(BaseModel):
        points: list[PointModel] = Field(max_length=MAX_BATCH_SIZE)
        output: Literal["han", "abc"] = "han"

    class ToWGSRequest(BaseModel):
        codes: list[str] = Field(max_length=MAX_BATCH_SIZE)

    app = FastAPI(title="NPNkorea API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        # Keep browser access local-only by default while allowing common dev ports.
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/to-npn")
    def to_npn_endpoint(body: ToNPNRequest) -> dict[str, list[str]]:
        points = [LonLat(lon=point.lon, lat=point.lat) for point in body.points]
        results = to_npn(points, output=body.output)
        if isinstance(results, str):
            return {"results": [results]}
        return {"results": results}

    @app.post("/to-wgs")
    def to_wgs_endpoint(body: ToWGSRequest) -> dict[str, list[dict[str, float]]]:
        results = to_wgs(body.codes)
        points = [results] if isinstance(results, LonLat) else results
        return {"results": [{"lon": point.lon, "lat": point.lat} for point in points]}

    @app.exception_handler(NPNKoreaError)
    async def npnkorea_error_handler(_, exc: NPNKoreaError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    return app
