#!/usr/bin/env python3
"""Build a set of markdown pages into a self-contained HTML site.

    docsbuild                       # build the doc set(s) found from here
    docsbuild --set onboarding      # one named set of several
    docsbuild --root ~/repo/docs    # a project in another checkout

The unit of work is a **doc set**: a directory of markdown with a ``site.toml`` beside
it. A project may have one, or several listed in a ``sites.toml`` — a guide, a plan, a
book of runbooks. Nothing here knows or cares which; the two features that look
set-specific (``[concat]`` and ``[[standalone]]``) are optional config keys any set may
use.

**Pages are discovered from the directory** rather than listed anywhere: every ``*.md``
is a page, ordered by filename with ``index`` first, titled by its own ``# heading``.
Adding a page means adding the file.

Every path resolves relative to the config file that named it, never to the working
directory. That is what lets one installed copy build docs living anywhere.

**Python 3.11+**, and three small runtime dependencies: ``markdown-it-py`` with
``mdit-py-plugins`` for the markdown, and ``mdurl`` which the former requires. Nothing
else, and nothing heavy — a consumer installs this tool, so its dependencies never touch
their own project.

**Markdown is CommonMark**, via ``markdown-it-py``, plus tables, strikethrough,
footnotes and task lists. Raw HTML is escaped rather than passed through: rendering
markup from a document would mean trusting every input or shipping a sanitiser, and
neither belongs here.

Two conventions of this tool's own sit on top, both in ``_renderer``:

* Links written as ``*.md`` (so the sources also read on GitHub) are rewritten to
  ``*.html`` for the built site when they point at a page the project builds, keeping
  any ``#section``. A link to markdown that is not a page, such as a README beside the
  docs, keeps pointing at that file.
* A **status badge** at the very start of a list item renders as a coloured pill — the
  way a document marks finished work *without deleting it*. Tokens are declared per doc
  set in ``[badges]``; with none declared, every bracketed word stays literal text.
"""

from __future__ import annotations

import argparse
import os
import posixpath
import re
import sys
import tomllib
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.tasklists import tasklists_plugin

Page = tuple[str, str]  # (slug, title)

LinkDirs = tuple[str, str]  # (source dir name, output dir name)

# A doc set names its own directories in ``site.toml``; these are only the defaults for
# a caller that has no site to hand. See ``_renderer`` for what they are used for.
DEFAULT_LINK_DIRS: LinkDirs = ("markdown", "html")

# Badge styles the bundled stylesheet defines. A project may use any token it likes; one
# whose style is not in here renders as an unstyled pill until the project adds the CSS.
BADGE_STYLES = ("done", "next", "later", "planned", "dropped")

# Restores the light/dark choice before first paint, so a themed page never flashes.
THEME_SCRIPT = (
    "<script>(function(){try{var t=localStorage.getItem('theme');"
    "if(t==='dark'||t==='light')document.documentElement.setAttribute("
    "'data-theme',t);}catch(e){}})();</script>"
)


# ------------------------------------------------------------------ inline rendering


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _badge_styles(raw: object) -> dict[str, tuple[str, str]]:
    """Normalise a ``[badges]`` table into ``token -> (css class, label)``.

    Two spellings, because most tokens want neither::

        [badges]
        DONE  = "Done"                                # class: badge done
        BUILT = { label = "Built", style = "done" }    # class: badge done

    A bare string derives its style from the lowercased token, which is right whenever
    the token names its own colour. The table form exists for a token that should reuse
    another's styling, and for tokens whose lowercase is not one of the styles the
    stylesheet defines.
    """
    if not isinstance(raw, dict):
        return {}
    out: dict[str, tuple[str, str]] = {}
    for token, value in raw.items():
        if isinstance(value, dict):
            label = str(value.get("label", token.title()))
            style = str(value.get("style", token.lower()))
        else:
            label, style = str(value), token.lower()
        out[token] = (f"badge {style}", label)
    return out


_BADGE_TOKEN = re.compile(r"^\[([A-Z][A-Z0-9_]*)\]\s*")


def _badge_rule(badges: Mapping[str, tuple[str, str]]) -> Any:
    """A core rule promoting a leading ``[TOKEN]`` in a list item to a pill.

    Markdown has no syntax for this, so it cannot be a parser extension — it is a
    transform over the token stream after parsing. Only the *first* inline token of a
    list item is considered, which is what keeps ``[TODO]`` mid-sentence as plain text.
    """
    # Where to stop looking for an item's *own* first inline token. Scanning past a
    # nested list's opener let an item with no text of its own claim the badge belonging
    # to its first child, which put the pill's styling on the wrong ``<li>``.
    boundaries = ("list_item_close", "bullet_list_open", "ordered_list_open")

    def rule(state: Any) -> None:
        tokens = state.tokens
        for index, opener in enumerate(tokens):
            if opener.type != "list_item_open":
                continue
            # `no branch`: every list_item_open has a matching close, so this loop
            # always exits by `break`, never by exhaustion.
            for token in tokens[index + 1 :]:  # pragma: no branch
                if token.type in boundaries:
                    break
                if token.type != "inline":
                    continue
                match = _BADGE_TOKEN.match(token.content)
                if match is None or match.group(1) not in badges:
                    break
                children = token.children or []
                if not children or children[0].type != "text":
                    # The bracketed word was parsed as something else — a reference
                    # link, given a matching `[TOKEN]: url` definition. Markdown's own
                    # meaning wins; badging it would render the pill *and* the link.
                    break
                css, label = badges[match.group(1)]
                token.content = token.content[match.end() :]
                children[0].content = _BADGE_TOKEN.sub("", children[0].content)
                pill = Token("badge", "", 0)
                pill.meta = {"css": css, "label": label}
                token.children = [pill, *children]
                opener.attrJoin("class", "lb")
                break

    return rule


