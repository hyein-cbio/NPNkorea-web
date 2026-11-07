# NPNkorea

NPN coordinate conversion service and web client.

## Repository layout

- [`api/`](api/) — Python package, FastAPI local API, and AWS Lambda/SAM deployment
- [`web/`](web/) — static browser client for Vercel

The API and web client are separate applications in one monorepo. They can be
developed and deployed independently.

## API

```bash
cd api
pixi run -m ~/pixi/work0/pixi.toml python -m pytest -q
sam build --use-container
sam deploy --guided
```

The API exposes `GET /health`, `POST /convert`, `POST /to-npn`, and `POST /to-wgs`. The web client uses `/convert` to complete each interaction in one request.

## Web

```bash
cd web
python3 -m http.server 3000
```

For Vercel, set the project **Root Directory to `web`** (not the repository
root). [`web/vercel.json`](web/vercel.json) configures a static deployment with
no install or build step and output directory `.`. The API stays on AWS; it
should not be built as Vercel Functions.

See [`web/README.md`](web/README.md#vercel-deployment) for deployment settings
and post-deployment checks. Set the deployed API URL in the page settings or
update `DEFAULT_API_URL` in `web/app.js`.
