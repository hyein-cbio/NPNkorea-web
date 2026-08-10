# NPNkorea Python

Python 3.10+ package skeleton for converting between Korea's National Point
Numbers (NPN) and WGS84 longitude/latitude coordinates.

## Scope

This repository is a fresh Python sibling to the existing R package. The goal
of this skeleton is to provide:

- modern Python packaging via `pyproject.toml`
- a `src/` layout
- a minimal runtime dependency on `pyproj`
- a public API shaped around `to_npn()` and `to_wgs()`
- a starting test suite that mirrors the R package behavior

## Proposed public API

```python
from npnkorea import LonLat, to_npn, to_wgs

code = to_npn(LonLat(lon=126.978422, lat=37.566742))
codes = to_npn([LonLat(lon=126.978422, lat=37.566742)])
point = to_wgs("다사 5396 5207")
```

## Input and Output Contract

`to_npn()` accepts:
- one `LonLat`
- a sequence of `LonLat` values

`to_wgs()` accepts:
- one NPN string
- a batch of NPN strings

Return values:
- single input returns a single result
- batch input returns a list of results

Domain rules:
- `to_npn()` is intentionally Korea-specific
- longitude must satisfy `124 < lon < 133`
- latitude must satisfy `32 < lat < 39`
- coordinates that pass those heuristics but still fall outside the supported NPN grid are rejected with an explicit error

Accepted NPN forms:
- Hangul: `"다사 5396 5207"`
- compact Hangul: `"다사53965207"`
- romanized: `"DaSa 5396 5207"`
- compact romanized: `"dasa53965207"`

## API Surface

The web API is intentionally batch-oriented:

- `GET /health`
- `POST /to-npn`
- `POST /to-wgs`

The FastAPI app can be created from `npnkorea.web.fastapi_app:create_app`
after installing the `api` extra.

## Run the API

Once `fastapi` and `uvicorn` are installed, you can run the local API server:

```bash
pixi run -m ~/pixi/work0/pixi.toml python -m npnkorea.web.main
```

or, after package installation:

```bash
npnkorea-api
```

## Local browser access

The FastAPI app includes a minimal CORS policy for local development. Browser
requests are allowed only from:

- `http://localhost:<port>`
- `http://127.0.0.1:<port>`

This is meant to support a frontend developer running a local JavaScript dev
server without opening the API to arbitrary remote origins.

## API Examples

Convert WGS84 coordinates to NPN:

```bash
curl -X POST http://127.0.0.1:8000/to-npn \
  -H 'Content-Type: application/json' \
  -d '{
    "points": [
      { "lon": 126.978422, "lat": 37.566742 }
    ],
    "output": "han"
  }'
```

Expected JSON response:

```json
{
  "results": ["다사 5393 5205"]
}
```

Convert NPN strings to WGS84 coordinates:

```bash
curl -X POST http://127.0.0.1:8000/to-wgs \
  -H 'Content-Type: application/json' \
  -d '{
    "codes": ["다사 5396 5207", "MaRa43478827"]
  }'
```

Expected JSON response:

```json
{
  "results": [
    { "lon": 126.97866380715097, "lat": 37.56684471509263 },
    { "lon": 129.0756266828708, "lat": 35.17949162224057 }
  ]
}
```

## AWS Lambda deployment

`template.yaml` defines the minimal API Gateway HTTP API and Lambda
implementation. Build with Docker so `pyproj` is packaged for Lambda:

```bash
sam build --use-container
sam deploy --guided
```

The deployed API exposes `/health`, `/to-npn`, and `/to-wgs`. Delete the stack
when it is no longer needed with `sam delete`.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
pytest
```

## Notes

- The package metadata requires Python 3.10 or newer.
- The code is intentionally lightweight and depends on `pyproj` for CRS
  transformation instead of heavier geospatial stacks.