@dataclass(frozen=True)
class LinkTargets:
    """Where one page's links can lead, for a real build.

    ``pages`` maps the source ``.md`` of every page the project builds — in any doc set,
    standalone pages included — to the ``.html`` it becomes. ``source_dir`` is the
    directory the page being rendered is read from, which its relative links are
    written against; ``output_dir`` is where its HTML is written, which they must be
    rewritten against. All paths are absolute and resolved.
    """

    pages: Mapping[Path, Path]
    source_dir: Path
    output_dir: Path

    def href(self, path: str, sibling_marker: str) -> str | None:
        """The link to the file a relative ``.md`` path names, from the built page.

        A page links to its ``.html``. A path through another set's source directory
        (``sibling_marker``, e.g. ``/markdown/``) that is not a known page belongs to a
        set this build was not told about, as with ``--config``, so ``None`` hands it
        back to the naming convention. Anything else is not a page: it still links to
        the file itself, rebased onto the output directory so it resolves from there.
        """
        target = (self.source_dir / path).resolve()
        if target in self.pages:
            target = self.pages[target]
        elif sibling_marker in path:
            return None
        return Path(os.path.relpath(target, self.output_dir)).as_posix()


def _split_fragment(href: str) -> tuple[str, str]:
    """``page.md#section`` → ``("page.md", "#section")``; no fragment gives ``""``."""
    path, hash_mark, fragment = href.partition("#")
    return path, hash_mark + fragment


def _rewrite_href(href: str, link_dirs: LinkDirs, targets: LinkTargets | None) -> str:
    """Point one link at the built site. See ``LinkTargets`` and ``_renderer``.

    A relative link to a ``.md`` file is authored that way so the source also reads on
    GitHub. With ``targets`` (a real build) it is resolved against the project's actual
    pages. Without them, or for a sibling set's page the build does not know, it is
    assumed to be a page and becomes ``.html``, with a link through a sibling set's
    source directory repointed at that set's output.
    """
    path, fragment = _split_fragment(href)
    source_dir, output_dir = link_dirs
    if path.endswith(".md") and not _NOT_RELATIVE.match(path):
        if targets is not None:
            resolved = targets.href(path, f"/{source_dir}/")
            if resolved is not None:
                return resolved + fragment
        path = path[:-3] + ".html"
    if source_dir != output_dir:
        path = path.replace(f"/{source_dir}/", f"/{output_dir}/")
    return path + fragment


def _renderer(
    link_dirs: LinkDirs = DEFAULT_LINK_DIRS,
    badges: Mapping[str, tuple[str, str]] | None = None,
    targets: LinkTargets | None = None,
) -> MarkdownIt:
    """A configured CommonMark renderer.

    CommonMark plus tables, strikethrough, footnotes and task lists. ``html=False``
    keeps raw HTML escaped, as the hand-written converter did. That is worth keeping:
    passing markup through would mean trusting every input or shipping a sanitiser.

    Four rules customise the output, and they are the whole reason this is not just a
    library call: page links written as ``.md``, anchor ids for in-page contents, the
    horizontal-scroll wrapper around tables, and status badges.
    """
    md = MarkdownIt("commonmark", {"html": False, "xhtmlOut": False})
    md.enable(["table", "strikethrough"])
    md.use(footnote_plugin).use(tasklists_plugin)

    if badges:
        md.core.ruler.push("docsbuild_badges", _badge_rule(badges))
        md.add_render_rule(
            "badge",
            lambda self, tokens, idx, options, env: (
                f'<span class="{tokens[idx].meta["css"]}">'
                f"{esc(tokens[idx].meta['label'])}</span>"
            ),
            fmt="html",
        )

    def link_open(self: Any, tokens: Any, idx: int, options: Any, env: Any) -> str:
        href = tokens[idx].attrGet("href")
        if href:
            tokens[idx].attrSet("href", _rewrite_href(href, link_dirs, targets))
        return self.renderToken(tokens, idx, options, env)

    def heading_open(self: Any, tokens: Any, idx: int, options: Any, env: Any) -> str:
        # h2/h3 only: deep enough for an in-page contents panel, shallow enough that the
        # ids stay meaningful. GitHub-style, so a `page.md#section` written to work on
        # GitHub lands on the same heading here.
        if tokens[idx].tag in ("h2", "h3"):
            tokens[idx].attrSet("id", anchor(tokens[idx + 1].content))
        return self.renderToken(tokens, idx, options, env)

    md.add_render_rule("link_open", link_open, fmt="html")
    md.add_render_rule("heading_open", heading_open, fmt="html")
    md.add_render_rule(
        "table_open",
        lambda self, tokens, idx, options, env: '<div class="tbl"><table>',
        fmt="html",
    )
    md.add_render_rule(
        "table_close",
        lambda self, tokens, idx, options, env: "</table></div>",
        fmt="html",
    )
    return md


def md_to_html(
    md: str,
    link_dirs: LinkDirs = DEFAULT_LINK_DIRS,
    badges: Mapping[str, tuple[str, str]] | None = None,
    targets: LinkTargets | None = None,
) -> str:
    """Convert markdown to an HTML fragment.

    ``link_dirs`` is the set's ``(source, output)`` directory names, used to repoint
    cross-set links when no ``targets`` are given. ``badges`` maps a ``[TOKEN]`` at the
    start of a list item to a pill; absent, no token is special and every bracketed word
    stays literal text. ``targets`` are the project's real pages; see ``LinkTargets``.
    """
    return _renderer(link_dirs, badges, targets).render(md).strip()


