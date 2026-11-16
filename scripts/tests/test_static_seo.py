"""Check SEO content directly from HTML, without executing JavaScript."""

import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CrawlText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.metadata = {}
        self.canonicals = []
        self.headings = []
        self.paragraphs = []
        self.title = []
        self.service_intro = None
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section" and "service-intro" in attrs.get("class", "").split():
            self.service_intro = attrs
        if tag == "meta":
            self.metadata[attrs.get("name")] = attrs.get("content")
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))
        if tag == "h1":
            self.headings.append([])
            self.current = self.headings[-1]
        elif tag == "p":
            self.paragraphs.append([])
            self.current = self.paragraphs[-1]
        elif tag == "title":
            self.current = self.title

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag in {"title", "h1", "p"}:
            self.current = None


class StaticSEOTests(unittest.TestCase):
    def setUp(self):
        self.page = CrawlText()
        self.page.feed((ROOT / "web/index.html").read_text(encoding="utf-8"))

    def test_search_metadata_and_canonical(self):
        title = "".join(self.page.title)
        for keyword in ("국가지점번호", "조회", "변환", "NPNkorea"):
            self.assertIn(keyword, title)
        description = self.page.metadata["description"]
        for keyword in ("국가지점번호", "WGS84", "위도", "경도"):
            self.assertIn(keyword, description)
        self.assertEqual(self.page.canonicals, ["https://www.npnkorea.com/"])

    def test_service_intro_is_visually_hidden_but_accessible(self):
        intro = self.page.service_intro
        self.assertIsNotNone(intro)
        self.assertIn("visually-hidden", intro["class"].split())
        self.assertNotIn("hidden", intro)
        self.assertNotEqual(intro.get("aria-hidden"), "true")
        self.assertEqual(intro["aria-labelledby"], "service-title")

    def test_service_text_is_in_initial_html(self):
        self.assertEqual(len(self.page.headings), 1)
        self.assertIn("국가지점번호 조회", "".join(self.page.headings[0]))
        body = " ".join("".join(parts) for parts in self.page.paragraphs)
        for phrase in ("국가지점번호", "경도, 위도 순서", "10 m 격자", "남서쪽 모서리"):
            self.assertIn(phrase, body)


if __name__ == "__main__":
    unittest.main()
