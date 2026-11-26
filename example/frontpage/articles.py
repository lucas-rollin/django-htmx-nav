"""Markdown article loader backed by Python-Markdown and Django templates."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import markdown
from benchmarks.metrics.summary import load_benchmark_summary
from django.conf import settings
from django.http import Http404, HttpRequest
from django.template import RequestContext, Template
from django.utils.safestring import SafeString, mark_safe

ARTICLES_DIR = Path(__file__).resolve().parent / "content" / "articles"

_CODE_TAG_RE = re.compile(r"(<code\b[^>]*>)(.*?)(</code>)", re.DOTALL)
_PRE_TAG_RE = re.compile(r"<pre>(.*?)</pre>", re.DOTALL)


@dataclass(frozen=True)
class TocItem:
    """Single heading entry in an article's table of contents."""

    level: int
    id: str
    title: str


@dataclass(frozen=True)
class CompiledArticle:
    """Parsed article metadata, ToC, raw source, and compiled Django body."""

    slug: str
    title: str
    meta_description: str
    eyebrow: str
    heading: str
    lede_html: SafeString
    demo_variant: str
    raw_markdown: str
    toc: tuple[TocItem, ...]
    body_template: Template


@dataclass(frozen=True)
class RenderedArticle:
    """Request-rendered article context passed to `article.html`."""

    slug: str
    title: str
    meta_description: str
    eyebrow: str
    heading: str
    lede: SafeString
    demo_variant: str
    raw_markdown: str
    toc: tuple[TocItem, ...]
    body_html: SafeString


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    if not raw.startswith("+++"):
        return {}, raw
    _, fm, body = raw.split("+++", 2)
    return tomllib.loads(fm), body.lstrip("\r\n")


def _flatten_toc(tokens: list[dict[str, Any]]) -> tuple[TocItem, ...]:
    items: list[TocItem] = []
    for node in tokens:
        items.append(TocItem(level=node["level"], id=node["id"], title=node["name"]))
        if node.get("children"):
            items.extend(_flatten_toc(node["children"]))
    return tuple(items)


def _protect_code_and_style_pre(rendered_html: str) -> str:
    """Wrap Django delimiters inside `<code>` in `{% verbatim %}` and style `<pre>`."""

    def _wrap_verbatim(match: re.Match[str]) -> str:
        open_tag, inner, close_tag = match.groups()
        if "{%" in inner or "{{" in inner or "{#" in inner:
            return f"{open_tag}{{% verbatim %}}{inner}{{% endverbatim %}}{close_tag}"
        return match.group(0)

    html_out = _CODE_TAG_RE.sub(_wrap_verbatim, rendered_html)
    return _PRE_TAG_RE.sub(
        r'<div class="rounded-xl overflow-hidden border border-base-300 code-block p-4 not-prose my-3">'
        r'<div class="overflow-x-auto"><pre>\1</pre></div></div>',
        html_out,
    )


def _compile_article(slug: str) -> CompiledArticle:
    if "/" in slug or "\\" in slug or ".." in slug:
        raise Http404(f"Invalid article slug: '{slug}'")
    path = ARTICLES_DIR / f"{slug}.md"
    if not path.is_file():
        raise Http404(f"Article not found: '{slug}'")

    raw_markdown = path.read_text(encoding="utf-8")
    meta, body_md = _split_frontmatter(raw_markdown)

    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "attr_list", "toc"],
        extension_configs={"toc": {"toc_depth": "2-3"}},
    )
    body_html = _protect_code_and_style_pre(md.convert(body_md))

    lede_raw = str(meta.get("lede", ""))
    lede_html = mark_safe(
        markdown.markdown(lede_raw).removeprefix("<p>").removesuffix("</p>")
    )

    return CompiledArticle(
        slug=slug,
        title=str(meta["title"]),
        meta_description=str(meta.get("meta_description", "")),
        eyebrow=str(meta.get("eyebrow", "")),
        heading=str(meta["heading"]),
        lede_html=lede_html,
        demo_variant=str(meta.get("demo_variant", "")),
        raw_markdown=raw_markdown,
        toc=_flatten_toc(md.toc_tokens),
        body_template=Template(body_html),
    )


@lru_cache(maxsize=32)
def _compile_article_cached(slug: str) -> CompiledArticle:
    return _compile_article(slug)


def render_article(request: HttpRequest, slug: str) -> RenderedArticle:
    """Render a Markdown article with request context and live benchmark metrics."""
    compiled = (
        _compile_article(slug) if settings.DEBUG else _compile_article_cached(slug)
    )
    ctx = RequestContext(request, {"bench": load_benchmark_summary()})
    return RenderedArticle(
        slug=compiled.slug,
        title=compiled.title,
        meta_description=compiled.meta_description,
        eyebrow=compiled.eyebrow,
        heading=compiled.heading,
        lede=compiled.lede_html,
        demo_variant=compiled.demo_variant,
        raw_markdown=compiled.raw_markdown,
        toc=compiled.toc,
        body_html=mark_safe(compiled.body_template.render(ctx)),
    )