def h2_headings(md: str) -> list[tuple[str, str]]:
    """The page's ``##`` headings as ``(anchor, text)``, for in-page contents panels."""
    return [
        (anchor(m.group(1)), m.group(1))
        for line in md.split("\n")
        if (m := re.match(r"##\s+(.*)", line))
    ]


# ---------------------------------------------------------------------- page chrome


def toc(pages: list[Page], active: str, brand: str) -> str:
    """The contents sidebar, with the current page marked."""
    entries = []
    for page_slug, title in pages:
        cls = ' class="active"' if page_slug == active else ""
        entries.append(f'<li><a href="{page_slug}.html"{cls}>{esc(title)}</a></li>')
    links = "".join(entries)
    return (
        f'<nav class="toc"><a class="brand" href="index.html">{esc(brand)}</a>'
        f"<h2>Contents</h2><ol>{links}</ol></nav>"
    )


def _nav_link(item: Page | None, kind: str, label: str) -> str:
    if item is None:
        return f'<span class="{kind} disabled"></span>'
    link_slug, title = item
    return (
        f'<a class="{kind}" href="{link_slug}.html">'
        f"<small>{label}</small>{esc(title)}</a>"
    )


def nav(pages: list[Page], index: int, position: str) -> str:
    """Previous / next buttons, derived from the page's position in ``pages``."""
    prev = pages[index - 1] if index > 0 else None
    nxt = pages[index + 1] if index < len(pages) - 1 else None
    return (
        f'<div class="nav {position}">'
        f"{_nav_link(prev, 'prev', 'Previous')}"
        f"{_nav_link(nxt, 'next', 'Next')}</div>"
    )


def _shell(title: str, style: str, sidebar: str, main: str) -> str:
    """The common HTML document: head, inlined CSS, theme script, sidebar + main."""
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)}</title>\n"
        f"<style>{style}</style>\n{THEME_SCRIPT}\n</head>\n<body>\n"
        f'<div class="layout">{sidebar}<main>{main}</main></div>\n'
        "</body>\n</html>\n"
    )


def page_shell(
    pages: list[Page],
    index: int,
    page_slug: str,
    title: str,
    body: str,
    style: str,
    brand: str,
    title_suffix: str,
) -> str:
    """One page of a guide: contents sidebar, prev/next above and below the article."""
    main = (
        f"{nav(pages, index, 'top')}<article>{body}</article>"
        f"{nav(pages, index, 'bottom')}"
    )
    sidebar = toc(pages, page_slug, brand)
    return _shell(f"{title} · {title_suffix}", style, sidebar, main)


def standalone_page(
    title: str,
    brand: str,
    brand_href: str,
    md: str,
    style: str,
    link_dirs: LinkDirs = DEFAULT_LINK_DIRS,
    badges: Mapping[str, tuple[str, str]] | None = None,
    targets: LinkTargets | None = None,
) -> str:
    """A self-contained page outside any reading chain, with an in-page section TOC."""
    items = "".join(
        f'<li><a href="#{anchor}">{esc(text)}</a></li>'
        for anchor, text in h2_headings(md)
    )
    sidebar = (
        f'<nav class="toc"><a class="brand" href="{brand_href}">{esc(brand)}</a>'
        f"<h2>On this page</h2><ol>{items}</ol></nav>"
    )
    body = f"<article>{md_to_html(md, link_dirs, badges, targets)}</article>"
    return _shell(title, style, sidebar, body)


# ----------------------------------------------------------------------- build utils


def prune_stale(html_dir: Path, keep: set[str]) -> list[str]:
    """Delete generated pages that are no longer part of the page set.

    The build only ever writes the current pages, so a renamed or removed one used to
    leave its old file behind — still opening in a browser, still turning up in
    searches, silently out of sync with its source. Only ``*.html`` directly inside
    ``html_dir`` is considered, so the markdown sources and ``style.css`` (which live
    above it) are never at risk.
    """
    removed: list[str] = []
    for path in sorted(html_dir.glob("*.html")):
        if path.name not in keep:
            path.unlink()
            removed.append(path.name)
    return removed


def read_sources(md_dir: Path, pages: list[Page]) -> dict[str, str]:
    """Read every page's markdown, failing fast rather than building a partial site."""
    sources: dict[str, str] = {}
    for page_slug, _ in pages:
        md_path = md_dir / f"{page_slug}.md"
        if not md_path.exists():
            raise SystemExit(f"missing markdown source: {md_path}")
        sources[page_slug] = md_path.read_text()
    return sources


def write_pages(html_dir: Path, rendered: dict[str, str]) -> list[str]:
    """Prune stale pages, then write the rendered ones. Returns what was removed.

    Pruning happens *after* rendering, never before: a failure part-way through
    conversion must leave the existing docs untouched rather than deleted.
    """
    html_dir.mkdir(parents=True, exist_ok=True)
    removed = prune_stale(html_dir, set(rendered))
    for name, html in rendered.items():
        (html_dir / name).write_text(html)
    return removed


def report(built: int, html_dir: Path, removed: list[str]) -> None:
    """Print what the build did, so a rename is visible rather than silent."""
    print(f"Built {built} pages into {html_dir}")
    if removed:
        print(f"Removed {len(removed)} stale page(s): {', '.join(removed)}")


# ------------------------------------------------------------------ page discovery


def first_h1(md: str) -> str:
    """The text of the page's first ``#`` heading (its title)."""
    for line in md.split("\n"):
        if m := re.match(r"#\s+(.*)", line):
            return m.group(1)
    return ""


