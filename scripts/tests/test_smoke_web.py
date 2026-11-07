import contextlib
import io
import json
import unittest
from email.message import Message
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import smoke_web as smoke


ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / "web/index.html").read_text()
APP_JS = (ROOT / "web/app.js").read_bytes()
API_URL = smoke.default_api_url(APP_JS.decode())
CONVERSION = {"code": smoke.EXPECTED_CODE, "cell_corner": smoke.EXPECTED_CORNER}


def headers(content_type="application/json", **extra):
    result = Message()
    result["Content-Type"] = content_type
    result["Access-Control-Allow-Origin"] = "*"
    for key, value in extra.items():
        if key in result:
            result.replace_header(key, value)
        else:
            result[key] = value
    return result


class Response:
    def __init__(self, url, body, response_headers, status=200):
        self.url = url
        self.body = body
        self.headers = response_headers
        self.status = status

    def geturl(self):
        return self.url

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class PageTests(unittest.TestCase):
    def test_current_page(self):
        smoke.check_page(HTML)

    def test_login_error_missing_controls_assets_and_base_are_rejected(self):
        pages = [
            "<title>Login</title>",
            "NOT_FOUND",
            HTML.replace('id="map"', 'id="missing-map"'),
            HTML.replace('src="app.js"', 'src="missing.js"'),
            HTML.replace("<head>", '<head><base href="/web/">'),
        ]
        for page in pages:
            with self.subTest(page=page[:70]), self.assertRaises(ValueError):
                smoke.check_page(page)

    def test_public_api_defaults_use_custom_domain(self):
        self.assertEqual(API_URL, "https://api.npnkorea.com")
        input_values = []

        class APIInputParser(HTMLParser):
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "input" and attrs.get("id") == "base-url":
                    input_values.append(attrs.get("value"))

        APIInputParser().feed(HTML)
        self.assertEqual(input_values, [API_URL])

    def test_deployed_api_url(self):
        self.assertEqual(smoke.default_api_url(APP_JS.decode()), API_URL)
        for value in ("", 'const DEFAULT_API_URL = "http://example.com";',
                      'const DEFAULT_API_URL = "https://user:secret@example.com";',
                      'const DEFAULT_API_URL = "https://example.com?token=x";'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                smoke.default_api_url(value)

    def test_conversion_validation(self):
        smoke.check_conversion(CONVERSION)
        for result in ({}, {"code": "wrong"}, {"code": smoke.EXPECTED_CODE},
                       {"code": smoke.EXPECTED_CODE, "cell_corner": {"lon": float("nan"), "lat": True}}):
            with self.subTest(result=result), self.assertRaises(ValueError):
                smoke.check_conversion(result)


class RequestTests(unittest.TestCase):
    def test_redirect_wrong_type_empty_body_and_wrong_status_fail(self):
        url = smoke.SITE_URL
        responses = [
            Response("https://vercel.com/login", b"login", headers("text/html")),
            Response(url, b"NOT_FOUND", headers("text/plain")),
            Response(url, b"", headers("text/html")),
            Response(url, b"error", headers("text/html"), status=503),
        ]
        for response in responses:
            with self.subTest(response=response), patch.object(smoke, "urlopen", return_value=response):
                with self.assertRaises(ValueError):
                    smoke.request(url, media_types={"text/html"})

    def test_request_has_timeout_and_json_body(self):
        response = Response(API_URL + "/convert", b"{}", headers())
        with patch.object(smoke, "urlopen", return_value=response) as opened:
            smoke.request(response.url, method="POST", payload={"point": smoke.POINT})
        req = opened.call_args.args[0]
        self.assertEqual(opened.call_args.kwargs["timeout"], 15)
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data), {"point": smoke.POINT})
        self.assertEqual(req.get_header("Content-type"), "application/json")

    def test_http_error_returns_failure_exit_code(self):
        error = HTTPError(smoke.SITE_URL, 404, "Not Found", {}, None)
        try:
            with patch.object(smoke, "check_site", side_effect=error), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(smoke.main(), 1)
        finally:
            error.close()


class SiteTests(unittest.TestCase):
    def serve(self, req, timeout):
        url = req.full_url
        if url == smoke.SITE_URL:
            return Response(url, HTML.encode(), headers("text/html"))
        if url.startswith(smoke.SITE_URL):
            path = url.removeprefix(smoke.SITE_URL)
            body = APP_JS if path == "app.js" else b"/* asset */"
            return Response(url, body, headers(sorted(smoke.ASSETS[path])[0]))
        if url == API_URL + "/health":
            return Response(url, b'{"status":"ok"}', headers())
        if url == API_URL + "/convert":
            if req.get_method() == "OPTIONS":
                return Response(url, b"", headers(**{
                    "Access-Control-Allow-Methods": "GET,OPTIONS,POST",
                    "Access-Control-Allow-Headers": "content-type",
                }), status=204)
            self.payloads.append(json.loads(req.data))
            return Response(url, json.dumps(CONVERSION).encode(), headers())
        self.fail(f"Unexpected request: {url}")

    def setUp(self):
        self.payloads = []

    def test_healthy_site_including_cors_and_both_conversions(self):
        with patch.object(smoke, "urlopen", side_effect=self.serve), contextlib.redirect_stdout(io.StringIO()):
            smoke.check_site()
        self.assertEqual(self.payloads, [
            {"point": smoke.POINT, "output": "han"},
            {"code": smoke.EXPECTED_CODE, "output": "han"},
        ])

    def test_bad_health_cors_json_asset_and_conversion_fail(self):
        cases = [
            ("/health", "GET", b'{"status":"error"}', headers()),
            ("/health", "GET", b'[]', headers()),
            ("/health", "GET", b'not json', headers()),
            ("/health", "GET", b'{"status":"ok"}', headers(**{"Access-Control-Allow-Origin": "https://wrong.example"})),
            ("/convert", "OPTIONS", b"", headers(**{"Access-Control-Allow-Methods": "GET"})),
            ("/convert", "OPTIONS", b"", headers(**{"Access-Control-Allow-Methods": "POST"})),
            ("/convert", "POST", b'{"code":"wrong"}', headers()),
            ("/app.js", "GET", HTML.encode(), headers("text/html")),
        ]
        for path, method, body, response_headers in cases:
            def serve(req, timeout):
                if req.full_url.endswith(path) and req.get_method() == method:
                    return Response(req.full_url, body, response_headers, 204 if method == "OPTIONS" else 200)
                return self.serve(req, timeout)

            with self.subTest(path=path, method=method, body=body):
                with patch.object(smoke, "urlopen", side_effect=serve), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(ValueError):
                        smoke.check_site()


if __name__ == "__main__":
    unittest.main()
