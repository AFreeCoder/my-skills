#!/usr/bin/env python3
"""
Clip a webpage URL into local Markdown with downloaded images.
"""
from __future__ import annotations

import argparse
import base64
import datetime as _dt
import hashlib
import mimetypes
import os
import re
import sys
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin, urlparse

_VAULT_ENV = os.environ.get("OBSIDIAN_VAULT")
DEFAULT_VAULT_PATH = Path(_VAULT_ENV).expanduser().resolve() if _VAULT_ENV else None


def _slugify(text: str, fallback: str = "clipped-page") -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9\-_.]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-._")
    return text or fallback


def _safe_filename(text: str, fallback: str = "clipped-page") -> str:
    text = text.strip()
    text = re.sub(r"[\\/:*?\"<>|]+", "-", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or fallback


def _parse_srcset(srcset: str) -> Optional[str]:
    candidates = []
    for part in srcset.split(","):
        piece = part.strip()
        if not piece:
            continue
        segs = piece.split()
        url = segs[0]
        width = 0
        if len(segs) > 1 and segs[1].endswith("w"):
            try:
                width = int(segs[1][:-1])
            except ValueError:
                width = 0
        candidates.append((width, url))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[-1][1]

def _normalize_inline_wrappers(soup) -> None:
    inline_tags = ["span", "strong", "b", "i", "em", "a"]
    block_tags = {
        "div",
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "table",
        "tr",
        "td",
        "th",
        "blockquote",
        "pre",
        "code",
        "section",
    }
    for tag_name in inline_tags:
        for element in list(soup.find_all(tag_name)):
            contains_block = False
            for block_tag in block_tags:
                if element.find(block_tag):
                    contains_block = True
                    break
            if not contains_block:
                continue
            new_div = soup.new_tag("div")
            for child in list(element.contents):
                new_div.append(child)
            element.replace_with(new_div)

def _style_is_bold(style: str) -> bool:
    if not style:
        return False
    style = style.lower()
    if "font-weight" not in style:
        return False
    match = re.search(r"font-weight\s*:\s*([^;]+)", style)
    if not match:
        return False
    value = match.group(1).strip()
    if "bold" in value:
        return True
    num_match = re.search(r"(\d+)", value)
    if not num_match:
        return False
    try:
        return int(num_match.group(1)) >= 600
    except ValueError:
        return False


def _style_is_italic(style: str) -> bool:
    if not style:
        return False
    style = style.lower()
    if "font-style" not in style:
        return False
    match = re.search(r"font-style\s*:\s*([^;]+)", style)
    if not match:
        return False
    value = match.group(1).strip()
    return "italic" in value


def _style_is_underline(style: str) -> bool:
    if not style:
        return False
    style = style.lower()
    if "text-decoration" not in style:
        return False
    match = re.search(r"text-decoration\s*:\s*([^;]+)", style)
    if not match:
        return False
    value = match.group(1).strip()
    return "underline" in value


def _promote_inline_styles(soup) -> None:
    for span in list(soup.find_all("span")):
        style = span.get("style") or ""
        bold = _style_is_bold(style)
        italic = _style_is_italic(style)
        underline = _style_is_underline(style)
        if not bold and not italic and not underline:
            continue
        wrappers = []
        if bold:
            wrappers.append("strong")
        if italic:
            wrappers.append("em")
        if underline:
            wrappers.append("u")
        root = soup.new_tag(wrappers[0])
        current = root
        for tag in wrappers[1:]:
            nested = soup.new_tag(tag)
            current.append(nested)
            current = nested
        for child in list(span.contents):
            current.append(child)
        span.replace_with(root)


_PSEUDO_LIST_ORDERED_RE = re.compile(r"^\s*(\d{1,3}|[A-Za-z])[.、)]\s*$")
_PSEUDO_LIST_BULLET_RE = re.compile(
    r"^\s*[•●○■□◆◇·▪▫•○●■□◆◇·*\-]\s*$"
)


def _promote_pseudo_lists(soup) -> None:
    """Convert WeChat-style flex pseudo-lists into real <ol>/<ul>.

    WeChat editors render numbered/bulleted items as one flex <section> per item:
        <section style="display:flex"><span>1.</span><p>content</p></section>
    Adjacent sections like this are siblings, not children of a single <ol>.
    Markdownify renders them as marker + blank line + content, breaking the list.
    Detect runs of such siblings under the same parent and replace them with a
    real <ol>/<ul> wrapping the content portions in <li>.
    """

    def classify(section):
        if getattr(section, "name", None) != "section":
            return None, None
        style = (section.get("style") or "").lower().replace(" ", "")
        if "display:flex" not in style:
            return None, None
        children = [c for c in section.children if getattr(c, "name", None)]
        if len(children) < 2:
            return None, None
        marker_text = children[0].get_text(" ", strip=True)
        if not marker_text or len(marker_text) > 4:
            return None, None
        if _PSEUDO_LIST_ORDERED_RE.match(marker_text):
            return "ol", children[1:]
        if _PSEUDO_LIST_BULLET_RE.match(marker_text):
            return "ul", children[1:]
        return None, None

    seen_parents = set()
    for section in list(soup.find_all("section")):
        if section.parent is None:
            continue
        kind, _ = classify(section)
        if kind is None:
            continue
        parent = section.parent
        if id(parent) in seen_parents:
            continue
        seen_parents.add(id(parent))

        kids = [c for c in parent.children if getattr(c, "name", None)]
        i = 0
        while i < len(kids):
            k1, _ = classify(kids[i])
            if k1 is None:
                i += 1
                continue
            j = i
            items = []
            while j < len(kids):
                k2, body = classify(kids[j])
                if k2 != k1:
                    break
                items.append((kids[j], body))
                j += 1
            if len(items) >= 2:
                new_list = soup.new_tag(k1)
                for _, body in items:
                    li = soup.new_tag("li")
                    for node in list(body):
                        li.append(node.extract())
                    new_list.append(li)
                items[0][0].replace_with(new_list)
                for orig, _ in items[1:]:
                    orig.decompose()
                kids = [c for c in parent.children if getattr(c, "name", None)]
                if new_list in kids:
                    i = kids.index(new_list) + 1
                else:
                    i = j
            else:
                i = j if j > i else i + 1


def _promote_blockquotes(soup) -> None:
    for element in list(soup.find_all(["section", "div", "p"])):
        if element.name == "blockquote":
            continue
        style = (element.get("style") or "").lower()
        classes = " ".join(element.get("class", [])).lower()
        if (
            "blockquote" in classes
            or "quote" in classes
            or ("border-left" in style and "padding" in style)
        ):
            block = soup.new_tag("blockquote")
            for child in list(element.contents):
                block.append(child)
            element.replace_with(block)



def _ensure_picture_img(soup, base_url: str) -> None:
    for picture in soup.find_all("picture"):
        img = picture.find("img")
        if img:
            continue
        source = picture.find("source")
        if not source:
            continue
        srcset = source.get("srcset") or source.get("data-srcset")
        src = source.get("src") or source.get("data-src")
        if srcset:
            src = _parse_srcset(srcset)
        if not src:
            continue
        if src.startswith("//"):
            src = f"{urlparse(base_url).scheme}:{src}"
        if src.startswith("/"):
            src = urljoin(base_url, src)
        img = soup.new_tag("img")
        img["src"] = src
        picture.append(img)


def _convert_inline_svg(soup) -> None:
    for svg in list(soup.find_all("svg")):
        svg_str = str(svg)
        data_uri = (
            "data:image/svg+xml;base64,"
            + base64.b64encode(svg_str.encode("utf-8")).decode("utf-8")
        )
        img = soup.new_tag("img")
        img["src"] = data_uri
        svg.replace_with(img)

def _image_url_key(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    return f"{parsed.netloc}{parsed.path}"


_BAD_TITLES = {"微信公众平台", "微信公众号", "微信", "wechat", "404", "page not found"}


def _extract_meta_title(html: str) -> Optional[str]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for attrs in (
        {"property": "og:title"},
        {"name": "twitter:title"},
        {"itemprop": "headline"},
    ):
        meta = soup.find("meta", attrs=attrs)
        content = meta.get("content").strip() if meta and meta.get("content") else None
        if content:
            return content
    for selector_id in ("activity-name", "title"):
        el = soup.find(id=selector_id)
        if el:
            text = el.get_text(" ", strip=True)
            if text:
                return text
    return None


def _filter_title(title: Optional[str]) -> Optional[str]:
    if not title:
        return None
    cleaned = title.strip()
    if not cleaned:
        return None
    if cleaned.strip().lower() in _BAD_TITLES:
        return None
    return cleaned


def _extract_cover_image(html: str, base_url: str) -> Optional[str]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    def _add(url: Optional[str]) -> None:
        if not url:
            return
        candidates.append(_normalize_image_url(url, base_url))
    meta = soup.find("meta", attrs={"property": "og:image"})
    _add(meta.get("content") if meta else None)
    meta = soup.find("meta", attrs={"name": "twitter:image"})
    _add(meta.get("content") if meta else None)
    meta = soup.find("meta", attrs={"itemprop": "image"})
    _add(meta.get("content") if meta else None)
    for url in candidates:
        if url:
            return url
    return None


def _inject_cover_image(
    html: str,
    cover_url: Optional[str],
    base_url: str,
    title: Optional[str] = None,
    insert_title: bool = False,
) -> Tuple[str, bool]:
    if not cover_url:
        return html, False
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return html, False
    soup = BeautifulSoup(html, "html.parser")
    cover_url = _normalize_image_url(cover_url, base_url)
    cover_key = _image_url_key(cover_url)
    existing_img = None
    for img in soup.find_all("img"):
        src = _pick_image_source(img) or img.get("src")
        if not src:
            continue
        src = _normalize_image_url(src, base_url)
        if _image_url_key(src) == cover_key:
            existing_img = img
            break
    if existing_img and insert_title and title and not soup.find("h1"):
        heading = soup.new_tag("h1")
        heading.string = title
        parent = existing_img.parent
        if parent and parent.name in ("p", "figure", "div"):
            parent.insert_after(heading)
        else:
            existing_img.insert_after(heading)
        return str(soup), True
    if existing_img:
        return str(soup), True
    wrapper = soup.new_tag("p")
    img_tag = soup.new_tag("img")
    img_tag["src"] = cover_url
    wrapper.append(img_tag)
    target = soup.body if soup.body else soup
    if target.contents:
        target.insert(0, wrapper)
        if insert_title and title and not soup.find("h1"):
            heading = soup.new_tag("h1")
            heading.string = title
            target.insert(1, heading)
    else:
        target.append(wrapper)
        if insert_title and title and not soup.find("h1"):
            heading = soup.new_tag("h1")
            heading.string = title
            target.append(heading)
    return str(soup), True


def _pick_image_source(tag) -> Optional[str]:
    attrs = [
        "data-original",
        "data-src",
        "data-lazy-src",
        "data-actualsrc",
        "data-raw",
        "data-url",
        "data-img",
        "data-srcset",
        "data-lazy-srcset",
        "srcset",
        "src",
    ]
    for attr in attrs:
        val = tag.get(attr)
        if not val:
            continue
        if "srcset" in attr:
            picked = _parse_srcset(val)
            if picked:
                return picked
        else:
            return val
    return None


def _normalize_image_url(src: str, base_url: str) -> str:
    if not src:
        return src
    if src.startswith("//"):
        src = f"{urlparse(base_url).scheme}:{src}"
    if src.startswith("/"):
        src = urljoin(base_url, src)
    if urlparse(base_url).scheme == "https" and src.startswith("http:"):
        src = "https:" + src[5:]
    return src


def _guess_ext(url: str, content_type: Optional[str] = None) -> str:
    path = urlparse(url).path
    ext = Path(path).suffix
    if ext and len(ext) <= 6:
        return ext
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    return ".bin"


def _download_bytes(url: str, timeout: int, user_agent: str) -> Tuple[bytes, str]:
    try:
        import requests
    except ImportError:
        print("缺少依赖 requests。请先运行: python -m pip install requests", file=sys.stderr)
        sys.exit(2)

    headers = {"User-Agent": user_agent} if user_agent else {}
    resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "")
    return resp.content, content_type


def _decode_data_uri(data_uri: str) -> Tuple[Optional[bytes], Optional[str]]:
    if not data_uri.startswith("data:"):
        return None, None
    try:
        header, data = data_uri.split(",", 1)
    except ValueError:
        return None, None
    if ";base64" in header:
        mime = header.split(":", 1)[1].split(";")[0]
        try:
            return base64.b64decode(data), mime
        except Exception:
            return None, None
    return None, None


def _get_html(url: str, engine: str, timeout: int, user_agent: str) -> Tuple[str, Optional[str]]:
    if engine == "browser":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("未安装 playwright。请先运行: python -m pip install playwright && playwright install", file=sys.stderr)
            sys.exit(2)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=user_agent or None)
            page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
            title = page.title()
            html = page.content()
            browser.close()
        return html, title

    try:
        import requests
    except ImportError:
        print("缺少依赖 requests。请先运行: python -m pip install requests", file=sys.stderr)
        sys.exit(2)

    headers = {"User-Agent": user_agent} if user_agent else {}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or resp.encoding
    text = resp.text
    if "mp.weixin.qq.com" in url and (
        "环境异常" in text or "secitptpage/verify" in text or "去验证" in text
    ):
        return _get_html(url, "browser", timeout, user_agent)
    return text, None