def _page_sort_key(path: Path) -> tuple[int, str]:
    """Filename order, except a cover page named ``index`` always comes first.

    Plain sorting puts ``index`` last, since letters sort after digits.
    """
    return (0 if path.stem == "index" else 1, path.stem)


def discover_pages(
    source: Path,
    titles: Mapping[str, str] | None = None,
    order: Sequence[str] | None = None,
) -> list[Page]:
    """The reading order for a doc set, derived from the directory itself.

    Every ``*.md`` in ``source`` is a page. Its title is the ``titles`` override if one
    is given, else the file's first ``#`` heading, else the slug. ``order`` replaces the
    default sort entirely, for a set whose sequence can't be expressed by filename.
    """
    titles = titles or {}
    found = {p.stem: p for p in source.glob("*.md")}
    if order is None:
        slugs = [p.stem for p in sorted(found.values(), key=_page_sort_key)]
    else:
        missing = [s for s in order if s not in found]
        if missing:
            raise SystemExit(f"{source}: 'order' names missing page(s): {missing}")
        slugs = list(order)
    return [
        (slug, titles.get(slug) or first_h1(found[slug].read_text()) or slug)
        for slug in slugs
    ]


# ------------------------------------------------------------------- concatenation


def anchor(title: str) -> str:
    """A GitHub-style heading anchor for a title (for the single-file build)."""
    text = re.sub(r"[^\w\s-]", "", title.strip().lower())
    return text.replace(" ", "-")


_MD_LINK = re.compile(r"\]\(([^)]+)\)")

# A link that is not relative to the page's own directory: a URL with a scheme, a
# site-absolute path, or a bare in-page anchor. Rebasing any of these would be wrong.
_NOT_RELATIVE = re.compile(r"(^[a-z][a-z0-9+.-]*:)|(^[/#])", re.IGNORECASE)


def concat_links(
    md: str,
    anchors: Mapping[str, str],
    slugs: Collection[str],
    prefix: str = "markdown",
) -> str:
    """Rewrite one page's links for the concatenated single-file build.

    Links to a page *in this set* become in-document anchors — matched against the real
    page list rather than a guessed filename convention, so an oddly-named page is not
    silently missed.

    Every other relative link is **rebased**. The page sources live in the set's source
    directory; the concatenated file is written somewhere else, usually a level or two
    above. A path that was correct relative to the sources is therefore wrong relative
    to the concatenated file, by exactly the distance between the two. ``prefix`` is
    that distance — the relative path *from* the concatenated file's directory *to* the
    sources — so joining it onto the link and normalising gives the corrected path.

    With the default, ``../../other/x.md`` becomes ``../other/x.md`` (one level shorter)
    and ``assets/x.png`` becomes ``markdown/assets/x.png`` (one level longer). Both fall
    out of the same rule rather than being special cases.
    """

    def rewrite(match: re.Match[str]) -> str:
        href = match.group(1)
        path, fragment = _split_fragment(href)
        stem = path[:-3] if path.endswith(".md") else None
        if stem is not None and stem in slugs:
            # Every page is inlined, so a section link jumps to that section's anchor.
            return f"](#{fragment[1:] or anchors.get(stem, stem)})"
        if _NOT_RELATIVE.match(href):
            return match.group(0)
        return f"]({posixpath.normpath(posixpath.join(prefix, href))})"

    return _MD_LINK.sub(rewrite, md)


# -------------------------------------------------------------------------- config


BUNDLED_STYLE = Path(__file__).resolve().parent / "style.css"


@dataclass(frozen=True)
class SiteConfig:
    """One doc set, as described by its ``site.toml``. All paths are absolute."""

    name: str
    base: Path  # the config file's own directory; every relative path hangs off it
    source: Path
    output: Path
    style: Path
    brand: str
    title_suffix: str
    titles: dict[str, str] = field(default_factory=dict)
    badges: dict[str, tuple[str, str]] = field(default_factory=dict)
    order: list[str] | None = None
    standalone: list[dict] = field(default_factory=list)
    concat: dict | None = None


def load_site(config_path: Path) -> SiteConfig:
    """Read a ``site.toml``, resolving every path relative to the config file.

    Resolving against the config's own directory — not the working directory — is what
    lets a set be built from anywhere, including a checkout of a different repository.

    ``style`` is optional: omit it and the bundled stylesheet is used. That is what lets
    a project with a single doc set be nothing but a ``site.toml`` and a directory of
    markdown, with no stylesheet to write and no parent directory to invent.
    """
    config_path = config_path.resolve()
    here = config_path.parent
    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)
    if missing := [key for key in ("brand", "title_suffix") if key not in raw]:
        raise SystemExit(
            f"{config_path}: missing required key(s) {', '.join(missing)}.\n"
            "A minimal config is two lines:\n"
            f'  brand        = "{humanise(here.name)}"\n'
            f'  title_suffix = "{humanise(here.name)}"'
        )
    return SiteConfig(
        name=raw.get("name") or here.name,
        base=here,
        source=here / raw.get("source", "markdown"),
        output=here / raw.get("output", "html"),
        style=(here / raw["style"]) if "style" in raw else BUNDLED_STYLE,
        brand=raw["brand"],
        title_suffix=raw["title_suffix"],
        titles=raw.get("titles", {}),
        badges=_badge_styles(raw.get("badges")),
        order=raw.get("order"),
        standalone=raw.get("standalone", []),
        concat=raw.get("concat"),
    )


# --------------------------------------------------------------------------- build


