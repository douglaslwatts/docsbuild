"""Tests for the parts that let this tool live outside the project it builds.

The converter is the same code it always was; these cover the four things that had to
change once it stopped sitting next to the docs it renders — finding a project root from
the working directory, shipping a default stylesheet, honouring configured directory
names when rewriting links, and deriving the concatenated file's depth instead of
assuming it.
"""

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


def _single_set(root: Path, extra: str = "", source: str = "markdown") -> Path:
    """A minimal one-doc-set project: a site.toml and a directory of markdown."""
    _pages(root / source, {"index": "Cover", "01-first": "First"})
    (root / "site.toml").write_text(
        f'brand = "B"\ntitle_suffix = "T"\nsource = "{source}"\n{extra}'
    )
    return root


# ------------------------------------------------------------------ root discovery


def test_find_root_finds_a_single_set_project(db: ModuleType, tmp_path: Path) -> None:
    """A project with one doc set needs no index file — just its site.toml."""
    _single_set(tmp_path)

    assert db.find_root(tmp_path) == tmp_path


def test_find_root_finds_a_multi_set_project(db: ModuleType, tmp_path: Path) -> None:
    (tmp_path / "sites.toml").write_text('sets = ["guide"]\n')

    assert db.find_root(tmp_path) == tmp_path


def test_find_root_walks_up_from_a_nested_directory(
    db: ModuleType, tmp_path: Path
) -> None:
    """Run from anywhere inside the project and it still finds the root."""
    _single_set(tmp_path)
    deep = tmp_path / "markdown" / "nested" / "deeper"
    deep.mkdir(parents=True)

    assert db.find_root(deep) == tmp_path


def test_find_root_steps_down_into_a_docs_directory(
    db: ModuleType, tmp_path: Path
) -> None:
    """Building from a repo root must work, or init succeeding there is a lie."""
    (tmp_path / "src").mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "sites.toml").write_text('sets = ["guide"]\n')

    assert db.find_root(tmp_path) == docs


def test_find_root_finds_a_docs_directory_from_a_sibling_subdirectory(
    db: ModuleType, tmp_path: Path
) -> None:
    """`cd src && docsbuild` must find docs/, not give up at src/.

    Otherwise a stray README.md in src/ makes the error suggest configuring src/ as a
    doc set, which is precisely the wrong advice.
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "README.md").write_text("# Source\n")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "sites.toml").write_text('sets = ["guide"]\n')

    assert db.find_root(src) == docs


def test_find_root_prefers_the_upward_walk_over_stepping_down(
    db: ModuleType, tmp_path: Path
) -> None:
    """Existing behaviour wins: a config at or above the start is the answer."""
    _single_set(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "sites.toml").write_text('sets = ["x"]\n')

    assert db.find_root(tmp_path) == tmp_path


def test_find_root_errors_clearly_when_there_is_no_project(
    db: ModuleType, tmp_path: Path
) -> None:
    """The message has to name what it looked for; 'not found' alone is useless."""
    empty = tmp_path / "nothing" / "here"
    empty.mkdir(parents=True)

    with pytest.raises(SystemExit) as err:
        db.find_root(empty)

    assert "site.toml" in str(err.value) and "sites.toml" in str(err.value)


# ------------------------------------------------------------------- set selection


def test_site_configs_finds_the_lone_site_toml(db: ModuleType, tmp_path: Path) -> None:
    """sites.toml is optional: one doc set does not need an index listing itself."""
    _single_set(tmp_path)

    assert db.site_configs(tmp_path) == [tmp_path / "site.toml"]


def test_site_configs_reads_the_sets_index(db: ModuleType, tmp_path: Path) -> None:
    (tmp_path / "sites.toml").write_text('sets = ["guide", "plan"]\n')

    assert db.site_configs(tmp_path) == [
        tmp_path / "guide" / "site.toml",
        tmp_path / "plan" / "site.toml",
    ]


def test_site_configs_selects_one_named_set(db: ModuleType, tmp_path: Path) -> None:
    (tmp_path / "sites.toml").write_text('sets = ["guide", "plan"]\n')

    assert db.site_configs(tmp_path, "plan") == [tmp_path / "plan" / "site.toml"]


def test_site_configs_rejects_an_unknown_set_name(
    db: ModuleType, tmp_path: Path
) -> None:
    (tmp_path / "sites.toml").write_text('sets = ["guide"]\n')

    with pytest.raises(SystemExit) as err:
        db.site_configs(tmp_path, "nope")

    assert "nope" in str(err.value)


def test_site_configs_errors_when_the_directory_holds_no_project(
    db: ModuleType, tmp_path: Path
) -> None:
    with pytest.raises(SystemExit):
        db.site_configs(tmp_path)


# ------------------------------------------------------- errors that teach the fix


def test_unconfigured_markdown_is_told_to_run_init(
    db: ModuleType, tmp_path: Path
) -> None:
    """The common first encounter: a repo with docs but no config. Name the fix."""
    _pages(tmp_path / "onboarding" / "markdown", {"index": "Cover"})

    with pytest.raises(SystemExit) as err:
        db.site_configs(tmp_path)

    message = str(err.value)
    assert "docsbuild init" in message
    assert "onboarding" in message


def test_a_directory_with_no_docs_at_all_says_that_instead(
    db: ModuleType, tmp_path: Path
) -> None:
    """'No config' and 'nothing here' are different problems; say which one it is."""
    with pytest.raises(SystemExit) as err:
        db.site_configs(tmp_path)

    assert "docsbuild init" not in str(err.value)


def test_find_root_also_points_at_init_when_it_finds_markdown(
    db: ModuleType, tmp_path: Path
) -> None:
    _pages(tmp_path / "markdown", {"index": "Cover"})

    with pytest.raises(SystemExit) as err:
        db.find_root(tmp_path)

    assert "docsbuild init" in str(err.value)


def test_a_config_missing_a_required_key_names_the_file_and_the_key(
    db: ModuleType, tmp_path: Path
) -> None:
    """An empty site.toml used to raise a bare KeyError with no context."""
    _pages(tmp_path / "markdown", {"index": "Cover"})
    (tmp_path / "site.toml").write_text('title_suffix = "T"\n')

    with pytest.raises(SystemExit) as err:
        db.load_site(tmp_path / "site.toml")

    message = str(err.value)
    assert "brand" in message
    assert "site.toml" in message


def test_a_config_missing_both_required_keys_names_both(
    db: ModuleType, tmp_path: Path
) -> None:
    _pages(tmp_path / "markdown", {"index": "Cover"})
    (tmp_path / "site.toml").write_text("# nothing here\n")

    with pytest.raises(SystemExit) as err:
        db.load_site(tmp_path / "site.toml")

    assert "brand" in str(err.value) and "title_suffix" in str(err.value)


def test_naming_a_set_a_single_set_project_does_not_have_is_an_error(
    db: ModuleType, tmp_path: Path
) -> None:
    """--set on a one-set project should say so, not silently build the wrong thing."""
    _single_set(tmp_path)

    with pytest.raises(SystemExit) as err:
        db.site_configs(tmp_path, "other")

    assert "other" in str(err.value)


def test_naming_a_single_set_project_by_its_directory_works(
    db: ModuleType, tmp_path: Path
) -> None:
    """A one-set project answers to its own directory name, so --set stays usable."""
    project = tmp_path / "guide"
    _single_set(project)

    assert db.site_configs(project, "guide") == [project / "site.toml"]


# ---------------------------------------------------------------------------- CLI


def test_bare_invocation_builds_the_discovered_set(
    db: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`docsbuild` with no arguments, run inside a project, just works."""
    _single_set(tmp_path)
    monkeypatch.chdir(tmp_path)

    db.main([])

    assert (tmp_path / "html" / "index.html").exists()
    assert (tmp_path / "html" / "01-first.html").exists()


