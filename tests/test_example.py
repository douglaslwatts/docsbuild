"""This project's own documentation must actually build.

Two artifacts of ours are rendered by the tool itself: the bundled `example/` project,
and the onboarding guide in `docs/`. A README can drift from the code without anyone
noticing; these cannot, because they are built on every test run.

Both are copied into a temporary directory first, so running the tests never dirties the
repository or leaves stale output behind.

The onboarding guide claims, in its own text, that a change breaking the build stops
those pages rendering. `test_the_onboarding_guide_builds` is what makes that claim true
rather than aspirational — otherwise nobody finds out until they next build by hand.
"""

import shutil
from pathlib import Path

import docsbuild

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "example"
DOCS = ROOT / "docs"


def test_the_example_project_builds(tmp_path: Path) -> None:
    """Copied anywhere and built with no arguments, exactly as the README claims."""
    project = tmp_path / "example"
    shutil.copytree(EXAMPLE, project)

    docsbuild.main(["--root", str(project)])

    built = sorted(p.name for p in (project / "html").glob("*.html"))
    assert built == ["01-writing-pages.html", "02-configuring.html", "index.html"]


def test_the_example_needs_no_stylesheet_of_its_own(tmp_path: Path) -> None:
    """Its site.toml has no `style` key, so the bundled sheet has to carry it."""
    project = tmp_path / "example"
    shutil.copytree(EXAMPLE, project)
    assert not (project / "style.css").exists()

    docsbuild.main(["--root", str(project)])

    assert ".layout" in (project / "html" / "index.html").read_text()


def test_the_example_pages_are_in_reading_order(tmp_path: Path) -> None:
    """`index` first despite sorting last alphabetically, then filename order."""
    project = tmp_path / "example"
    shutil.copytree(EXAMPLE, project)

    pages = docsbuild.discover_pages(project / "markdown")

    assert [slug for slug, _ in pages] == [
        "index",
        "01-writing-pages",
        "02-configuring",
    ]


def test_the_example_documents_the_real_badge_list(tmp_path: Path) -> None:
    """The badges page claims a specific set of tokens; they must all still render."""
    project = tmp_path / "example"
    shutil.copytree(EXAMPLE, project)

    docsbuild.main(["--root", str(project)])

    html = (project / "html" / "01-writing-pages.html").read_text()
    assert html.count('<span class="badge') == 3


# ------------------------------------------------------- this project's own guide


def test_the_onboarding_guide_builds(tmp_path: Path) -> None:
    """Dogfooding, enforced. The guide is rendered by the tool it documents."""
    docs = tmp_path / "docs"
    shutil.copytree(DOCS, docs, ignore=shutil.ignore_patterns("html"))

    docsbuild.main(["--root", str(docs)])

    built = sorted(p.name for p in (docs / "onboarding" / "html").glob("*.html"))
    sources = sorted(
        f"{p.stem}.html" for p in (DOCS / "onboarding" / "markdown").glob("*.md")
    )
    assert built == sources


def test_every_link_in_the_guide_resolves(tmp_path: Path) -> None:
    """A cross-reference to a page that does not exist is the guide's likeliest rot."""
    import re

    docs = tmp_path / "docs"
    shutil.copytree(DOCS, docs, ignore=shutil.ignore_patterns("html"))
    docsbuild.main(["--root", str(docs)])

    dead = [
        f"{page.name} -> {href}"
        for page in sorted((docs / "onboarding" / "html").glob("*.html"))
        for href in re.findall(r'href="([^"#]+)"', page.read_text())
        if not href.startswith(("http", "mailto:"))
        and not (page.parent / href).resolve().exists()
    ]

    assert dead == []


def test_the_guide_has_no_leaked_markup(tmp_path: Path) -> None:
    """The same invariants the corpus asserts, applied to our own prose."""
    import re

    docs = tmp_path / "docs"
    shutil.copytree(DOCS, docs, ignore=shutil.ignore_patterns("html"))
    docsbuild.main(["--root", str(docs)])

    for page in sorted((docs / "onboarding" / "html").glob("*.html")):
        body = re.search(r"<article>(.*?)</article>", page.read_text(), re.S)
        assert body is not None, page.name
        prose = re.sub(
            r"<pre>.*?</pre>|<code>.*?</code>", " ", body.group(1), flags=re.S
        )
        assert "**" not in prose, page.name
        assert "](" not in prose, page.name