def _link_dirs(site: SiteConfig) -> LinkDirs:
    """The ``(source, output)`` directory names used to repoint cross-set links.

    A **flat** doc set — markdown sitting directly in the set's own directory, with
    ``source = "."`` — has no source subdirectory for such a link to route through. Its
    directory name is not a safe marker either: passing it would rewrite *any* link
    containing that word, including one pointing somewhere unrelated. So rewriting is
    switched off, by naming a segment that cannot occur in a path.
    """
    if site.source == site.base:
        return ("\x00", "\x00")
    return (site.source.name, site.output.name)


def site_pages(site: SiteConfig) -> dict[Path, Path]:
    """Every page one doc set builds, standalone pages included: source → output."""
    found = {
        (site.source / f"{slug}.md").resolve(): (site.output / f"{slug}.html").resolve()
        for slug, _ in discover_pages(site.source)
    }
    for spec in site.standalone:
        found[(site.base / spec["source"]).resolve()] = (
            site.base / spec["output"]
        ).resolve()
    return found


def build_site(
    site: SiteConfig, project_pages: Mapping[Path, Path] | None = None
) -> None:
    """Render one doc set: its pages, its standalone pages, and its concatenation.

    ``project_pages`` is every page in the project (see ``site_pages``), so links into
    other doc sets resolve. Without it, only this set's own pages are known.
    """
    pages = discover_pages(site.source, site.titles, site.order)
    sources = read_sources(site.source, pages)
    style = site.style.read_text()
    link_dirs = _link_dirs(site)
    known = site_pages(site) if project_pages is None else project_pages
    targets = LinkTargets(known, site.source.resolve(), site.output.resolve())
    # Render every page *before* touching the directory, so a failure part-way through
    # can never leave the docs deleted and not replaced.
    rendered = {
        f"{slug}.html": page_shell(
            pages,
            index,
            slug,
            title,
            md_to_html(sources[slug], link_dirs, site.badges, targets),
            style,
            site.brand,
            site.title_suffix,
        )
        for index, (slug, title) in enumerate(pages)
    }
    removed = write_pages(site.output, rendered)
    report(len(pages), site.output, removed)

    for spec in site.standalone:
        source = site.base / spec["source"]
        if not source.exists():
            continue
        out = site.base / spec["output"]
        out.write_text(
            standalone_page(
                spec["title"],
                spec.get("brand", site.brand),
                spec.get("brand_href", ""),
                source.read_text(),
                style,
                link_dirs,
                site.badges,
                LinkTargets(known, source.parent.resolve(), out.parent.resolve()),
            )
        )
        print(f"Built standalone page {out}")

    if site.concat:
        out = site.base / site.concat["output"]
        # How far the concatenated file sits from the sources, which is exactly how far
        # every relative link inside it has to move. See ``concat_links``.
        prefix = os.path.relpath(site.source, out.parent)
        slugs = {slug for slug, _ in pages}
        anchors = {slug: anchor(first_h1(md)) for slug, md in sources.items()}
        parts = [
            concat_links(sources[slug], anchors, slugs, prefix) for slug, _ in pages
        ]
        src = site.source.name
        banner = (
            f"<!-- Generated from {src}/*.md by docsbuild — do not edit by hand.\n"
            f"     Edit the sources under {src}/ and run:\n"
            f"     {site.concat['command']} -->"
        )
        body = "\n\n---\n\n".join(p.strip() for p in parts)
        out.write_text(f"{banner}\n\n{body}\n")
        print(f"Built the concatenated file into {out}")


# ---------------------------------------------------------------- detection & init


@dataclass(frozen=True)
class DetectedSet:
    """A doc set found by looking for markdown, before any config exists for it."""

    name: str  # its directory name, or "" for a set at the scanned root itself
    directory: Path
    source: str  # "markdown" for the nested layout, "." for a flat one
    pages: int


# Directories that hold other people's markdown, not yours. A vendored tree can carry
# thousands of files, and a cache directory's own README is not documentation. The dot
# rule covers .git, .venv, .tox and .pytest_cache; these are the common non-dot cases.
SKIP_DIRS = frozenset(
    {
        "node_modules",
        "__pycache__",
        "venv",
        "dist",
        "build",
        "target",
        "vendor",
        "site-packages",
        "htmlcov",
    }
)

# Where documentation conventionally lives inside a repository, in preference order.
DOCS_DIR_NAMES = ("docs", "doc", "documentation")


def _scannable(directory: Path) -> bool:
    """Whether a directory is worth looking inside for documentation."""
    return (
        directory.is_dir()
        and not directory.name.startswith(".")
        and directory.name not in SKIP_DIRS
    )


def _subdirs(directory: Path) -> list[Path]:
    """The children of *directory* worth scanning, in name order."""
    if not directory.is_dir():
        return []
    return [child for child in sorted(directory.iterdir()) if _scannable(child)]


def _markdown_count(directory: Path) -> int:
    return len(list(directory.glob("*.md")))


def _as_set(directory: Path, name: str) -> DetectedSet | None:
    """Read one directory as a doc set, or ``None`` if it is not one.

    Same three-way choice as ``detect_sets``, one level down. In particular a directory
    that *contains* doc sets is a container and not itself a set: ``docs/`` holding a
    loose ``CONFIGURATION.md`` beside two real sets must not be read as a one-page set,
    because that is precisely what hides the sets beneath it.
    """
    if nested := _markdown_count(directory / "markdown"):
        return DetectedSet(name, directory, "markdown", nested)
    if any(_holds_sets(child) for child in _subdirs(directory)):
        return None
    if flat := _markdown_count(directory):
        return DetectedSet(name, directory, ".", flat)
    return None


def _holds_sets(directory: Path) -> bool:
    """Whether *directory* is itself a doc set — one level of look-ahead, no deeper."""
    return bool(_markdown_count(directory / "markdown") or _markdown_count(directory))


