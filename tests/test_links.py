"""Tests for where links point once a page is built.

Two rules meet here. A link to a *page* — any page the project builds, in this doc set,
another one, or a standalone page — must point at that page's ``.html``, keeping any
``#section`` after it. A link to a ``.md`` file that is *not* a page, such as a README
outside the docs, must keep pointing at that file. Heading ids follow GitHub's style, so
a ``#section`` written to work on GitHub lands on the same heading in the built site.
"""

from pathlib import Path
from types import ModuleType

import pytest

import docsbuild


@pytest.fixture
def db() -> ModuleType:
    return docsbuild


# ----------------------------------------------------------------- section links


def test_a_section_link_keeps_its_fragment(db: ModuleType) -> None:
    out = db.md_to_html("see [questions](02-status.md#open-questions)")

    assert 'href="02-status.html#open-questions"' in out


def test_a_cross_set_section_link_keeps_its_fragment(db: ModuleType) -> None:
    out = db.md_to_html("[x](../../onboarding/markdown/04-wake-word.md#setup)")

    assert 'href="../../onboarding/html/04-wake-word.html#setup"' in out


def test_heading_ids_follow_github_style(db: ModuleType) -> None:
    """GitHub keeps one hyphen per space, so dropped punctuation leaves a double one."""
    out = db.md_to_html("## Notes, lists & to-dos\n\n## `code` and **bold**")

    assert '<h2 id="notes-lists--to-dos">' in out
    assert '<h2 id="code-and-bold">' in out


def test_the_section_index_uses_the_same_ids_as_the_headings(db: ModuleType) -> None:
    assert db.h2_headings("## Notes, lists & to-dos") == [
        ("notes-lists--to-dos", "Notes, lists & to-dos")
    ]


def test_concat_turns_a_section_link_into_that_sections_anchor(db: ModuleType) -> None:
    """Every page is inlined in the single file, so the section's anchor is there."""
    out = db.concat_links(
        "[x](02-status.md#open-questions)",
        {"02-status": "where-it-stands"},
        {"02-status"},
    )

    assert out == "[x](#open-questions)"


def test_concat_rebases_a_section_link_to_another_set(db: ModuleType) -> None:
    out = db.concat_links("[x](../../onboarding/markdown/04-a.md#setup)", {}, set())

    assert out == "[x](../onboarding/markdown/04-a.md#setup)"


# ------------------------------------------------------- only pages become .html


def _page(path: Path, body: str = "Body text.") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {path.stem}\n\n{body}\n")


def _project(root: Path) -> Path:
    """A repository with a README beside docs/, two doc sets and a standalone page."""
    (root / "README.md").write_text("# Readme\n")
    docs = root / "docs"
    (docs / "sites.toml").parent.mkdir(parents=True)
    (docs / "sites.toml").write_text('sets = ["guide", "plan"]\n')
    for name in ("guide", "plan"):
        (docs / name / "site.toml").parent.mkdir(parents=True)
    (docs / "guide" / "site.toml").write_text(
        'brand = "B"\ntitle_suffix = "T"\n\n[[standalone]]\n'
        'source = "../CONFIG.md"\noutput = "../CONFIG.html"\ntitle = "Config"\n'
    )
    (docs / "plan" / "site.toml").write_text('brand = "B"\ntitle_suffix = "T"\n')
    _page(docs / "CONFIG.md", "[guide](guide/markdown/index.md)")
    _page(
        docs / "guide" / "markdown" / "index.md",
        "[readme](../../../README.md) [config](../../CONFIG.md)"
        " [plan](../../plan/markdown/index.md#later)",
    )
    _page(
        docs / "plan" / "markdown" / "index.md",
        "[guide](../../guide/markdown/index.md)",
    )
    return docs


def test_a_link_to_markdown_that_is_not_a_page_still_points_at_the_file(
    db: ModuleType, tmp_path: Path
) -> None:
    """A README outside the docs is never built, so ``README.html`` would be dead."""
    docs = _project(tmp_path)

    db.main(["--root", str(docs)])

    html = (docs / "guide" / "html" / "index.html").read_text()
    assert 'href="../../../README.md"' in html


def test_a_link_to_a_standalone_page_points_at_its_html(
    db: ModuleType, tmp_path: Path
) -> None:
    docs = _project(tmp_path)

    db.main(["--root", str(docs)])

    html = (docs / "guide" / "html" / "index.html").read_text()
    assert 'href="../../CONFIG.html"' in html


def test_a_standalone_pages_own_links_point_at_pages(
    db: ModuleType, tmp_path: Path
) -> None:
    docs = _project(tmp_path)

    db.main(["--root", str(docs)])

    assert 'href="guide/html/index.html"' in (docs / "CONFIG.html").read_text()


def test_building_one_set_still_knows_the_other_sets_pages(
    db: ModuleType, tmp_path: Path
) -> None:
    """``--set`` builds one set, but its links reach pages of the whole project."""
    docs = _project(tmp_path)

    db.main(["--root", str(docs), "--set", "plan"])

    html = (docs / "plan" / "html" / "index.html").read_text()
    assert 'href="../../guide/html/index.html"' in html
    assert not (docs / "guide" / "html").exists()


def test_a_cross_set_section_link_resolves_in_a_real_build(
    db: ModuleType, tmp_path: Path
) -> None:
    docs = _project(tmp_path)

    db.main(["--root", str(docs)])

    html = (docs / "guide" / "html" / "index.html").read_text()
    assert 'href="../../plan/html/index.html#later"' in html


def test_a_flat_set_links_a_file_outside_it_from_its_output_directory(
    db: ModuleType, tmp_path: Path
) -> None:
    """Flat pages sit one level above ``html/``, so a non-page link gains a ``..``."""
    (tmp_path / "README.md").write_text("# Readme\n")
    guide = tmp_path / "guide"
    _page(guide / "index.md", "[readme](../README.md)")
    (guide / "site.toml").write_text('brand = "B"\ntitle_suffix = "T"\nsource = "."\n')

    db.main(["--config", str(guide / "site.toml")])

    html = (guide / "html" / "index.html").read_text()
    assert 'href="../../README.md"' in html


def test_a_markdown_url_on_another_site_is_left_alone(db: ModuleType) -> None:
    """Only relative links can be pages of this project."""
    out = db.md_to_html("[x](https://example.com/README.md)")

    assert 'href="https://example.com/README.md"' in out


def test_a_set_with_no_source_directory_leaves_other_links_alone(
    db: ModuleType,
) -> None:
    """With no source directory name there is nothing to repoint."""
    out = db.md_to_html("[x](assets/diagram.png)", ("\x00", "\x00"))

    assert 'href="assets/diagram.png"' in out
