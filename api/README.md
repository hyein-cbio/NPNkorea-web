# NPNkorea API

Public HTTP service and Python package for converting between Korea's National
Point Numbers (NPN, 국가지점번호) and WGS84 longitude/latitude coordinates.

## Public HTTP API

**Base URL:** `https://api.npnkorea.com`

This is the callable production URL, served by API Gateway HTTP API and a Python
Lambda in AWS `eu-west-2`. The [web demo](https://www.npnkorea.com/) is a
separate static client hosted on Vercel. No Python or R installation is needed
to call the HTTP API. For the separate R package, see
[hyein-cbio/NPNkorea](https://github.com/hyein-cbio/NPNkorea).

### Access and operating limitations

- Requests currently require **no API key, token, or authentication**. Send POST
  bodies as JSON objects with `Content-Type: application/json`.
- Production CORS allows any origin (`Access-Control-Allow-Origin: *`). The SAM
  template allows `GET`, `POST`, and `OPTIONS`, with the `content-type` request
  header. This is distinct from the local FastAPI CORS policy described below.
- The application limit is **1,000 items per batch request**, not a request-rate
  allowance. No requests-per-second quota, unlimited-use commitment, or SLA is
  specified here. Deployment-level throttling, availability, pricing/use terms,
  and logging/retention policies need confirmation with the maintainer. Do not
  infer privacy guarantees from unauthenticated access; avoid sending sensitive
  location data until those policies are confirmed.
- Production uses the Lambda handler, **not FastAPI**. It does not expose Swagger
  UI or an OpenAPI document: production `/docs` and `/openapi.json` return 404.
  This README is the public usage reference.

### Endpoints

All successful responses below have HTTP status 200 and JSON bodies.

| Method | Path | Request | Response / purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | No body | `{"status":"ok"}`; basic service health |
| `POST` | `/convert` | Exactly one of `point` or `code`; optional `output` | One canonical `code` and its `cell_corner` |
| `POST` | `/to-npn` | `points` array; optional `output` | `results` array of NPN strings |
| `POST` | `/to-wgs` | `codes` array | `results` array of WGS84 grid-cell corners |

### Quick start: health

```bash
curl --fail --show-error --silent \
  https://api.npnkorea.com/health
```

```json
{"status":"ok"}
```

### Convert one coordinate to a code and cell corner

For Seoul City Hall, supply longitude as `lon` and latitude as `lat`:

```bash
curl --fail --show-error --silent \
  https://api.npnkorea.com/convert \
  -H 'Content-Type: application/json' \
  -d '{"point":{"lon":126.978422,"lat":37.566742}}'
```

```json
{
  "code": "다사 5393 5205",
  "cell_corner": {
    "lon": 126.97832537074162,
    "lat": 37.56666295072666
  }
}
```

### Convert one code to a canonical code and cell corner

`/convert` also accepts an NPN string. Input spacing and romanization are
normalized; the default output is Hangul, even for romanized input.

```bash
curl --fail --show-error --silent \
  https://api.npnkorea.com/convert \
  -H 'Content-Type: application/json' \
  -d '{"code":"dasa53935205"}'
```

```json
{
  "code": "다사 5393 5205",
  "cell_corner": {
    "lon": 126.97832537074162,
    "lat": 37.56666295072666
  }
}
```

For `/convert`, supply **exactly one non-null input**: `point` (a JSON object
with `lon` and `lat`) or `code` (a string). Omit the other field. Supplying both,
neither, or only null values is invalid. This endpoint does not accept arrays.

On `/convert` and `/to-npn`, `output` is optional and defaults to `"han"`:

- `"han"` → Hangul, e.g. `다사 5393 5205`
- `"abc"` → romanized, e.g. `DaSa 5393 5205`

These are the only supported values and are case-sensitive. `output` controls
code formatting, not the coordinate reference system or cell-corner position.
`/to-wgs` has no output-format option; its results are always WGS84 coordinates.

### Batch coordinates to NPN

Even a single item must be inside the `points` array. This example requests
romanized codes for Seoul and Busan:

```bash
curl --fail --show-error --silent \
  https://api.npnkorea.com/to-npn \
  -H 'Content-Type: application/json' \
  -d '{"points":[{"lon":126.978422,"lat":37.566742},{"lon":129.075642,"lat":35.179554}],"output":"abc"}'
```

```json
{"results":["DaSa 5393 5205","MaRa 4347 8827"]}
```

### Batch NPN to coordinates

Supply a `codes` array, not a bare string or top-level array. Hangul and
romanized forms may be mixed:

```bash
curl --fail --show-error --silent \
  https://api.npnkorea.com/to-wgs \
  -H 'Content-Type: application/json' \
  -d '{"codes":["다사53935205","MaRa43478827"]}'
```

```json
{
  "results": [
    {"lon":126.97832537074162,"lat":37.56666295072666},
    {"lon":129.0756266828708,"lat":35.17949162224057}
  ]
}
```

For both batch endpoints:

- The array can contain **0–1,000 items**, inclusive. An empty array returns
  `{"results":[]}`; larger arrays are rejected (413 in production).
- Results retain input order and are always arrays, including for one item.
- If any item is invalid, the whole request fails; there are no partial results
  or per-item error entries. Split larger inputs into batches of at most 1,000.

### Coordinate and NPN rules

**Coordinates:** WGS84 (`EPSG:4326`), decimal degrees. Use named fields in
**longitude, latitude** order: `{"lon":126.978422,"lat":37.566742}`. Positional
arrays such as `[lat, lon]` or `[lon, lat]` are not the HTTP input format. Use
finite JSON numbers satisfying the strict bounds:

- `124 < lon < 133`
- `32 < lat < 39`

Boundary values are excluded. These are Korea-specific validation bounds, not
a geographic coverage guarantee: a point inside them can still fall outside
the supported NPN grid after projection and be rejected. NPN-to-coordinate
conversion also rejects codes whose decoded corner falls outside these bounds.

**NPN strings:** two supported band letters followed by exactly four easting
digits and four northing digits (keep leading zeros). Whitespace is ignored;
romanized letters are case-insensitive. Examples for the same cell:

- `다사 5393 5205`
- `다사53935205`
- `DaSa 5393 5205`
- `dasa53935205`

The supported letter mapping is `가/Ga`, `나/Na`, `다/Da`, `라/Ra`, `마/Ma`,
`바/Ba`, `사/Sa`, `아/A`, `자/Ja`, `차/Cha`, `카/Ka`, `타/Ta`, `파/Pa`,
`하/Ha`. Arbitrary abbreviations such as `DS`, mixed Hangul/romanized band
pairs, and codes with fewer or more digits are not supported. A syntactically
valid code must also pass the decoded-coordinate bounds check.

**10 m cells, not exact original points:** the implementation projects to
Korea Unified CS (`EPSG:5179`), assigns two 100 km band letters, and floors the
within-band easting and northing to 10 m offsets. Each code identifies a
**10 m × 10 m projected grid cell**. `cell_corner` from `/convert`, and each
coordinate from `/to-wgs`, is the WGS84 transformation of that cell's
**lower-left corner in projected coordinates** (minimum easting and northing).
It is not the cell center, the original submitted point, or necessarily the
minimum longitude and latitude of all transformed cell corners. Thus a round
trip does not recover the original coordinate; 10 m is the grid resolution,
not a guarantee of positional accuracy. Final floating-point digits may vary
slightly with the projection library/runtime.

### Errors (production Lambda)

Handled application errors return a JSON object with a string `detail`:

| HTTP status | Causes in the Lambda handler |
| --- | --- |
| `400` | Malformed JSON or a non-object body; missing required fields; wrong container types; coordinates that cannot be converted to numbers; `/convert` with both or neither input |
| `413` | More than 1,000 entries in `points` or `codes` |
| `422` | Conversion/domain validation: out-of-range or non-finite coordinates, projected grid outside support, invalid NPN strings or decoded bounds, unsupported `output` |
| `404` | Unhandled route/method; API Gateway may reject it before Lambda |

For example, `POST /convert` with `{}` returns 400:

```json
{"detail":"Invalid request: Exactly one of `point` or `code` is required"}
```

`POST /to-npn` with `{"points":[{"lon":140,"lat":37}]}` returns 422:

```json
{"detail":"`lon` must be between 124 and 133."}
```

An oversized `codes` array returns 413:

```json
{"detail":"`codes` cannot contain more than 1000 items."}
```

Gateway/infrastructure errors are not guaranteed to use this `detail` shape.
For example, production `/docs` returns 404 with `{"message":"Not Found"}`.
Clients should check the HTTP status before reading success fields and handle
non-JSON or differently shaped error responses too. The table describes
application validation, not all possible upstream errors or service quotas.

## Python package and local development

The implemented Python package lives in `src/npnkorea/` and requires Python
3.10+ with `pyproj>=3.7` for CRS transformations. It is a Python sibling of the
[separate R package](https://github.com/hyein-cbio/NPNkorea), not a requirement
for HTTP clients.

From the repository root, create an environment and install the package with
local API and test dependencies:

```bash
cd api
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[api,dev]'
python -m pytest -q
```

To use only the conversion package, install with `python -m pip install -e .`
instead. From an installed environment:

```python
from npnkorea import LonLat, to_npn, to_wgs

code = to_npn(LonLat(lon=126.978422, lat=37.566742))
# "다사 5393 5205"
codes = to_npn([LonLat(lon=126.978422, lat=37.566742)], output="abc")
# ["DaSa 5393 5205"]
point = to_wgs("다사 5393 5205")
# LonLat representing the grid-cell corner, not the original point
```

`to_npn()` accepts one `LonLat` or a sequence of `LonLat` values; `to_wgs()`
accepts one string or a sequence of strings. Single inputs return a single
result; sequence inputs return lists. Invalid conversion inputs raise
`NPNKoreaError`. The 1,000-item cap is enforced by the HTTP adapters, not the
core Python functions. The same coordinate, code, and cell-corner rules apply.

### Local FastAPI server (not production Lambda)

With the `api` extra installed, run either command:

```bash
npnkorea-api
# Alternative:
python -m npnkorea.web.main
```

The server binds to `http://127.0.0.1:8000`. The factory is
`npnkorea.web.fastapi_app:create_app`. The four conversion/health routes use
the same core functions as Lambda. For local requests, replace the production
base URL in the curl examples with `http://127.0.0.1:8000`.

Local-only differences:

- Interactive docs: <http://127.0.0.1:8000/docs>; schema:
  <http://127.0.0.1:8000/openapi.json>. Neither is a production Lambda route.
- CORS allows only HTTP/HTTPS origins on `localhost` or `127.0.0.1`, with optional
  ports. Allowed methods are `GET`, `POST`, and `OPTIONS`; request headers are
  unrestricted. This does not describe production's wildcard-origin policy.
- FastAPI/Pydantic schema validation generally returns 422 with a structured
  `detail` array (for example, missing fields, malformed bodies, or oversized
  batches). Both/neither `/convert` inputs return 422 with a string `detail`,
  rather than Lambda's 400. Core conversion errors return 422 with a string
  `detail` in both adapters. Do not assume identical error status/shape across
  local and production servers.

### AWS Lambda deployment (maintainers)

[`template.yaml`](template.yaml) defines API Gateway HTTP API routes, production
CORS, and the Lambda using `npnkorea.lambda_handler.handler` with API Gateway
payload v2. The checked-in template specifies Python 3.12, 256 MB memory, and a
10-second timeout; these are template settings, not an availability or latency
promise. [`src/requirements.txt`](src/requirements.txt) supplies the Lambda
runtime dependency.

From `api/`, with AWS SAM CLI, Docker, and appropriate AWS credentials already
configured, build in a container to package `pyproj` for Lambda, then deploy:

```bash
sam build --use-container
sam deploy --guided --region eu-west-2
```

These commands create/update AWS resources; they are not needed to use the
public service. Use the stack's `ApiUrl` output as the base URL for your own
deployment, not an AWS console URL. The frontend is deployed separately; see
[`../web/README.md`](../web/README.md#vercel-deployment). No deployment is needed
for documentation-only edits.