def detect_sets(root: Path) -> list[DetectedSet]:
    """The doc sets under *root*, found from the markdown rather than from config.

    This is what lets ``init`` scaffold a project that has never used this tool, and
    what lets the "no config" errors name the sets they can see. Both share it, so the
    scaffolder and the error messages can never disagree about what a doc set is.

    Three rules, in this order:

    1. ``root/markdown/`` exists -> *root* is the set, and it is the only one.
    2. Otherwise every subdirectory holding markdown is a set.
    3. Otherwise loose ``*.md`` at *root* make it a single flat set.

    Rule 1 returns exclusively because the config format requires it, not as a
    preference: ``sites.toml`` names sets by *subdirectory*, so a set at the root cannot
    be listed in an index sitting in that same directory. A project cannot mix the two,
    so detection has to choose, and an explicit ``markdown/`` says which.

    Rule 3 comes **last** on purpose. A docs root commonly holds a loose ``.md`` — a
    README, a changelog, a reference page kept outside the reading chain — and treating
    that as "the root is a one-page doc set" would hide every real set beneath it.
    """
    if nested := _markdown_count(root / "markdown"):
        return [DetectedSet("", root, "markdown", nested)]

    children = (_as_set(child, child.name) for child in _subdirs(root))
    if found := [s for s in children if s is not None]:
        return found

    if flat := _markdown_count(root):
        return [DetectedSet("", root, ".", flat)]
    return []


def _configured(directory: Path) -> bool:
    """Whether *directory* already holds a doc project's config."""
    return (directory / "sites.toml").exists() or (directory / "site.toml").exists()


def find_docs_root(start: Path) -> Path:
    """*start*, or the conventional documentation directory inside it.

    Lets both ``init`` and the build run from a repository root — where people naturally
    run things — without the tool searching a whole tree. Config already sitting in
    *start* settles it; otherwise the first of ``docs/``, ``doc/`` or ``documentation/``
    that holds config or doc sets is used, and failing that *start* comes back unchanged
    for the caller to complain about.

    Note the conventional directory is checked *before* asking whether *start* itself
    holds sets. A repository root very often has a stray ``README.md`` in some
    subdirectory, which would otherwise look like a doc set and stop the real ``docs/``
    tree from ever being considered.
    """
    start = start.resolve()
    if _configured(start):
        return start
    for name in DOCS_DIR_NAMES:
        candidate = start / name
        if candidate.is_dir() and (_configured(candidate) or detect_sets(candidate)):
            return candidate
    return start


_BADGE_IN_ITEM = re.compile(r"^\s*[-*+]\s+\[([A-Z][A-Z0-9_]*)\]\s")


def scan_badge_tokens(source: Path) -> list[str]:
    """Badge-shaped tokens used in *source*, most frequent first, ties broken by name.

    Applies the same rule the renderer does — a bracketed capitalised word at the head
    of a list item — so what ``init`` writes is exactly what will render. Fenced code is
    skipped: a fenced example of the syntax is documentation, not a declaration.
    """
    counts: dict[str, int] = {}
    for path in sorted(source.glob("*.md")):
        fenced = False
        for line in path.read_text().split("\n"):
            if line.lstrip().startswith("```"):
                fenced = not fenced
            elif not fenced and (match := _BADGE_IN_ITEM.match(line)):
                counts[match.group(1)] = counts.get(match.group(1), 0) + 1
    return sorted(counts, key=lambda token: (-counts[token], token))


def humanise(name: str) -> str:
    """A directory name as a readable label: ``development-plans`` -> ``Development
    Plans``."""
    return re.sub(r"[-_]+", " ", name).strip().title()


def _describe(sets: Sequence[DetectedSet]) -> str:
    """The detected sets, for an error message that points at ``docsbuild init``."""
    names = ", ".join(s.name or s.directory.name for s in sets)
    return (
        f"found markdown but no config ({names}).\n"
        "Run `docsbuild init` here to write one."
    )


def _build_command(set_name: str) -> str:
    """The command that builds this set — bare when it is the project's only one."""
    return f"docsbuild --set {set_name}" if set_name else "docsbuild"