def _extract_main(html: str, base_url: str) -> Tuple[str, Optional[str]]:
    try:
        from readability import Document

        doc = Document(html)
        title = doc.short_title()
        return doc.summary(html_partial=True), title
    except Exception:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            print("缺少依赖 beautifulsoup4。请先运行: python -m pip install beautifulsoup4", file=sys.stderr)
            sys.exit(2)

        soup = BeautifulSoup(html, "html.parser")
        node = soup.find("article") or soup.find("main") or soup.body or soup
        title = None
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        return str(node), title


def _to_markdown(html: str) -> str:
    try:
        from markdownify import MarkdownConverter

        class ObsidianConverter(MarkdownConverter):
            def convert_u(self, el, text, **kwargs):
                return f"<u>{text}</u>"

        return ObsidianConverter(heading_style="ATX").convert(html)
    except Exception:
        try:
            import html2text
        except ImportError:
            print(
                "缺少依赖 markdownify 或 html2text。请先运行: python -m pip install markdownify",
                file=sys.stderr,
            )
            sys.exit(2)
        h = html2text.HTML2Text()
        h.body_width = 0
        return h.handle(html)


def _clean_markdown_body(markdown: str, base_url: str) -> str:
    if "mp.weixin.qq.com" not in base_url:
        return markdown.strip()
    tail_markers = [
        "\n![赞赏二维码]",
        "\n微信扫一扫赞赏作者",
        "\n赞赏后展示我的头像",
    ]
    cut_at = len(markdown)
    for marker in tail_markers:
        idx = markdown.find(marker)
        if idx >= 0:
            cut_at = min(cut_at, idx)
    return markdown[:cut_at].strip()


