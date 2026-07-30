"""Tests for the build layer: page chrome, standalone pages, and failure reporting.

These cover the parts of the program that turn converted markdown into files on disk.
They were untested for a long time because the converter carried all the attention —
this is where the ordering guarantee lives (render everything, *then* prune, *then*
write), so a regression here loses documentation rather than merely misformatting it.
"""

import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

import docsbuild


@pytest.fixture
def db() -> ModuleType:
    return docsbuild


def _pages(directory: Path, pages: dict[str, str]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for slug, title in pages.items():
        (directory / f"{slug}.md").write_text(f"# {title}\n\nBody text.\n")


# ------------------------------------------------------------------- page chrome


def test_standalone_page_lists_its_own_h2_sections(db: ModuleType) -> None:
    """A page outside the reading chain gets a section index, not prev/next links."""
    html = db.standalone_page(
        "Configuring",
        "Brand",
        "../index.html",
        "# Top\n\n## Audio\n\n## Wake word\n",
        "",
    )

    assert '<a href="#audio">Audio</a>' in html
    assert '<a href="#wake-word">Wake word</a>' in html
    assert "On this page" in html
    assert 'class="nav' not in html


def test_standalone_page_points_its_brand_where_asked(db: ModuleType) -> None:
    html = db.standalone_page("T", "Brand", "guide/html/index.html", "# T\n", "")

    assert 'class="brand" href="guide/html/index.html"' in html


def test_page_shell_marks_the_current_page_and_wires_neighbours(
    db: ModuleType,
) -> None:
    pages = [("index", "Cover"), ("01-a", "A"), ("02-b", "B")]

    html = db.page_shell(pages, 1, "01-a", "A", "<p>x</p>", "", "Brand", "Suffix")

    assert '<a href="01-a.html" class="active">A</a>' in html
    assert '<a class="prev" href="index.html">' in html
    assert '<a class="next" href="02-b.html">' in html
    assert "<title>A · Suffix</title>" in html


def test_the_first_and_last_pages_have_no_dangling_neighbour(db: ModuleType) -> None:
    pages = [("index", "Cover"), ("01-a", "A")]

    first = db.page_shell(pages, 0, "index", "Cover", "", "", "B", "S")
    last = db.page_shell(pages, 1, "01-a", "A", "", "", "B", "S")

    assert '<span class="prev disabled"></span>' in first
    assert '<span class="next disabled"></span>' in last


# ----------------------------------------------------------------- build reporting


def test_read_sources_fails_loudly_on_a_missing_page(
    db: ModuleType, tmp_path: Path
) -> None:
    """Better to stop than to publish a site with a page silently missing."""
    _pages(tmp_path, {"index": "Cover"})

    with pytest.raises(SystemExit) as err:
        db.read_sources(tmp_path, [("index", "Cover"), ("gone", "Gone")])

    assert "gone.md" in str(err.value)


def test_report_names_every_page_it_removed(
    db: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A rename that quietly deletes a page is exactly what this print prevents."""
    db.report(3, tmp_path, ["09-old.html", "12-older.html"])

    out = capsys.readouterr().out
    assert "Built 3 pages" in out
    assert "09-old.html, 12-older.html" in out


def test_report_stays_quiet_when_nothing_was_removed(
    db: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    db.report(3, tmp_path, [])

    assert "Removed" not in capsys.readouterr().out


# --------------------------------------------------------------- standalone pages


def _site_with_standalone(root: Path, source_name: str = "extra.md") -> Path:
    _pages(root / "markdown", {"index": "Cover"})
    (root / "site.toml").write_text(
        'brand = "B"\ntitle_suffix = "T"\n\n'
        "[[standalone]]\n"
        f'source = "{source_name}"\n'
        'output = "extra.html"\n'
        'title = "Extra"\n'
        'brand_href = "markdown/index.html"\n'
    )
    return root / "site.toml"


def test_a_standalone_page_is_built_beside_its_config(
    db: ModuleType, tmp_path: Path
) -> None:
    cfg = _site_with_standalone(tmp_path)
    (tmp_path / "extra.md").write_text("# Extra\n\n## A section\n\nText.\n")

    db.build_site(db.load_site(cfg))

    html = (tmp_path / "extra.html").read_text()
    assert "<title>Extra</title>" in html
    assert '<a href="#a-section">A section</a>' in html


def test_a_standalone_page_with_no_source_is_skipped_not_fatal(
    db: ModuleType, tmp_path: Path
) -> None:
    """The ordinary pages must still build when an optional extra is absent."""
    cfg = _site_with_standalone(tmp_path, source_name="never-written.md")

    db.build_site(db.load_site(cfg))

    assert (tmp_path / "html" / "index.html").exists()
    assert not (tmp_path / "extra.html").exists()


def test_a_standalone_page_falls_back_to_the_site_brand(
    db: ModuleType, tmp_path: Path
) -> None:
    cfg = _site_with_standalone(tmp_path)
    (tmp_path / "extra.md").write_text("# Extra\n")

    db.build_site(db.load_site(cfg))

    assert ">B<" in (tmp_path / "extra.html").read_text()


# ------------------------------------------------------------- pruning on rebuild


def test_a_rebuild_removes_a_page_whose_source_is_gone(
    db: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Renaming a page must not leave the old one browsable forever."""
    _pages(tmp_path / "markdown", {"index": "Cover", "01-old": "Old"})
    (tmp_path / "site.toml").write_text('brand = "B"\ntitle_suffix = "T"\n')
    db.build_site(db.load_site(tmp_path / "site.toml"))
    assert (tmp_path / "html" / "01-old.html").exists()

    (tmp_path / "markdown" / "01-old.md").rename(tmp_path / "markdown" / "01-new.md")
    db.build_site(db.load_site(tmp_path / "site.toml"))

    assert not (tmp_path / "html" / "01-old.html").exists()
    assert (tmp_path / "html" / "01-new.html").exists()
    assert "01-old.html" in capsys.readouterr().out


# --------------------------------------------------------------- installed entry points


def test_the_module_runs_as_a_script(tmp_path: Path) -> None:
    """`python -m docsbuild` must work straight from a checkout, before installing."""
    _pages(tmp_path / "markdown", {"index": "Cover"})
    (tmp_path / "site.toml").write_text('brand = "B"\ntitle_suffix = "T"\n')

    result = subprocess.run(
        [sys.executable, "-m", "docsbuild"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "html" / "index.html").exists()


def test_the_console_script_is_installed(tmp_path: Path) -> None:
    """The `docsbuild` command is the documented way in; prove it exists and runs."""
    _pages(tmp_path / "markdown", {"index": "Cover"})
    (tmp_path / "site.toml").write_text('brand = "B"\ntitle_suffix = "T"\n')

    result = subprocess.run(["docsbuild"], cwd=tmp_path, capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "html" / "index.html").exists()