def _site_toml(
    project: str,
    label: str,
    source: str,
    set_name: str,
    tokens: Sequence[str] = (),
) -> str:
    """The scaffolded config for one doc set.

    Beyond the two required keys it carries a commented, filled-in example of each
    optional block, with a note on what the block actually does. Someone editing this
    file should not have to go and find the README to learn what is available.

    Everything past the required keys is a comment. Nothing here may parse as live
    configuration, or scaffolding would silently switch on a feature nobody asked for.
    """
    brand = f"{project} · {label}" if project else label
    suffix = f"{project} {label}" if project else label
    name = set_name or "all"
    # A set in a subdirectory reaches a shared page one level up; a set at the project
    # root is already there. Getting this wrong makes the example point outside the
    # project, which is worse than showing no example at all.
    up = "../" if set_name else ""
    lines = [
        "# Written by `docsbuild init`. The two brand strings are a guess from the",
        "# directory names — edit them.",
        "",
        f'brand        = "{brand}"',
        f'title_suffix = "{suffix}"',
    ]
    if source != "markdown":  # only write it when it differs from the default
        lines.append(f'source       = "{source}"')
    lines += [
        "",
        "# --- Optional. Uncomment and edit what you need. ---------------------------",
        "#",
        "# Prose below never starts a line with a bracket, so uncommenting whole",
        "# example blocks is safe — only real config lines look like config.",
        "",
        "# Sidebar labels: override the name a page gets in the contents list, for",
        "# when it should read differently there than the page's own `# heading`",
        "# does. Only the pages you list change; every other page keeps its heading.",
        "#",
        "# [titles]",
        '# index = "Overview & contents"',
        "",
        "# One file with everything in it: also write every page into a single file,",
        "# in reading order, with links between pages becoming in-document anchors so",
        "# it reads top to bottom. Useful for diffing a whole document in one place,",
        "# or handing it to a tool in one read. Generated — never edit the result.",
        "#",
        "# [concat]",
        f'# output  = "{name}.md"',
        f'# command = "{_build_command(set_name)}"',
        "",
        "# A page outside the reading chain: rendered with an index of its own `##`",
        "# sections instead of previous/next buttons. Good for a reference or",
        "# configuration page that is not part of the tour. Add one block per page;",
        "# a missing source file is skipped rather than failing the build.",
        "#",
        "# [[standalone]]",
        f'# source = "{up}REFERENCE.md"',
        f'# output = "{up}REFERENCE.html"',
        '# title  = "Reference"',
        "",
        "# Status badges: a declared token at the head of a list item becomes a",
        "# coloured pill, so a document can mark finished work without deleting it.",
        "# Opt-in — with no table here, every bracketed word stays plain text. A bare",
        "# string is the label, and the pill's colour comes from the lowercased token;",
        "# the table form lets a token borrow another's colour.",
        f"# Styles the bundled stylesheet defines: {', '.join(BADGE_STYLES)}.",
    ]
    if tokens:
        # Tokens were found in this set's markdown, so write a live table rather than a
        # commented one. Otherwise the build would silently render every existing badge
        # as plain text, with nothing here to suggest why.
        lines += ["#", "[badges]"]
        width = max(len(token) for token in tokens)
        lines += [f'{token.ljust(width)} = "{humanise(token)}"' for token in tokens]
    else:
        lines += [
            "#",
            "# [badges]",
            '# DONE  = "Done"',
            '# BUILT = { label = "Built", style = "done" }',
        ]
    return "\n".join(lines) + "\n"


def _optional_blocks_note(sets: Sequence[DetectedSet]) -> str:
    """The closing report: what the optional blocks are, and one worked example.

    A summary line each keeps this short — the configs just written carry the full
    explanation and an example of all three. The one block shown here is filled in for a
    real detected set, so it is copy-paste correct rather than a placeholder.
    """
    example = sets[0].name if sets else ""
    return "\n".join(
        [
            "Optional blocks — fuller notes are in each config that was written:",
            "",
            "  [titles]         sidebar label for a page, when it should differ from",
            "                   that page's own `# heading`",
            "  [concat]         also write every page into one file, in reading order",
            "  [[standalone]]   render a page outside the reading chain, with its own",
            "                   section index instead of previous/next buttons",
            "",
            "  [concat]",
            f'  output  = "{example or "all"}.md"',
            f'  command = "{_build_command(example)}"',
            "",
            "To reproduce another project's docs exactly, copy its site.toml files —",
            "brand strings and these blocks are not inferable from the filesystem.",
        ]
    )


def _project_name(root: Path) -> str:
    """A guess at the project's name, for the brand prefix.

    The directory above the docs root is usually the checkout, so ``acme/docs`` gives
    ``acme``. Returns "" when there is nothing sensible above, leaving the label alone.
    """
    parent = root.resolve().parent
    return "" if parent == parent.parent else parent.name


def init_project(root: Path, force: bool = False) -> None:
    """Write a ``site.toml`` for every doc set under *root*, and an index if plural.

    Existing config is kept, not overwritten, unless *force* is set: quietly replacing a
    hand-tuned config would be worse than not scaffolding at all.
    """
    given = root.resolve()
    # Accept a repository root and work out where the documentation really lives, so
    # config lands beside the sets it names, not scattered at the top of the repo.
    root = find_docs_root(given)
    if root != given:
        print(f"Using {root.relative_to(given)}/ as the docs root.\n")

    sets = detect_sets(root)
    if not sets:
        raise SystemExit(
            f"no markdown found in {root} or its subdirectories — "
            "nothing to configure here"
        )

    print(f"Detected {len(sets)} doc set(s) in {root}:")
    for spec in sets:
        layout = "flat" if spec.source == "." else "markdown/"
        print(f"  {spec.name or '.':<24} {spec.pages:>3} pages   ({layout})")
    print()

    # Loose markdown at the root is not a doc set when real sets were found beneath it
    # (see ``detect_sets``). Saying so beats leaving the file silently unbuilt, and
    # ``[[standalone]]`` is usually what such a page actually wants.
    skipped = (
        sorted(p.name for p in root.glob("*.md")) if any(s.name for s in sets) else []
    )
    if skipped:
        print(
            f"Note: {', '.join(skipped)} at the top level is not a doc set.\n"
            "      If it should be a page of one of these, add a [[standalone]]\n"
            "      entry to that set's config.\n"
        )

    project = _project_name(root)
    written: list[Path] = []
    kept: list[Path] = []
    unstyled: list[str] = []
    for spec in sets:
        path = spec.directory / "site.toml"
        if path.exists() and not force:
            kept.append(path)
            continue
        label = humanise(spec.name) if spec.name else humanise(root.name)
        tokens = scan_badge_tokens(spec.directory / spec.source)
        unstyled += [t for t in tokens if t.lower() not in BADGE_STYLES]
        path.write_text(_site_toml(project, label, spec.source, spec.name, tokens))
        written.append(path)

    # An index is needed whenever the sets live in *subdirectories*, whatever their
    # number: it is what tells the build where to look. Only a set at the root itself
    # can do without one, because then its site.toml already sits at the root.
    unlisted: list[str] = []
    if any(spec.name for spec in sets):
        index = root / "sites.toml"
        if index.exists() and not force:
            kept.append(index)
            # An existing index is kept rather than merged, because a set may have been
            # left out of it deliberately. But silence would be a trap: a newly added
            # set would get a config and still never build. So name the difference.
            with index.open("rb") as fh:
                listed = tomllib.load(fh).get("sets", [])
            unlisted = [s.name for s in sets if s.name not in listed]
        else:
            names = ", ".join(f'"{s.name}"' for s in sets)
            index.write_text(
                "# The doc sets in this project, in the order `--all` builds them.\n"
                f"sets = [{names}]\n"
            )
            written.append(index)

    for path in written:
        print(f"Wrote {path.relative_to(root)}")
    for path in kept:
        print(f"Kept  {path.relative_to(root)} (already existed; --force to replace)")

    if unstyled:
        # Guessing a colour would be worse than saying nothing: the token's meaning is
        # the project's, and picking one at random would look deliberate.
        names = ", ".join(sorted(set(unstyled)))
        print(
            f"\nNote: {names} has no matching style in the bundled stylesheet, so it\n"
            f"      renders as an unstyled pill. Add CSS for it, or point it at\n"
            f"      one of: {', '.join(BADGE_STYLES)} — e.g.\n"
            f'        BUILT = {{ label = "Built", style = "done" }}'
        )

    if unlisted:
        print(
            f"\nNote: {', '.join(unlisted)} not listed in sites.toml, so `--all` will "
            "skip it.\n      Add it to `sets` there if you want it built."
        )

    print("\nEdit the brand strings, then build:")
    print("  docsbuild")
    print()
    print(_optional_blocks_note(sets))


