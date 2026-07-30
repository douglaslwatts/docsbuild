"""Invariants asserted across a corpus of real markdown.

The other test modules check specific behaviours against small hand-written inputs. This
one does something different and complementary: it runs 39 real documents — 200 KB of
prose written without any thought for this converter — through the renderer and asserts
properties that must hold for *every* page.

Why it exists: two rendering defects shipped and were found by eye, in output, weeks
later. A third (images rendering as `!<a href=...>`) survived even a deliberate audit of
the converter's limits, because nobody thought to write an image. Invariants catch that
class of bug mechanically, without anyone reading a page.

It asserts *invariants*, never exact HTML. That is deliberate: the converter's markup is
expected to change — a markdown library may replace it — and this harness has to survive
that, so it can be the thing which verifies the migration.

Known defects are marked ``xfail(strict=True)``. Strict matters: an xfail that quietly
starts passing would leave the harness asserting nothing, so a fix must announce itself
by failing the run until the marker is removed.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

import docsbuild

CORPUS = sorted((Path(__file__).parent / "corpus").rglob("*.md"))

# A guard on the harness itself: if the corpus is ever emptied or moved, every test
# below would vacuously pass. Fail loudly instead.
assert len(CORPUS) >= 30, f"corpus looks wrong: {len(CORPUS)} files"


def _ids(paths: list[Path]) -> list[str]:
    return [f"{p.parent.name}/{p.name}" for p in paths]


@pytest.fixture(params=CORPUS, ids=_ids(CORPUS))
def page(request: pytest.FixtureRequest) -> tuple[Path, str]:
    """One corpus document, with its rendered HTML."""
    path: Path = request.param
    return path, docsbuild.md_to_html(path.read_text())


# --------------------------------------------------------------- stripping code out


_CODE = re.compile(r"<pre>.*?</pre>|<code>.*?</code>", re.DOTALL)


def _prose(html: str) -> str:
    """The rendered HTML with code blocks and spans removed.

    Literal markdown in backticks is intentional — a page may well write ``**bold**`` to
    show what bold looks like. Only markup leaking into *prose* is a defect.
    """
    return _CODE.sub(" ", html)


# ------------------------------------------------------------------- markup leakage


def test_no_unrendered_bold_markers(page: tuple[Path, str]) -> None:
    """Leaked `**` is the signature of the wrapped-bullet bug that shipped once."""
    _, html = page

    assert "**" not in _prose(html)


def test_no_unrendered_link_syntax(page: tuple[Path, str]) -> None:
    """`](` reaching the output means a link form the converter does not understand."""
    _, html = page

    assert "](" not in _prose(html)


def test_no_stray_bang_before_a_link(page: tuple[Path, str]) -> None:
    """An image rendered as a link leaves its `!` behind as visible punctuation."""
    _, html = page

    assert not re.search(r"!\s*<a ", _prose(html))


def test_every_markdown_link_became_html(page: tuple[Path, str]) -> None:
    """Links are authored as `.md` so they work on GitHub; the build rewrites them."""
    _, html = page

    assert not re.search(r'href="[^"]*\.md"', html)


# ------------------------------------------------------------------- well-formedness


class _Wellformed(HTMLParser):
    """Checks tags nest and close correctly, using only the standard library."""

    VOID = frozenset({"br", "hr", "img", "meta", "link", "input"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID:
            return
        if not self.stack:
            self.errors.append(f"</{tag}> with nothing open")
        elif self.stack[-1] != tag:
            self.errors.append(f"</{tag}> closes <{self.stack[-1]}>")
            self.stack.pop()
        else:
            self.stack.pop()


def test_output_is_well_formed(page: tuple[Path, str]) -> None:
    """Every tag opened is closed, in order. Malformed markup renders unpredictably."""
    _, html = page

    checker = _Wellformed()
    checker.feed(html)

    assert checker.errors == []
    assert checker.stack == [], f"never closed: {checker.stack}"


def _heading_lines(source: str) -> int:
    """Count `#` headings, skipping fenced code.

    A shell or TOML block full of `# comment` lines is not a run of headings — and the
    converter is right to leave them alone. Counting them was a bug in this test.
    """
    count, in_fence = 0, False
    for line in source.split("\n"):
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence and re.match(r"#{1,6}\s+\S", line):
            count += 1
    return count


def test_headings_survive_as_headings(page: tuple[Path, str]) -> None:
    """Every `#` line outside a code fence has to become a heading element."""
    path, html = page
    expected = _heading_lines(path.read_text())

    found = len(re.findall(r"<h[1-6][ >]", html))

    assert found == expected


# ----------------------------------------------------------- formerly wrong output
#
# Four cases that used to produce *wrong* output rather than merely unsupported output.
# Each was first written here as the assertion it should satisfy, marked
# xfail(strict=True), and each announced its own fix by reporting XPASS(strict) until
# the marker came off. They stay as ordinary regression tests.


def test_nested_lists_are_not_flattened() -> None:
    """An indented child item is absorbed into its parent, keeping its literal marker.

    Indentation currently means only "continuation of this item"; it must also mean
    "child list" when the indented line carries a list marker.
    """
    html = docsbuild.md_to_html("- top\n  - child\n- next")

    assert html.count("<ul>") == 2, html
    assert "top - child" not in html


def test_images_render_as_images() -> None:
    """`![alt](src)` produces a link preceded by a stray `!` instead of an `<img>`."""
    html = docsbuild.md_to_html("![A diagram](diagram.png)")

    assert '<img src="diagram.png"' in html
    assert "!<a" not in html


def test_italics_nested_inside_bold() -> None:
    """The bold pattern refuses inner asterisks, so the `**` leaks into the page."""
    html = docsbuild.md_to_html("**bold with *inner* text**")

    assert "**" not in html
    assert "<strong>" in html and "<em>" in html


def test_table_column_alignment_is_honoured() -> None:
    """`:---:` is accepted as a separator, then discarded rather than applied."""
    html = docsbuild.md_to_html("| L | C |\n|:---|:--:|\n| a | b |")

    assert "text-align:left" in html.replace(" ", "")
    assert "text-align:center" in html.replace(" ", "")
