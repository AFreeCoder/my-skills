#!/usr/bin/env python3
"""本地 AI 信息采集与简报生成；仅使用 Python 3.10+ 标准库。"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import uuid
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

SOURCES = Path(__file__).resolve().parents[1] / "references" / "sources.json"
PRODUCTS = {"OpenAI", "Codex", "ChatGPT", "Anthropic", "Claude", "Claude Code"}
SKIP = {"script", "style", "svg", "nav", "footer", "noscript", "button"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCK = {"p", "div", "section", "article", "main", "li", "br", "tr", "h1", "h2", "h3", "h4", "pre"}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def save(path, value):
    """原子替换，避免中断留下半个状态文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    temporary.replace(path)


def dump(path, value):
    save(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def load_lines(path):
    # 原文可含 Unicode 段落分隔符；JSONL 仅以 LF 分行。
    return [json.loads(line) for line in path.read_text().split("\n") if line.strip()]


def canonical(url):
    parts = urlsplit(url)
    if parts.scheme not in {"https", "http"} or not parts.netloc:
        raise ValueError("内容链接必须是 HTTP(S) URL")
    # 不丢弃查询参数和锚点：它们可能标识不同更新项。
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, parts.query, parts.fragment))


def date(value):
    if not value:
        return None
    for parser in (lambda s: datetime.fromisoformat(s.replace("Z", "+00:00")), parsedate_to_datetime):
        try:
            d = parser(value)
            return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
        except (ValueError, TypeError, OverflowError):
            pass
    return None


class Node:
    def __init__(self, tag="root", attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def text(self, base=""):
        if self.tag in SKIP or "hidden" in self.attrs:
            return ""
        if self.tag == "img":
            return self.attrs.get("alt") or ""
        content = "".join(child.text(base) if isinstance(child, Node) else child for child in self.children)
        if self.tag == "a" and self.attrs.get("href") and content.strip():
            link = urljoin(base, self.attrs["href"])
            if link.startswith(("https://", "http://")):
                content = f"[{content.strip()}]({link})"
        return f"\n{content}\n" if self.tag in BLOCK else content


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs)
        self.stack[-1].children.append(n)
        if tag not in VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def tidy(text):
    return re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", text).strip()


def html_text(text, url):
    root = Document(text).root
    nodes = list(root.walk())
    main = next((n for n in nodes if n.tag == "main"), None)
    main = main or next((n for n in nodes if n.tag == "article"), root)
    title = next((n.text() for n in nodes if n.tag == "title"), url)
    return tidy(main.text(url)), title, main


def record(source, url, title, text, published_at=None, **extra):
    url = canonical(url)
    return {"id": digest(source["id"] + "|" + url)[:24], "source_id": source["id"],
            "source_name": source["name"], "products_hint": source["products"],
            "url": url, "title": title.strip(), "text": text.strip(),
            "published_at": published_at, **extra}


