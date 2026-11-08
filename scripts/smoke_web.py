"""Check both public production site URLs and their deployed API using only stdlib."""

import json
import math
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


SITE_URL = "https://npnkorea.vercel.app/"
OFFICIAL_SITE_URL = "https://www.npnkorea.com/"
OFFICIAL_API_URL = "https://api.npnkorea.com"
ASSETS = {
    "styles.css": {"text/css"},
    "vendor/leaflet/leaflet.css": {"text/css"},
    "vendor/leaflet/leaflet.js": {"application/javascript", "text/javascript"},
    "app.js": {"application/javascript", "text/javascript"},
}
POINT = {"lon": 126.978422, "lat": 37.566742}
EXPECTED_CODE = "다사 5393 5205"
EXPECTED_CORNER = {"lon": 126.97832537074162, "lat": 37.56666295072665}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def request(url, *, method="GET", payload=None, headers=None, media_types=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {"User-Agent": "NPNkorea-production-smoke-test"}
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    request_headers.update(headers or {})
    req = Request(url, data=data, headers=request_headers, method=method)
    with urlopen(req, timeout=15) as response:
        expected_status = 204 if method == "OPTIONS" else 200
        require(response.status == expected_status, f"{url}: HTTP {response.status}")
        # A login redirect must not count as a healthy deployment.
        require(response.geturl() == url, f"{url}: unexpected redirect to {response.geturl()}")
        if media_types:
            media_type = response.headers.get_content_type()
            require(media_type in media_types, f"{url}: unexpected content type {media_type}")
        body = response.read()
        require(method == "OPTIONS" or body, f"{url}: empty response")
        return body, response.headers


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.assets = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "script" and "src" in attrs:
            self.assets.add(attrs["src"])
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.assets.add(attrs.get("href"))
        require(tag != "base", "Unexpected base element changes asset URLs")


def check_page(html):
    require("<title>NPNkorea Map</title>" in html, "Homepage is not the NPNkorea page")
    page = Page()
    page.feed(html)
    require({"map", "command-form", "result-code"} <= page.ids, "Homepage is missing app controls")
    require(set(ASSETS) <= page.assets, "Homepage is missing required asset references")


def default_api_url(app_js):
    match = re.search(r'^const DEFAULT_API_URL = "([^"\n]+)";', app_js, re.MULTILINE)
    require(match is not None, "Cannot find deployed DEFAULT_API_URL in app.js")
    url = match.group(1)
    parsed = urlsplit(url)
    require(
        parsed.scheme == "https" and parsed.hostname and not parsed.username
        and not parsed.password and not parsed.query and not parsed.fragment,
        "Deployed default API must be an HTTPS URL without credentials, query, or fragment",
    )
    return url.rstrip("/")


def check_cors(headers, origin):
    require(
        headers.get("Access-Control-Allow-Origin") in {"*", origin},
        "API response does not allow the production site's origin",
    )


def api_json(api_url, path, *, origin, payload=None):
    body, headers = request(
        api_url + path, method="POST" if payload is not None else "GET",
        payload=payload, headers={"Origin": origin}, media_types={"application/json"},
    )
    check_cors(headers, origin)
    result = json.loads(body)
    require(isinstance(result, dict), f"{path}: expected a JSON object")
    return result


def check_conversion(result):
    require(result.get("code") == EXPECTED_CODE, "Unexpected sample NPN conversion code")
    corner = result.get("cell_corner")
    require(isinstance(corner, dict), "Conversion is missing the cell corner")
    for axis, expected in EXPECTED_CORNER.items():
        value = corner.get(axis)
        require(
            type(value) in (int, float) and math.isclose(value, expected, rel_tol=0, abs_tol=1e-9),
            f"Unexpected converted cell-corner {axis}: {value}",
        )


def check_site(site_url=SITE_URL, *, expected_api_url=None):
    body, _ = request(site_url, media_types={"text/html"})
    check_page(body.decode("utf-8"))
    print(f"PASS homepage: {site_url}", flush=True)
    assets = {}
    for path, media_types in ASSETS.items():
        assets[path], _ = request(urljoin(site_url, path), media_types=media_types)
        print(f"PASS asset: {path}", flush=True)

    api_url = default_api_url(assets["app.js"].decode("utf-8"))
    if expected_api_url is not None:
        require(api_url == expected_api_url, f"Deployed DEFAULT_API_URL must be {expected_api_url}")
    parsed_site = urlsplit(site_url)
    origin = f"{parsed_site.scheme}://{parsed_site.netloc}"
    health = api_json(api_url, "/health", origin=origin)
    require(health.get("status") == "ok", "API health is not ok")
    print(f"PASS API health: {api_url}", flush=True)

    _, headers = request(api_url + "/convert", method="OPTIONS", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    check_cors(headers, origin)
    methods = {value.strip().upper() for value in headers.get("Access-Control-Allow-Methods", "").split(",")}
    allowed_headers = {value.strip().lower() for value in headers.get("Access-Control-Allow-Headers", "").split(",")}
    require("POST" in methods, "CORS preflight does not allow POST")
    require("content-type" in allowed_headers or "*" in allowed_headers, "CORS preflight does not allow Content-Type")
    print(f"PASS API CORS preflight: {origin}", flush=True)

    for payload in ({"point": POINT, "output": "han"}, {"code": EXPECTED_CODE, "output": "han"}):
        check_conversion(api_json(api_url, "/convert", origin=origin, payload=payload))
    print(f"PASS coordinate and code conversion: {EXPECTED_CODE}", flush=True)


def main():
    exit_code = 0
    for site_url, expected_api_url in ((SITE_URL, None), (OFFICIAL_SITE_URL, OFFICIAL_API_URL)):
        try:
            check_site(site_url, expected_api_url=expected_api_url)
        except (OSError, ValueError) as error:
            print(f"FAIL {site_url}: {error}", file=sys.stderr)
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
