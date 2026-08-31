"""只验证采集保存与来源引用的主线行为，无网络和付费请求。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import news

SOURCE = {"id": "sample", "name": "Sample", "products": ["Codex"], "url": "https://example.org/feed", "kind": "feed"}


class NewsTests(unittest.TestCase):
    def fx_args(self, **overrides):
        return SimpleNamespace(**dict(dict(date="2026-08-31", timezone="Asia/Shanghai", days=7,
                                          limit=20, timeout=1, x_max_pages=5), **overrides))

    def fx_post(self, number, published="2026-08-31T04:00:00Z", **extra):
        return dict(dict(type="status", id=str(number), url=f"https://x.com/example/status/{number}",
                         text="正文" * 300, created_at=published, author={"screen_name": "example"}), **extra)

    def test_calendar_day_uses_local_midnight_and_exclusive_end(self):
        start, end = news.time_window(self.fx_args())
        self.assertEqual(start.isoformat(), "2026-08-30T16:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-08-31T16:00:00+00:00")
        values = ["2026-08-30T15:59:59Z", "2026-08-30T16:00:00Z", "2026-08-31T15:59:59Z", "2026-08-31T16:00:00Z"]
        rows = [{"published_at": value} for value in values]
        retained, limited = news.recent(rows, 7, 20, start, end)
        self.assertEqual({r["published_at"] for r in retained}, set(values[1:3]))
        self.assertFalse(limited)

    def test_fxembed_keeps_long_text_reply_and_quote(self):
        post = self.fx_post(1, replying_to="another", quote={"url": "https://x.com/another/status/5", "text": "上下文"})
        item = news.fxembed_records(SOURCE, {"code": 200, "results": [post]})[0]
        self.assertEqual(item["text"], post["text"])
        self.assertEqual(item["quoted_post"]["text"], "上下文")
        self.assertEqual(item["replying_to"], "another")
        self.assertFalse(item["full_text_verified"])
        with self.assertRaises(ValueError):
            news.fxembed_records(SOURCE, {"code": 500, "results": []})

    def test_fxembed_paginates_past_pinned_post_and_deduplicates(self):
        pages = [
            {"code": 200, "results": [self.fx_post(9, "2020-01-01T00:00:00Z"), self.fx_post(1)], "cursor": {"bottom": "next"}},
            {"code": 200, "results": [self.fx_post(1), self.fx_post(2, replying_to="another")], "cursor": {}},
        ]
        with tempfile.TemporaryDirectory() as d:
            with patch.object(news, "fetch", side_effect=[(json.dumps(p), "https://api.fxtwitter.com", "/raw/page.bin") for p in pages]) as fetch:
                items, report = news.acquire_fxembed(SOURCE, Path(d), self.fx_args())
        self.assertEqual(len(items), 2)
        self.assertEqual(report["pages"], 2)
        self.assertEqual(report["stop_reason"], "exhausted")
        self.assertIn("cursor=next", fetch.call_args_list[1].args[0])

    def test_fxembed_reports_limit_and_partial_page_failure(self):
        page = {"code": 200, "results": [self.fx_post(1), self.fx_post(2)], "cursor": {"bottom": "next"}}
        with tempfile.TemporaryDirectory() as d:
            with patch.object(news, "fetch", return_value=(json.dumps(page), "https://api.fxtwitter.com", "/raw/page.bin")):
                items, report = news.acquire_fxembed(SOURCE, Path(d), self.fx_args(limit=1))
                self.assertEqual(len(items), 1)
                self.assertTrue(report["limited"])
                self.assertEqual(report["stop_reason"], "item_limit")
                _, loop = news.acquire_fxembed(SOURCE, Path(d), self.fx_args())
                self.assertEqual(loop["status"], "partial")
                self.assertEqual(loop["stop_reason"], "repeated_cursor")
            with patch.object(news, "fetch", side_effect=[(json.dumps(page), "https://api.fxtwitter.com", "/raw/page.bin"), OSError("offline")]):
                items, report = news.acquire_fxembed(SOURCE, Path(d), self.fx_args())
                self.assertEqual(len(items), 2)
                self.assertEqual(report["status"], "partial")
                self.assertEqual(report["stop_reason"], "request_failed")

    def test_fxembed_old_reposts_do_not_hide_newer_next_page(self):
        source = {**SOURCE, "url": "https://x.com/example"}
        pages = [
            {"code": 200, "results": [self.fx_post(9, "2020-01-01T00:00:00Z", reposted_by={"screen_name": "example"})], "cursor": {"bottom": "next"}},
            {"code": 200, "results": [self.fx_post(1)], "cursor": {}},
        ]
        with tempfile.TemporaryDirectory() as d, patch.object(news, "fetch", side_effect=[(json.dumps(p), "https://api.fxtwitter.com", "/raw/page.bin") for p in pages]):
            items, report = news.acquire_fxembed(source, Path(d), self.fx_args())
        self.assertEqual([r["original_id"] for r in items], ["1"])
        self.assertEqual(report["pages"], 2)

    def test_fxembed_keeps_good_items_and_reports_unavailable_posts(self):
        page = {"code": 200, "results": [self.fx_post(1), {"type": "status", "id": "bad"},
                {"type": "tombstone", "id": "gone", "reason": "unavailable"}], "cursor": {}}
        with tempfile.TemporaryDirectory() as d, patch.object(news, "fetch", return_value=(json.dumps(page), "https://api.fxtwitter.com", "/raw/page.bin")):
            items, report = news.acquire_fxembed(SOURCE, Path(d), self.fx_args())
        self.assertEqual([r["original_id"] for r in items], ["1"])
        self.assertEqual(report["status"], "partial")
        self.assertEqual([r["post_id"] for r in report["attempts"]], ["bad", "gone"])

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
