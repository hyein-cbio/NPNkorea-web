# NPNkorea

Convert between Korea's National Point Numbers (NPN, 국가지점번호) and WGS84
longitude/latitude coordinates.

## Use the service

- **Web demo:** <https://npnkorea.vercel.app/>
- **Public HTTP API base URL:** <https://api.npnkorea.com>
- **[API usage documentation](api/README.md#public-http-api):** endpoints, runnable
  curl examples, input/output rules, errors, and operating limitations
- **Related R package (separate repository):** <https://github.com/hyein-cbio/NPNkorea>

The public API currently accepts requests without an API key or authentication.
For example:

```bash
curl --fail --show-error --silent \
  https://api.npnkorea.com/health
```

Response: `{"status":"ok"}`. See the API documentation for conversion examples;
public access is not a promise of unlimited use or an SLA.

## Architecture and repository layout

```text
Browser → Vercel static web client → AWS API Gateway HTTP API
                                  → AWS Lambda (Python, eu-west-2)
```

- [`api/`](api/) — Python conversion package, production Lambda handler, AWS SAM
  template, optional local FastAPI server, and API tests. Production endpoints
  are `GET /health`, `POST /convert`, `POST /to-npn`, and `POST /to-wgs`.
- [`web/`](web/) — static browser client. It uses `/convert` to retrieve a code
  and its grid-cell corner in one request. Vercel serves the client, not the API.
- [`scripts/`](scripts/) — production HTTP smoke test and its unit tests.

The API and web client can be developed and deployed independently. See
[`api/README.md`](api/README.md#python-package-and-local-development) for Python,
local server, tests, and Lambda deployment instructions, and
[`web/README.md`](web/README.md) for local web development and Vercel settings.
For Vercel, the project Root Directory must be `web`, not the repository root.
