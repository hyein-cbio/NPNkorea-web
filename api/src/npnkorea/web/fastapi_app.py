"""Optional FastAPI application for NPNkorea."""

from typing import Literal

from ..constants import MAX_BATCH_SIZE
from ..core import convert_code, convert_point, to_npn, to_wgs
from ..exceptions import NPNKoreaError
from ..types import LonLat


def create_app():
    """Create a FastAPI app if FastAPI is installed."""

    try:
        from fastapi import FastAPI, HTTPException
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

    class ConvertRequest(BaseModel):
        point: PointModel | None = None
        code: str | None = None
        output: Literal["han", "abc"] = "han"

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

    @app.post("/convert")
    def convert_endpoint(body: ConvertRequest) -> dict[str, object]:
        if (body.point is None) == (body.code is None):
            raise HTTPException(status_code=422, detail="Exactly one of `point` or `code` is required")

        if body.point is not None:
            code, corner = convert_point(
                LonLat(lon=body.point.lon, lat=body.point.lat),
                output=body.output,
            )
        else:
            code, corner = convert_code(body.code, output=body.output)

        return {
            "code": code,
            "cell_corner": {"lon": corner.lon, "lat": corner.lat},
        }

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