def _rewrite_images(
    html: str,
    base_url: str,
    assets_dir: Path,
    base_dir: Path,
    timestamp: str,
    timeout: int,
    user_agent: str,
) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("缺少依赖 beautifulsoup4。请先运行: python -m pip install beautifulsoup4", file=sys.stderr)
        sys.exit(2)

    assets_dir.mkdir(parents=True, exist_ok=True)
    soup = BeautifulSoup(html, "html.parser")
    _ensure_picture_img(soup, base_url)
    _convert_inline_svg(soup)
    _promote_inline_styles(soup)
    for img in soup.find_all("img"):
        src = _pick_image_source(img)
        if not src:
            continue
        src = _normalize_image_url(src, base_url)
        if "wikipedia/commons/thumb/" in src:
            idx = src.rfind(".")
            ext = src[idx:] if idx > -1 else ""
            if ".svg.png" in src:
                ext = ".svg"
            marker = f"{ext}/"
            cut = src.find(marker)
            if cut > 0:
                src = src[: cut + len(ext)]
                src = src.replace("/commons/thumb/", "/commons/")
        if "zhimg.com" in src and ".jpg" in src and "ztext-gif" in (img.get("class") or []):
            src = src.replace(".jpg", ".webp")
        if src.startswith("data:"):
            data, mime = _decode_data_uri(src)
            if data and mime:
                ext = mimetypes.guess_extension(mime) or ".bin"
                name = f"{timestamp}-{hashlib.md5(data).hexdigest()}{ext}"
                out_path = assets_dir / name
                if not out_path.exists():
                    out_path.write_bytes(data)
                img["src"] = os.path.relpath(out_path, base_dir)
            continue
        abs_url = urljoin(base_url, src)
        try:
            data, content_type = _download_bytes(abs_url, timeout, user_agent)
        except Exception:
            continue
        ext = _guess_ext(abs_url, content_type)
        name = f"{timestamp}-{hashlib.md5(abs_url.encode('utf-8')).hexdigest()}{ext}"
        out_path = assets_dir / name
        if not out_path.exists():
            out_path.write_bytes(data)
        img["src"] = os.path.relpath(out_path, base_dir)
    return str(soup)