def fetch(url, raw_dir, timeout):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; LocalNewsCollector/1.0)", "Accept": "*/*"})
    with urlopen(req, timeout=timeout) as response:
        body = response.read(12 * 1024 * 1024 + 1)
        if len(body) > 12 * 1024 * 1024:
            raise ValueError("响应超过 12 MiB，本轮未提取")
        encoding = response.headers.get_content_charset() or "utf-8"
        final_url = response.url
        text = body.decode(encoding, errors="replace")
        raw_dir.mkdir(parents=True, exist_ok=True)
        name = digest(url)[:20]
        (raw_dir / (name + ".bin")).write_bytes(body)
        dump(raw_dir / (name + ".json"), {"url": url, "final_url": final_url,
             "fetched_at": stamp(), "status": response.status,
             "content_type": response.headers.get("Content-Type"), "encoding": encoding})
        return text, final_url, str(raw_dir / (name + ".bin"))


def feed_records(source, text):
    root = ET.fromstring(text)
    nodes = [n for n in root.iter() if n.tag.split("}")[-1] in {"item", "entry"}]
    if root.tag.split("}")[-1] not in {"rss", "feed", "RDF"}:
        raise ValueError("响应不是 RSS/Atom")
    result = []
    for n in nodes:
        values = {c.tag.split("}")[-1]: c for c in n}
        def field(*names):
            for name in names:
                if name in values:
                    return "".join(values[name].itertext()).strip()
            return ""
        link = next((c.attrib.get("href") or (c.text or "") for c in n
                     if c.tag.split("}")[-1] == "link" and c.attrib.get("rel", "alternate") == "alternate"), "")
        if not link:
            continue
        url = urljoin(source["url"], link)
        content = field("encoded", "content", "description", "summary")
        plain = html_text(content, url)[0] if "<" in content else content
        published = field("published", "pubDate", "updated") or None
        result.append(record(source, url, field("title") or url, plain, published,
                             kind="feed_entry", content_scope="feed_content", original_id=field("guid", "id")))
    return result


def x_records(source, text):
    root = Document(text).root
    result = []
    for article in root.walk():
        if article.tag != "article":
            continue
        nodes = list(article.walk())
        def meta(prop):
            return next((n.attrs.get("content") for n in nodes
                         if n.tag == "meta" and n.attrs.get("itemprop", "").lower() == prop.lower()), None)
        url = article.attrs.get("itemid") or meta("url")
        if not url or not re.match(r"https://(?:x|twitter)\.com/[^/]+/status/\d+", url):
            continue
        content = meta("text")
        if not content:
            continue
        links = sorted({urljoin(url, n.attrs["href"]) for n in nodes if n.tag == "a" and n.attrs.get("href")})
        media = sorted({n.attrs["src"] for n in nodes if n.tag in {"img", "video"} and n.attrs.get("src")})
        result.append(record(source, url, content.splitlines()[0][:160], content, meta("datePublished"),
                             kind="x_post", author=urlsplit(url).path.split("/")[1],
                             content_scope="public_profile_excerpt", full_text_verified=False,
                             links=links, media=media))
    if not result:
        raise ValueError("公开页面未提取到带原文链接的帖子；需要浏览器读取或选定 API")
    return result


def page_record(source, text, url):
    if re.search(r"<html\b|<!doctype\b", text[:1500], re.I):
        plain, title, tree = html_text(text, url)
    else:
        plain, title, tree = text.strip(), source["name"], None
    if len(plain) < 120 or re.search(r"^(Just a moment|Access Denied|Checking your browser)", title, re.I):
        raise ValueError("未取得可用正文，可能是登录页或访问拦截")
    return record(source, url, title, plain, kind="page", content_scope="page_snapshot"), tree


def recent(items, days, limit):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    retained = [r for r in items if not date(r.get("published_at")) or date(r["published_at"]) >= cutoff]
    retained.sort(key=lambda r: date(r.get("published_at")) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return retained[:limit], len(retained) > limit


def acquire(source, run, args):
    raw = run / "raw" / source["id"]
    attempts, result = [], []
    for endpoint in source.get("endpoints", [source["url"]]):
        try:
            body, url, raw_path = fetch(endpoint, raw, args.timeout)
            if source["kind"] == "feed":
                result, limited = recent(feed_records(source, body), args.days, args.limit)
                coverage = "feed_window"
                if source.get("article_body"):
                    for item in result:
                        try:
                            full_body, final, article_raw = fetch(item["url"], raw, args.timeout)
                            article, _ = page_record(source, full_body, final)
                            item.update(text=article["text"], content_scope="article_page", raw_path=article_raw)
                        except Exception as exc:
                            attempts.append({"url": item["url"], "error": str(exc)[:300], "retained": "feed_content"})
            elif source["kind"] == "x":
                result, limited = recent(x_records(source, body), args.days, args.limit)
                coverage = "public_profile_snapshot"
            else:
                item, tree = page_record(source, body, url)
                result, limited, coverage = [item], False, "page_snapshot"
                if tree and source.get("article_path"):
                    urls = list(dict.fromkeys(urljoin(url, n.attrs["href"]) for n in tree.walk()
                                if n.tag == "a" and n.attrs.get("href")))
                    urls = [u for u in urls if urlsplit(u).netloc == urlsplit(url).netloc
                            and urlsplit(u).path.startswith(source["article_path"])
                            and urlsplit(u).path != source["article_path"]]
                    limited = len(urls) > args.limit
                    for article_url in urls[:args.limit]:
                        try:
                            article_body, final, article_raw = fetch(article_url, raw, args.timeout)
                            child, _ = page_record(source, article_body, final)
                            child.update(raw_path=article_raw, content_scope="article_page")
                            result.append(child)
                        except Exception as exc:
                            attempts.append({"url": article_url, "error": str(exc)[:300]})
            for item in result:
                item.setdefault("raw_path", raw_path)
            return result, {"source_id": source["id"], "name": source["name"],
                            "status": "partial" if attempts else "ok", "coverage": coverage,
                            "limited": limited, "items": len(result), "attempts": attempts}
        except Exception as exc:
            attempts.append({"url": endpoint, "error": str(exc)[:300]})
    return [], {"source_id": source["id"], "name": source["name"], "status": "failed", "items": 0, "attempts": attempts}


def persist(output, run, records, reports, scope):
    existing_path = output / "items.jsonl"
    existing = {r["id"]: r for r in load_lines(existing_path)} if existing_path.exists() else {}
    changed, material = [], []
    for r in records:
        transient = {"raw_path", "fetched_at", "first_seen_at", "changed_at", "content_hash"}
        fingerprint = digest(json.dumps({k: v for k, v in r.items() if k not in transient}, sort_keys=True, ensure_ascii=False))
        old = existing.get(r["id"])
        r.update(content_hash=fingerprint, fetched_at=stamp())
        r["first_seen_at"] = old["first_seen_at"] if old else r["fetched_at"]
        r["changed_at"] = old["changed_at"] if old and old["content_hash"] == fingerprint else r["fetched_at"]
        if old is None or old["content_hash"] != fingerprint:
            changed.append(r)
        existing[r["id"]] = r
        material.append(r)
        save(run / "materials" / (r["id"] + ".md"), f"# {r['title']}\n\n来源：{r['url']}\n\n{r['text']}\n")
    for path, items in ((run / "items.jsonl", material), (run / "changed.jsonl", changed)):
        save(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in items))
    report = {"run_id": run.name, "finished_at": stamp(), "scope": scope, "sources": reports,
              "items": len(material), "changed": len(changed)}
    dump(run / "report.json", report)
    index = [f"# 采集材料 {run.name}", "", f"本轮 {len(material)} 份材料，其中 {len(changed)} 份新增或修改。", "",
             "| 来源 | 状态 | 材料数 | 覆盖范围 |", "| --- | --- | --- | --- |"]
    for r in reports:
        index.append(f"| {r['name']} | {r['status']} | {r['items']} | {r.get('coverage', '')} |")
    index.extend(["", "## 原始材料", ""])
    for r in material:
        index.append(f"- [{r['source_name']} · {r['title'].replace(chr(10), ' ')}](materials/{r['id']}.md) — `{r['id']}`")
    save(run / "index.md", "\n".join(index) + "\n")
    # 完整批次先落盘，再推进累计状态，便于异常后重新采集。
    save(existing_path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in existing.values()))
    print(json.dumps({"run": str(run), "items": len(material), "changed": len(changed),
                      "failed": [r["source_id"] for r in reports if r["status"] == "failed"]}, ensure_ascii=False))


def render(run, events_file):
    items = {r["id"]: r for r in load_lines(run / "items.jsonl")}
    payload = json.loads(events_file.read_text())
    covered, groups = set(), {}
    for event in payload["events"]:
        refs = event.get("item_ids", [])
        products = event.get("products", [])
        if not refs or any(r not in items for r in refs):
            raise ValueError("事件引用了未采集的材料 ID")
        if not products or not set(products) <= PRODUCTS:
            raise ValueError("事件产品分类无效")
        for field in ("title", "summary", "category"):
            if not isinstance(event.get(field), str) or not event[field].strip():
                raise ValueError(f"事件缺少 {field}")
        covered.update(refs)
        groups.setdefault(products[0], []).append(event)
    for skipped in payload.get("excluded", []):
        if skipped.get("item_id") not in items or not skipped.get("reason"):
            raise ValueError("未纳入简报的材料需要有效 ID 与原因")
        covered.add(skipped["item_id"])
    if covered != set(items):
        raise ValueError(f"尚有 {len(set(items) - covered)} 份材料没有处理去向")
    report = json.loads((run / "report.json").read_text())
    lines = ["# AI 信息简报", "", f"采集批次：{run.name}；原始材料 {len(items)} 份；合并后 {len(payload['events'])} 个事件。", ""]
    for product, events in groups.items():
        lines.extend([f"## {product}", ""])
        for event in events:
            lines.extend([f"### {event['title']}", "", f"分类：{event['category']} · {' / '.join(event['products'])}", "", event["summary"], ""])
            for rid in dict.fromkeys(event["item_ids"]):
                item = items[rid]
                lines.append(f"- [{item['source_name']}]({item['url']}) · {item.get('published_at') or '日期未提取'}")
            lines.append("")
    lines.extend(["## 采集范围", "", f"参数：{json.dumps(report['scope'], ensure_ascii=False)}", "",
                  "X 公开页面只覆盖本次页面返回的帖子，网页快照可能包含更早内容。", "",
                  f"未纳入正文的材料：{len(payload.get('excluded', []))} 份，原因见 events.json。", ""])
    for r in report["sources"]:
        lines.append(f"- {r['name']}：{r['status']}，{r['items']} 份材料" + ("，达到本轮数量上限" if r.get("limited") else ""))
    dump(run / "events.json", payload)
    save(run / "brief.md", "\n".join(lines) + "\n")
    print(str(run / "brief.md"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    collect = sub.add_parser("collect", help="抓取公开来源，不调用付费 API")
    collect.add_argument("--output", required=True, type=Path)
    collect.add_argument("--sources", type=Path, default=SOURCES)
    collect.add_argument("--only", help="逗号分隔的来源 ID")
    collect.add_argument("--days", type=int, default=7)
    collect.add_argument("--limit", type=int, default=20, help="每个 feed/X 的条数或列表页跟进文章数上限")
    collect.add_argument("--timeout", type=int, default=20)
    collect.add_argument("--workers", type=int, default=4)
    imp = sub.add_parser("import", help="导入浏览器/API 已取得的原文 JSONL")
    imp.add_argument("--output", required=True, type=Path)
    imp.add_argument("--file", required=True, type=Path)
    imp.add_argument("--sources", type=Path, default=SOURCES)
    rend = sub.add_parser("render", help="检查分类结果的来源覆盖并生成 Markdown")
    rend.add_argument("--run", required=True, type=Path)
    rend.add_argument("--events", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "render":
        render(args.run.resolve(), args.events.resolve())
        return
    sources = json.loads(args.sources.read_text())
    if args.command == "collect":
        if min(args.days, args.limit, args.timeout, args.workers) < 1:
            parser.error("数量、天数、超时和并发数必须为正整数")
        if args.only:
            ids = set(args.only.split(","))
            if ids - {s["id"] for s in sources}:
                parser.error("--only 包含未知来源")
            sources = [s for s in sources if s["id"] in ids]
    output = args.output.expanduser().resolve()
    # 安装目录是代码，不是采集数据库。
    if output.is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error("输出目录不能位于 skill 安装目录内")
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".collect.lock"
    try:
        lock.mkdir()
    except FileExistsError:
        parser.error(f"同一输出目录已有采集任务，或上次异常留下锁：{lock}")
    try:
        run = output / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6])
        run.mkdir(parents=True)
        records, reports = [], []
        if args.command == "collect":
            with ThreadPoolExecutor(max_workers=min(args.workers, 8)) as pool:
                for items, report in pool.map(lambda s: acquire(s, run, args), sources):
                    records.extend(items)
                    reports.append(report)
            scope = {"mode": "public", "days": args.days, "limit_per_source": args.limit,
                     "selected_sources": len(sources), "page_dates": "由整理阶段检查，网页不按日期截断"}
        else:
            by_id = {s["id"]: s for s in sources}
            for row in load_lines(args.file):
                if not row.get("text", "").strip():
                    raise ValueError("导入项缺少原文 text")
                source = by_id[row["source_id"]]
                records.append(record(source, row["url"], row["title"], row["text"], row.get("published_at"),
                                      kind=row.get("kind", "imported"), content_scope="external_capture",
                                      raw_path=str(run / "raw" / "import.jsonl")))
            save(run / "raw" / "import.jsonl", args.file.read_text())
            for sid in dict.fromkeys(r["source_id"] for r in records):
                reports.append({"source_id": sid, "name": by_id[sid]["name"], "status": "ok",
                                "items": sum(r["source_id"] == sid for r in records), "coverage": "external_capture"})
            scope = {"mode": "import", "selected_sources": len(reports)}
        # 页面内重复链接/重复帖子只留一份，原始响应不受影响。
        records = list({r["id"]: r for r in records}.values())
        for report in reports:
            report["items"] = sum(r["source_id"] == report["source_id"] for r in records)
        persist(output, run, records, reports, scope)
    finally:
        lock.rmdir()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, ET.ParseError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        sys.exit(1)