def test_root_builds_a_project_in_another_tree(
    db: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--root is what makes this usable against a checkout somewhere else."""
    project = tmp_path / "elsewhere"
    _single_set(project)
    elsewhere = tmp_path / "cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    db.main(["--root", str(project), "--all"])

    assert (project / "html" / "index.html").exists()


def test_config_builds_one_named_file(db: ModuleType, tmp_path: Path) -> None:
    _single_set(tmp_path)

    db.main(["--config", str(tmp_path / "site.toml")])

    assert (tmp_path / "html" / "index.html").exists()


def test_set_selects_one_of_several(db: ModuleType, tmp_path: Path) -> None:
    (tmp_path / "sites.toml").write_text('sets = ["guide", "plan"]\n')
    _single_set(tmp_path / "guide")
    _single_set(tmp_path / "plan")

    db.main(["--root", str(tmp_path), "--set", "guide"])

    assert (tmp_path / "guide" / "html" / "index.html").exists()
    assert not (tmp_path / "plan" / "html").exists()


# ------------------------------------------------------------- bundled stylesheet


def test_a_site_without_a_style_key_uses_the_bundled_sheet(
    db: ModuleType, tmp_path: Path
) -> None:
    """A one-set project should not have to invent a stylesheet to build anything."""
    _single_set(tmp_path)

    site = db.load_site(tmp_path / "site.toml")

    assert site.style == db.BUNDLED_STYLE
    assert site.style.name == "style.css"
    assert site.style.exists()


def test_the_bundled_sheet_is_inlined_into_the_built_page(
    db: ModuleType, tmp_path: Path
) -> None:
    _single_set(tmp_path)

    db.main(["--config", str(tmp_path / "site.toml")])

    html = (tmp_path / "html" / "index.html").read_text()
    assert ".layout" in html  # a selector the bundled sheet defines


def test_an_explicit_style_key_still_wins(db: ModuleType, tmp_path: Path) -> None:
    _single_set(tmp_path, extra='style = "mine.css"\n')
    (tmp_path / "mine.css").write_text("body{color:rebeccapurple}")

    db.main(["--config", str(tmp_path / "site.toml")])

    assert "rebeccapurple" in (tmp_path / "html" / "index.html").read_text()


# ------------------------------------------------------ configured directory names


def test_cross_set_links_follow_the_default_directory_names(db: ModuleType) -> None:
    out = db.md_to_html("[x](../../guide/markdown/01-a.md)")

    assert 'href="../../guide/html/01-a.html"' in out


def test_a_link_that_is_not_a_markdown_page_is_left_as_written(
    db: ModuleType,
) -> None:
    """Only ``.md`` links get an extension swap; everything else passes through."""
    out = db.md_to_html("[a](https://example.com) [b](diagram.png)")

    assert 'href="https://example.com"' in out
    assert 'href="diagram.png"' in out


def test_cross_set_links_follow_configured_directory_names(db: ModuleType) -> None:
    """A project that calls its directories something else must still get real links.

    Hardcoding markdown/ and html/ would silently point built pages at markdown files.
    """
    out = db.md_to_html("[x](../../guide/pages/01-a.md)", link_dirs=("pages", "site"))

    assert 'href="../../guide/site/01-a.html"' in out


def test_configured_names_reach_list_items_and_tables(db: ModuleType) -> None:
    """The parameter has to be threaded all the way down, not just to paragraphs."""
    bullet = db.md_to_html("- [x](../../g/pages/01-a.md)", link_dirs=("pages", "site"))
    table = db.md_to_html(
        "| h |\n|---|\n| [x](../../g/pages/01-a.md) |", link_dirs=("pages", "site")
    )

    assert "/site/01-a.html" in bullet
    assert "/site/01-a.html" in table


def test_a_flat_set_does_not_rewrite_links_containing_its_own_name(
    db: ModuleType, tmp_path: Path
) -> None:
    """A flat set's source dir *is* the set dir, so its name is not a safe marker.

    With source = ".", naively passing the directory name as the source-dir marker would
    rewrite any link containing that word — including one pointing somewhere unrelated.
    A flat set has no source subdirectory for a cross-set link to route through, so the
    link is treated as what it is: a file that is not a page, linked from ``html/``.
    """
    project = tmp_path / "onboarding"
    project.mkdir()
    (project / "index.md").write_text("# Cover\n\n[x](../vendor/onboarding/notes.md)\n")
    (project / "site.toml").write_text(
        'brand = "B"\ntitle_suffix = "T"\nsource = "."\n'
    )

    db.main(["--config", str(project / "site.toml")])

    html = (project / "html" / "index.html").read_text()
    assert 'href="../../vendor/onboarding/notes.md"' in html
    assert "/html/notes" not in html


def test_a_flat_set_builds_its_pages_into_the_output_directory(
    db: ModuleType, tmp_path: Path
) -> None:
    """Markdown directly in the set directory, no markdown/ subdirectory."""
    project = tmp_path / "notes"
    _pages(project, {"index": "Cover", "01-a": "A"})
    (project / "site.toml").write_text(
        'brand = "B"\ntitle_suffix = "T"\nsource = "."\n'
    )

    db.main(["--config", str(project / "site.toml")])

    assert (project / "html" / "index.html").exists()
    assert (project / "html" / "01-a.html").exists()


def test_a_build_passes_its_own_directory_names_to_the_converter(
    db: ModuleType, tmp_path: Path
) -> None:
    """End to end: the names in site.toml are the ones the links use."""
    _single_set(tmp_path, extra='output = "site"\n', source="pages")
    (tmp_path / "pages" / "02-link.md").write_text(
        "# Link\n\n[x](../../other/pages/01-a.md)\n"
    )

    db.main(["--config", str(tmp_path / "site.toml")])

    assert "/site/01-a.html" in (tmp_path / "site" / "02-link.html").read_text()


# ----------------------------------------------------------- concatenation depth


def test_concat_rebases_links_for_a_deeper_output(db: ModuleType) -> None:
    """A concat file two levels above the sources needs two fewer ``../``."""
    out = db.concat_links(
        "[x](../../guide/markdown/01-a.md)", {}, set(), prefix="plan/markdown"
    )

    assert out == "[x](guide/markdown/01-a.md)"


def test_concat_leaves_absolute_and_anchor_links_alone(db: ModuleType) -> None:
    """Rebasing is only meaningful for paths relative to the markdown directory."""
    md = "[a](https://example.com) [b](#section) [c](/root/x.png)"

    assert db.concat_links(md, {}, set()) == md


def test_concat_pulls_a_same_directory_link_into_the_source_dir(
    db: ModuleType,
) -> None:
    """An asset beside the pages is one level deeper once the file moves up."""
    out = db.concat_links("[x](assets/diagram.png)", {}, set())

    assert out == "[x](markdown/assets/diagram.png)"


def test_concat_output_two_levels_up_is_written_where_configured(
    db: ModuleType, tmp_path: Path
) -> None:
    """End to end, with the concat file somewhere other than one level up."""
    project = tmp_path / "docs" / "plan"
    _single_set(
        project,
        extra=('\n[concat]\noutput = "../../whole-plan.md"\ncommand = "docsbuild"\n'),
    )

    db.main(["--config", str(project / "site.toml")])

    assert (tmp_path / "whole-plan.md").exists()