def _count_tag(html: str, tag: str) -> int:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return 0
    soup = BeautifulSoup(html, "html.parser")
    return len(soup.find_all(tag))

def _table_text_length(html: str) -> int:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return 0
    soup = BeautifulSoup(html, "html.parser")
    total = 0
    for cell in soup.find_all(["th", "td"]):
        text = cell.get_text(" ", strip=True)
        if text:
            total += len(text)
    return total


def _preprocess_html(html: str, base_url: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return html
    soup = BeautifulSoup(html, "html.parser")
    _normalize_inline_wrappers(soup)
    _ensure_picture_img(soup, base_url)
    _convert_inline_svg(soup)
    _promote_pseudo_lists(soup)
    _promote_blockquotes(soup)
    _promote_inline_styles(soup)
    return str(soup)


def _fallback_body(html: str, base_url: str) -> str:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return html
    soup = BeautifulSoup(html, "html.parser")
    if "mp.weixin.qq.com" in base_url:
        node = soup.find(id="js_content")
        if node:
            return str(node)
    node = soup.find("article") or soup.find("main") or soup.body or soup
    return str(node)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clip webpage to local Markdown with images.")
    parser.add_argument("--url", required=True, help="网页 URL")
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_VAULT_PATH / "10_raw") if DEFAULT_VAULT_PATH else None,
        required=DEFAULT_VAULT_PATH is None,
        help="输出目录（未设置 OBSIDIAN_VAULT 时必填，否则默认 $OBSIDIAN_VAULT/10_raw）",
    )
    parser.add_argument(
        "--assets-dir",
        default=str(DEFAULT_VAULT_PATH / "assets") if DEFAULT_VAULT_PATH else None,
        help="图片输出目录（相对 out-dir 或绝对路径，默认 out-dir/assets）",
    )
    parser.add_argument("--title", default=None, help="标题覆盖")
    parser.add_argument("--engine", choices=["requests", "browser"], default="requests", help="获取方式")
    parser.add_argument("--timeout", type=int, default=30, help="请求超时（秒）")
    parser.add_argument("--user-agent", default="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")
    parser.add_argument("--no-frontmatter", action="store_true", help="不写 YAML frontmatter")
    heading_group = parser.add_mutually_exclusive_group()
    heading_group.add_argument("--with-heading", action="store_true", help="写一级标题")
    heading_group.add_argument("--no-heading", action="store_true", help="不写一级标题（默认）")
    args = parser.parse_args()

    html, browser_title = _get_html(args.url, args.engine, args.timeout, args.user_agent)
    cover_url = _extract_cover_image(html, args.url)
    pre_html = _preprocess_html(html, args.url)
    content_html, content_title = _extract_main(pre_html, args.url)

    if _count_tag(pre_html, "li") > 0 and _count_tag(content_html, "li") == 0:
        content_html = _fallback_body(pre_html, args.url)
    if _count_tag(pre_html, "img") > 0 and _count_tag(content_html, "img") == 0:
        content_html = _fallback_body(pre_html, args.url)
    pre_table_len = _table_text_length(pre_html)
    content_table_len = _table_text_length(content_html)
    if pre_table_len >= 20 and content_table_len < max(5, int(pre_table_len * 0.2)):
        content_html = _fallback_body(pre_html, args.url)
    meta_title = _extract_meta_title(html)
    title = (
        args.title
        or _filter_title(meta_title)
        or _filter_title(content_title)
        or _filter_title(browser_title)
        or args.url
    )
    safe_title = _safe_filename(title)
    slug = _slugify(title)
    insert_title = bool(args.with_heading)
    content_html, cover_present = _inject_cover_image(
        content_html,
        cover_url,
        args.url,
        title=title,
        insert_title=insert_title,
    )

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.assets_dir:
        assets_dir = Path(args.assets_dir).expanduser()
        if not assets_dir.is_absolute():
            assets_dir = out_dir / assets_dir
    else:
        assets_dir = out_dir / "assets"
    assets_dir = assets_dir.resolve()

    timestamp = _dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    rewritten_html = _rewrite_images(
        content_html,
        args.url,
        assets_dir,
        out_dir,
        timestamp,
        args.timeout,
        args.user_agent,
    )
    markdown_body = _clean_markdown_body(_to_markdown(rewritten_html), args.url)

    parts = []
    if not args.no_frontmatter:
        captured_at = _dt.datetime.now().strftime("%Y-%m-%d")
        parts.append("---")
        parts.append(f"title: {safe_title}")
        parts.append(f"captured_at: {captured_at}")
        parts.append("source_type: web")
        parts.append(f"source_url: {args.url}")
        parts.append("status: raw")
        parts.append("projects: []")
        parts.append("---\n")
    if insert_title and not cover_present:
        parts.append(f"# {safe_title}\n")
    parts.append(markdown_body)

    out_path = out_dir / f"{safe_title}.md"
    out_path.write_text("\n".join(parts).strip() + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