# ------------------------------------------------------------------ root discovery


def find_root(start: Path) -> Path:
    """The nearest directory at or above *start* that holds a doc project.

    A project is marked by a ``sites.toml`` (several doc sets) or a ``site.toml`` (just
    one). Searching upwards means the command works from anywhere inside the tree, the
    way ``git`` does, rather than only from the directory holding the config.

    At each level the search also glances *down* into a conventional documentation
    directory, so running from a repository root — or from a sibling of ``docs/`` —
    finds the project too. Config sitting at a level always beats a ``docs/`` inside
    it, and a nearer level always beats a farther one.
    """
    start = start.resolve()
    for candidate in (start, *start.parents):
        if _configured(candidate):
            return candidate
        for name in DOCS_DIR_NAMES:
            if _configured(candidate / name):
                return candidate / name
    if sets := detect_sets(start):
        raise SystemExit(f"{start}: {_describe(sets)}")
    raise SystemExit(
        f"no sites.toml or site.toml in {start} or any parent directory — "
        "run this inside a docs project, or pass --root/--config"
    )


def site_configs(root: Path, only: str | None = None) -> list[Path]:
    """The config files to build under *root*.

    A project with several doc sets lists them in ``sites.toml``. A project with one
    needs no index at all — its ``site.toml`` is the whole configuration.
    """
    index = root / "sites.toml"
    if index.exists():
        with index.open("rb") as fh:
            names = tomllib.load(fh).get("sets", [])
        if only is not None:
            if only not in names:
                raise SystemExit(f"unknown set {only!r}; sites.toml lists {names}")
            names = [only]
        return [root / name / "site.toml" for name in names]

    single = root / "site.toml"
    if single.exists():
        if only is not None and only != root.name:
            raise SystemExit(f"unknown set {only!r}; {root} holds a single doc set")
        return [single]

    if sets := detect_sets(root):
        raise SystemExit(f"{root}: {_describe(sets)}")
    raise SystemExit(f"no sites.toml or site.toml under {root}")


def _init_cli(argv: Sequence[str]) -> None:
    """``docsbuild init`` — scaffold config for a project that has markdown but none."""
    parser = argparse.ArgumentParser(
        prog="docsbuild init",
        description="Write a site.toml for each doc set found, so the project builds.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="directory to scan (default: the working directory)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace existing config instead of keeping it",
    )
    args = parser.parse_args(argv)
    init_project(args.root or Path.cwd(), args.force)


def main(argv: Sequence[str] | None = None) -> None:
    """Build the doc set or sets selected on the command line.

    With no arguments at all, the project is discovered from the working directory and
    everything in it is built — the common case, and the only one a single-set project
    ever needs. ``docsbuild init`` scaffolds config for a project that has none yet.

    ``init`` is matched as a leading word rather than an argparse subparser, because
    subparsers would force every other caller to write ``docsbuild build --all``, and a
    bare ``docsbuild`` that needs no arguments is the point of the design.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "init":
        return _init_cli(argv[1:])

    parser = argparse.ArgumentParser(
        prog="docsbuild",
        description="Build markdown doc sets into self-contained HTML sites. "
        "Run `docsbuild init` in a project that has no config yet.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="project directory holding sites.toml or site.toml "
        "(default: found by searching upwards from the working directory)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all", action="store_true", help="build every set (the default)"
    )
    group.add_argument("--set", dest="only", help="build one named set")
    group.add_argument("--config", type=Path, help="build one site.toml directly")
    args = parser.parse_args(argv)

    if args.config:
        configs = project = [args.config]
    else:
        # An explicit --root is taken at its word rather than searched upward from,
        # but may still name a repo root whose docs live in a `docs/` subdirectory.
        root = find_docs_root(args.root) if args.root else find_root(Path.cwd())
        configs = site_configs(root, args.only)
        # Even when building one set, a link may lead into any of them.
        project = site_configs(root)
    project_pages: dict[Path, Path] = {}
    for path in project:
        project_pages.update(site_pages(load_site(path)))
    for path in configs:
        build_site(load_site(path), project_pages)


if __name__ == "__main__":  # pragma: no cover
    main()
