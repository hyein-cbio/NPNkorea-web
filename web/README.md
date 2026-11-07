# NPNkorea Web

Static web client for the NPNkorea coordinate conversion API.

## Local development

```bash
python3 -m http.server 3000
```

Open <http://127.0.0.1:3000>.

The API URL can be changed from the settings control in the page. The default
is the deployed AWS API:
`https://or8wc0p8nf.execute-api.eu-west-2.amazonaws.com`.

## Vercel deployment

The production project is `hyein-cbio/npnkorea-web`, connected to the `main`
branch of this repository, at <https://npnkorea.vercel.app/>.

In Vercel Project Settings → Build and Deployment, set **Root Directory to
`web`**. This is a project-level setting, not a `vercel.json` option. Do not
leave it at the repository root: that serves the page at `/web/` instead of
`/`, and incorrectly builds the separate `api/` application as Vercel Functions.

The checked-in `vercel.json` selects the Other framework preset, skips
installation and building, and serves `.` as static output. The API remains
on AWS. Set its URL in the page settings, or update `DEFAULT_API_URL` in
`app.js` before deployment.

Push to `main` to trigger a production deployment. After changing Root
Directory, trigger a new deployment; existing deployments are not rebuilt
automatically when the setting changes.

### Post-deployment checks

A Vercel Ready status does not guarantee that `/` serves the application.
From any directory, check the public URL without Vercel authentication:

```bash
curl --fail --show-error --silent https://npnkorea.vercel.app/
curl --fail --show-error --silent -o /dev/null https://npnkorea.vercel.app/app.js
curl --fail --show-error --silent -o /dev/null https://npnkorea.vercel.app/styles.css
curl --fail --show-error --silent -o /dev/null https://npnkorea.vercel.app/vendor/leaflet/leaflet.js
curl --fail --show-error --silent https://or8wc0p8nf.execute-api.eu-west-2.amazonaws.com/health
```

The first response must be the NPNkorea HTML page, not a login or error page;
the health response must be `{"status":"ok"}`. Also open the site in a browser
and submit `126.978422, 37.566742` to verify the map and coordinate conversion.
