# NPNkorea Web

Static web client for the NPNkorea coordinate conversion API.

## Local development

```bash
python3 -m http.server 3000
```

Open <http://127.0.0.1:3000>.

The API URL can be changed from the settings control in the page. The default
is `http://127.0.0.1:8000`.

## Vercel deployment

Import this repository into Vercel as a static site. No build command is
required and the output directory is `.`. Set the production API URL in the
page settings, or update `DEFAULT_API_URL` in `app.js` before deployment.
