import datetime as dt
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

from cooking_classes import geo, pipeline, report
from cooking_classes.config import load_config
from cooking_classes.models import CookingClass, Extraction, RawPost
from cooking_classes.sources import manual, pages
from cooking_classes.sources.web_search import parse_json_array

FUTURE = (dt.date.today() + dt.timedelta(days=10)).isoformat()


def make_class(**kw):
    base = dict(title="Pasta Night", host="Nonna's Kitchen", description=None,
                cuisine_or_topic="Italian", start_date=FUTURE, start_time="18:30",
                end_time=None, recurrence=None, venue=None, address=None, town="ridgewood",
                state="NJ", is_online=False, in_bergen_county="unknown", price="$65",
                audience="adults", registration_url=None, contact=None)
    base.update(kw)
    return CookingClass(**base)


class FakeMessages:
    def __init__(self, search_items, extraction):
        self.search_items, self.extraction = search_items, extraction
        self.create_calls, self.parse_calls = [], []

    def create(self, **params):
        self.create_calls.append(params)
        return NS(stop_reason="end_turn",
                  content=[NS(type="text", text=json.dumps(self.search_items))])

    def parse(self, **params):
        self.parse_calls.append(params)
        return NS(stop_reason="end_turn", parsed_output=self.extraction)


class FakeClient:
    def __init__(self, *a):
        self.beta = NS(messages=FakeMessages(*a))


class GeoTests(unittest.TestCase):
    def test_70_municipalities(self):
        self.assertEqual(len(set(geo.BERGEN_MUNICIPALITIES)), 70)

    def test_canonical_town(self):
        self.assertEqual(geo.canonical_town("Hohokus, NJ"), "Ho-Ho-Kus")
        self.assertEqual(geo.canonical_town("Washington Twp"), "Washington Township")
        self.assertEqual(geo.canonical_town("fair lawn"), "Fair Lawn")
        self.assertIsNone(geo.canonical_town("Montclair"))


class ParsingTests(unittest.TestCase):
    def test_parse_json_array_tolerates_fences(self):
        txt = 'Here you go:\n```json\n[{"url": "https://x.com/e/1", "text": "a"}, {"text": "no url"}]\n```'
        self.assertEqual([d["url"] for d in parse_json_array(txt)], ["https://x.com/e/1"])
        self.assertEqual(parse_json_array("nothing found"), [])

    def test_html_to_text(self):
        t = pages.html_to_text("<html><script>x()</script><p>Sushi class</p><p>Sat&nbsp;7pm</p></html>")
        self.assertIn("Sushi class", t)
        self.assertNotIn("x()", t)

    def test_relevance_filter(self):
        self.assertTrue(pipeline.looks_relevant(RawPost("reddit", "u", "Kids baking class in Teaneck")))
        self.assertFalse(pipeline.looks_relevant(RawPost("reddit", "u", "Best pizza in Paramus?")))
        self.assertTrue(pipeline.looks_relevant(RawPost("manual", "u", "anything")))


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copy(Path(__file__).parent.parent / "config.toml", self.tmp / "config.toml")
        (self.tmp / "inbox").mkdir()
        self.cfg = load_config(self.tmp / "config.toml")
        self.cfg["web_search"]["queries"] = ["q1"]

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_end_to_end_with_fake_claude(self):
        (self.tmp / "inbox" / "post1.txt").write_text(
            "URL: https://facebook.com/groups/x/posts/1\nPasta class at my place in Ridgewood!")
        client = FakeClient(
            [{"url": "https://facebook.com/events/123", "platform": "facebook",
              "title": "Pasta Night", "text": "Hands-on pasta cooking class, Ridgewood NJ"}],
            Extraction(is_cooking_class_post=True, reason="class", classes=[make_class()]),
        )
        stats = pipeline.run(self.cfg, only=["web_search", "manual"], client=client)

        # Same class from two posts merges into one record with two sources.
        self.assertEqual(stats["extracted"], 2)
        self.assertEqual(stats["new_classes"], 1)
        data = json.loads((self.tmp / "data" / "classes.json").read_text())
        (rec,) = data.values()
        self.assertEqual(rec["town"], "Ridgewood")
        self.assertEqual(rec["in_bergen_county"], "yes")
        self.assertEqual(len(rec["sources"]), 2)
        self.assertIn("Pasta Night", (self.tmp / "data" / "latest.md").read_text())
        self.assertTrue((self.tmp / "inbox" / "processed" / "post1.txt").exists())

        # Request shape: web search tool, fallbacks, structured output model.
        create = client.beta.messages.create_calls[0]
        self.assertEqual(create["tools"][0]["type"], "web_search_20260209")
        self.assertEqual(create["extra_body"], {"fallbacks": "default"})
        self.assertIs(client.beta.messages.parse_calls[0]["output_format"], Extraction)

        # Second run: everything already seen, no new extraction calls.
        stats2 = pipeline.run(self.cfg, only=["web_search", "manual"], client=client)
        self.assertEqual(stats2["extracted"], 0)
        self.assertEqual(len(client.beta.messages.parse_calls), 2)

    def test_manual_jsonl(self):
        (self.tmp / "inbox" / "posts.jsonl").write_text(
            '{"url": "https://fb.com/1", "platform": "facebook", "text": "Baking class"}\nnot json\n')
        posts = manual.collect(self.cfg)
        self.assertEqual([p.url for p in posts], ["https://fb.com/1"])


class ReportTests(unittest.TestCase):
    def test_select_drops_past_and_out_of_county(self):
        past = (dt.date.today() - dt.timedelta(days=3)).isoformat()
        recs = {
            "a": {"id": "a", "start_date": FUTURE, "in_bergen_county": "yes", "sources": []},
            "b": {"id": "b", "start_date": past, "in_bergen_county": "yes", "sources": []},
            "c": {"id": "c", "start_date": past, "recurrence": "Every Tue",
                  "in_bergen_county": "yes", "sources": []},
            "d": {"id": "d", "start_date": FUTURE, "in_bergen_county": "no", "sources": []},
            "e": {"id": "e", "start_date": None, "in_bergen_county": "unknown", "sources": []},
        }
        self.assertEqual([r["id"] for r in report.select(recs, True)], ["c", "a", "e"])


if __name__ == "__main__":
    unittest.main()
