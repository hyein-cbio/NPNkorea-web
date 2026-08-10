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

The API exposes `GET /health`, `POST /to-npn`, and `POST /to-wgs`.

## Web

```bash
cd web
python3 -m http.server 3000
```

For Vercel, set the project Root Directory to `web`. No build command is
required; the static output directory is `.`. Set the deployed API URL in the
page settings or update `DEFAULT_API_URL` in `web/app.js`.
