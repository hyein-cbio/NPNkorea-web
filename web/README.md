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
The **Production smoke test** GitHub Actions workflow
([`.github/workflows/production-smoke.yml`](../.github/workflows/production-smoke.yml))
has only two triggers:

- `deployment_status`: the test job runs only when `state` is `success` and
  the deployment environment is exactly `Production`.
- `workflow_dispatch`: run it manually from Actions → Production smoke test →
  Run workflow, or `gh workflow run production-smoke.yml --ref main`.

There are no push, pull-request, or scheduled triggers. Preview and failed
or pending deployments do not run the test job. GitHub may still show a
skipped workflow run for those status events.

The trigger does not distinguish automatic from manual deployments: both
qualify **if they publish the matching GitHub deployment status**. A CLI or
dashboard deployment, promotion, or rollback that does not publish that event
cannot trigger this workflow; use the manual trigger in that case. This is
not a polling monitor and it does not automatically roll back a failed check.

The checks always target the public production alias
`https://npnkorea.vercel.app/`, not the event's potentially protected deployment
URL. Thus they test what users can access without a Vercel login or bypass
secret. If deployments overlap, the alias may already point at a newer
release; this is a live production check, not a per-deployment certification.
The event's commit and deployment URL are logged for context. Test tooling is
checked out from the default branch, rather than executing an arbitrary
deployment ref.

The Python standard-library smoke test checks the page identity and controls,
required JS/CSS responses and content types, the default API configured in the
**deployed** `app.js`, API health, CORS preflight, and coordinate/code conversion.
It is an HTTP smoke test, not a browser rendering or JavaScript execution test.
No additional secrets or Python packages are required. Run the same checks
locally from the repository root:

```bash
python3 -B -m unittest discover -s scripts/tests -v
python3 -B scripts/smoke_web.py
```

For a quick manual check from any directory, use:

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
