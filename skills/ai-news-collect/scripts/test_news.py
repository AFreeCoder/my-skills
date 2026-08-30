"""只验证采集保存与来源引用的主线行为，无网络和付费请求。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import news

SOURCE = {"id": "sample", "name": "Sample", "products": ["Codex"], "url": "https://example.org/feed", "kind": "feed"}


class NewsTests(unittest.TestCase):
    def test_feed_html_and_distinct_anchors(self):
        items = news.feed_records(SOURCE, '''<rss><channel>
          <item><title>One</title><link>https://example.org/log#one</link><description>&lt;p&gt;Full &amp;amp; body&lt;/p&gt;</description></item>
          <item><title>Two</title><link>https://example.org/log#two</link><description>Second</description></item>
        </channel></rss>''')
        self.assertEqual(items[0]["text"], "Full & body")
        self.assertNotEqual(items[0]["id"], items[1]["id"])
        with self.assertRaises(ValueError):
            news.feed_records(SOURCE, "<html><body>Login</body></html>")

    def test_html_boolean_alt_and_navigation(self):
        text, _, _ = news.html_text('<html><nav>Menu</nav><main><h1>Update</h1><img alt><p>Content</p><script>ignore()</script></main></html>', "https://example.org")
        self.assertIn("Content", text)
        self.assertNotIn("Menu", text)
        self.assertNotIn("ignore()", text)

    def test_x_requires_post_content_and_preserves_snapshot_limit(self):
        page = '''<article itemid="https://x.com/example/status/123">
          <meta itemprop="text" content="A launch announcement">
          <meta itemprop="datePublished" content="2026-08-29T00:00:00Z">
          <a href="https://example.org/details">Details</a></article>'''
        r = news.x_records(SOURCE, page)[0]
        self.assertEqual(r["author"], "example")
        self.assertFalse(r["full_text_verified"])
        self.assertIn("https://example.org/details", r["links"])
        with self.assertRaises(ValueError):
            news.x_records(SOURCE, "<html>Please sign in</html>")

    def test_failure_is_reported_without_fake_items(self):
        with tempfile.TemporaryDirectory() as d:
            args = type("Args", (), {"timeout": 1})()
            with patch.object(news, "fetch", side_effect=OSError("offline")):
                items, report = news.acquire(SOURCE, Path(d), args)
        self.assertEqual(items, [])
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["attempts"][0]["error"], "offline")

    def test_repeat_update_and_unicode_jsonl_roundtrip(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            output = Path(d)
            def run(number, body):
                directory = output / "runs" / str(number)
                r = news.record(SOURCE, "https://example.org/a", "Title", body)
                news.persist(output, directory, [r], [], {})
                return news.load_lines(directory / "changed.jsonl")
            body = "line\u2028separator\u2029paragraph\nnew line"
            self.assertEqual(len(run(1, body)), 1)
            self.assertEqual(len(run(2, body)), 0)
            self.assertEqual(len(run(3, body + " edited")), 1)
            self.assertEqual(len(news.load_lines(output / "items.jsonl")), 1)
            self.assertEqual(news.load_lines(output / "items.jsonl")[0]["text"], body + " edited")

    def test_render_merges_sources_and_rejects_missing_evidence(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            output = Path(d)
            run = output / "runs" / "sample"
            a = news.record(SOURCE, "https://example.org/a", "A", "First announcement")
            b = news.record(SOURCE, "https://example.org/b", "B", "More details")
            news.persist(output, run, [a, b], [], {})
            payload = {"events": [{"title": "同一事件", "products": ["Codex"], "category": "产品更新", "summary": "两个来源合并", "item_ids": [a["id"], b["id"]]}]}
            f = output / "input.json"
            news.dump(f, payload)
            news.render(run, f)
            brief = (run / "brief.md").read_text()
            self.assertIn("https://example.org/a", brief)
            self.assertIn("https://example.org/b", brief)
            payload["events"][0]["item_ids"] = [a["id"]]
            news.dump(f, payload)
            with self.assertRaisesRegex(ValueError, "没有处理去向"):
                news.render(run, f)
            payload["events"][0]["item_ids"] = ["invented"]
            news.dump(f, payload)
            with self.assertRaisesRegex(ValueError, "未采集"):
                news.render(run, f)


if __name__ == "__main__":
    unittest.main()
