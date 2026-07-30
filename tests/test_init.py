"""Tests for detection and scaffolding — `docsbuild init`.

The build keys off config files, not directory names, so a repository that has the
markdown but has never used this tool cannot build until a `site.toml` exists. These
cover the command that writes one, and the detection it shares with the error messages
that point people at it.
"""

import re
import tomllib
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

import docsbuild


@pytest.fixture
def db() -> ModuleType:
    return docsbuild


def _md(directory: Path, *slugs: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for slug in slugs:
        (directory / f"{slug}.md").write_text(f"# {slug.title()}\n\nBody.\n")


def _config(path: Path) -> dict[str, Any]:
    """Parse a generated config, so tests assert on meaning rather than formatting."""
    with path.open("rb") as fh:
        return tomllib.load(fh)


# ---------------------------------------------------------------------- detection


def test_detects_a_single_nested_set_at_the_root(
    db: ModuleType, tmp_path: Path
) -> None:
    """The conventional layout: markdown/ beside where the config will go."""
    _md(tmp_path / "markdown", "index", "01-a")

    found = db.detect_sets(tmp_path)

    assert [(s.name, s.source, s.pages) for s in found] == [("", "markdown", 2)]
    assert found[0].directory == tmp_path


def test_detects_a_single_flat_set_at_the_root(db: ModuleType, tmp_path: Path) -> None:
    """Markdown sitting directly in the directory, with no markdown/ subdirectory."""
    _md(tmp_path, "index", "01-a", "02-b")

    found = db.detect_sets(tmp_path)

    assert [(s.name, s.source, s.pages) for s in found] == [("", ".", 3)]


def test_root_markdown_wins_over_scanning_subdirectories(
    db: ModuleType, tmp_path: Path
) -> None:
    """A one-set project's own pages must not be read as a container of sets."""
    _md(tmp_path / "markdown", "index")
    _md(tmp_path / "onboarding" / "markdown", "index")

    found = db.detect_sets(tmp_path)

    assert [s.name for s in found] == [""]


def test_detects_several_sets_in_subdirectories(db: ModuleType, tmp_path: Path) -> None:
    """The case that prompted all of this: onboarding and a development plan."""
    _md(tmp_path / "onboarding" / "markdown", "index", "01-a", "02-b")
    _md(tmp_path / "development-plans" / "markdown", "index", "01-goal")

    found = db.detect_sets(tmp_path)

    assert [(s.name, s.source, s.pages) for s in found] == [
        ("development-plans", "markdown", 2),
        ("onboarding", "markdown", 3),
    ]


def test_a_mixed_project_detects_both_layouts(db: ModuleType, tmp_path: Path) -> None:
    _md(tmp_path / "guide" / "markdown", "index")
    _md(tmp_path / "notes", "index", "01-a")

    found = db.detect_sets(tmp_path)

    assert [(s.name, s.source) for s in found] == [
        ("guide", "markdown"),
        ("notes", "."),
    ]


def test_a_subdirectory_with_no_markdown_is_not_a_doc_set(
    db: ModuleType, tmp_path: Path
) -> None:
    _md(tmp_path / "onboarding" / "markdown", "index")
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "logo.png").write_bytes(b"")

    found = db.detect_sets(tmp_path)

    assert [s.name for s in found] == ["onboarding"]


def test_a_directory_with_no_documentation_detects_nothing(
    db: ModuleType, tmp_path: Path
) -> None:
    assert db.detect_sets(tmp_path) == []


def test_a_path_that_does_not_exist_detects_nothing_rather_than_raising(
    db: ModuleType, tmp_path: Path
) -> None:
    """A mistyped --root should reach the "nothing to configure" message, not a
    traceback."""
    missing = tmp_path / "not-here"

    assert db.detect_sets(missing) == []

    with pytest.raises(SystemExit) as err:
        db.main(["init", "--root", str(missing)])

    assert "no markdown found" in str(err.value)


def test_a_loose_markdown_file_at_the_root_does_not_hide_the_real_sets(
    db: ModuleType, tmp_path: Path
) -> None:
    """The layout that broke this: a standalone page beside two real doc sets.

    A docs root very often holds a loose `.md` — a README, a changelog, a reference
    page kept outside the reading chain. Reading that as "the root is a one-page doc
    set" made detection return a single flat set and never scan the subdirectories.
    """
    (tmp_path / "CONFIGURATION.md").write_text("# Configuring\n\nText.\n")
    _md(tmp_path / "onboarding" / "markdown", "index", "01-a", "02-b")
    _md(tmp_path / "development-plans" / "markdown", "index", "01-goal")

    found = db.detect_sets(tmp_path)

    assert [(s.name, s.source, s.pages) for s in found] == [
        ("development-plans", "markdown", 2),
        ("onboarding", "markdown", 3),
    ]


def test_loose_root_markdown_is_still_a_set_when_there_is_nothing_else(
    db: ModuleType, tmp_path: Path
) -> None:
    """Rule intact: loose files are a last resort, not ignored outright."""
    (tmp_path / "README.md").write_text("# Readme\n")
    (tmp_path / "guide.md").write_text("# Guide\n")

    found = db.detect_sets(tmp_path)

    assert [(s.name, s.source, s.pages) for s in found] == [("", ".", 2)]


def test_init_on_a_root_with_a_loose_page_configures_the_real_sets(
    db: ModuleType, tmp_path: Path
) -> None:
    """End to end on the reported failure: an index and a config per real set."""
    project = tmp_path / "docs"
    project.mkdir()
    (project / "CONFIGURATION.md").write_text("# Configuring\n")
    _md(project / "onboarding" / "markdown", "index", "01-a")
    _md(project / "development-plans" / "markdown", "index")

    db.main(["init", "--root", str(project)])

    assert _config(project / "sites.toml")["sets"] == [
        "development-plans",
        "onboarding",
    ]
    assert (project / "onboarding" / "site.toml").exists()
    assert (project / "development-plans" / "site.toml").exists()
    assert not (project / "site.toml").exists()


def test_init_names_the_top_level_file_it_skipped(
    db: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Skipping it silently would be the same mistake as reading it as a doc set."""
    project = tmp_path / "docs"
    project.mkdir()
    (project / "CONFIGURATION.md").write_text("# Configuring\n")
    _md(project / "onboarding" / "markdown", "index")
    _md(project / "plan" / "markdown", "index")

    db.main(["init", "--root", str(project)])

    out = capsys.readouterr().out
    assert "CONFIGURATION.md" in out
    assert "standalone" in out


def test_a_generated_output_directory_is_not_mistaken_for_a_set(
    db: ModuleType, tmp_path: Path
) -> None:
    """html/ holds no markdown, so it must never be picked up as a doc set."""
    _md(tmp_path / "onboarding" / "markdown", "index")
    (tmp_path / "onboarding" / "html").mkdir()
    (tmp_path / "onboarding" / "html" / "index.html").write_text("<p>x</p>")

    found = db.detect_sets(tmp_path)

    assert [s.name for s in found] == ["onboarding"]


# --------------------------------------------------------------------- exclusions


def test_a_dot_directory_holding_markdown_is_never_a_doc_set(
    db: ModuleType, tmp_path: Path
) -> None:
    """`.pytest_cache/README.md` was being configured as a one-page doc set."""
    _md(tmp_path / ".pytest_cache", "README")
    _md(tmp_path / "onboarding" / "markdown", "index")

    found = db.detect_sets(tmp_path)

    assert [s.name for s in found] == ["onboarding"]


def test_dependency_and_build_directories_are_skipped(
    db: ModuleType, tmp_path: Path
) -> None:
    """A vendored tree can hold thousands of markdown files. None of them are ours."""
    _md(tmp_path / "node_modules", "readme")
    _md(tmp_path / "__pycache__", "notes")
    _md(tmp_path / "dist", "readme")
    _md(tmp_path / "guide" / "markdown", "index")

    found = db.detect_sets(tmp_path)

    assert [s.name for s in found] == ["guide"]


def test_a_dot_directory_is_not_scanned_even_when_alone(
    db: ModuleType, tmp_path: Path
) -> None:
    """Excluding it must not depend on a real set existing to outrank it."""
    _md(tmp_path / ".pytest_cache", "README")

    assert db.detect_sets(tmp_path) == []


# ------------------------------------------------------------ containers vs sets


def test_a_directory_holding_doc_sets_is_not_itself_a_set(
    db: ModuleType, tmp_path: Path
) -> None:
    """`docs/` has CONFIGURATION.md beside two real sets. It is a container.

    Reading it as a one-page flat set is exactly what stopped it being recognised as
    the parent of onboarding/ and development-plans/.
    """
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "CONFIGURATION.md").write_text("# Configuring\n")
    _md(docs / "onboarding" / "markdown", "index", "01-a")
    _md(docs / "development-plans" / "markdown", "index")

    found = db.detect_sets(tmp_path)

    assert found == []  # the repo root holds no sets; docs/ is a container


def test_a_subdirectory_with_only_loose_markdown_is_still_a_flat_set(
    db: ModuleType, tmp_path: Path
) -> None:
    """The container rule must not break the flat layout it sits next to."""
    _md(tmp_path / "notes", "index", "01-a")

    found = db.detect_sets(tmp_path)

    assert [(s.name, s.source, s.pages) for s in found] == [("notes", ".", 2)]


# ------------------------------------------------------------- finding docs/ root


def test_find_docs_root_steps_into_a_conventional_docs_directory(
    db: ModuleType, tmp_path: Path
) -> None:
    _md(tmp_path / "docs" / "onboarding" / "markdown", "index")
    _md(tmp_path / "src", "not-docs")  # a decoy that is not a docs directory

    assert db.find_docs_root(tmp_path) == tmp_path / "docs"


def test_find_docs_root_prefers_the_directory_it_was_given(
    db: ModuleType, tmp_path: Path
) -> None:
    """Already standing in the docs root? Then that is the answer."""
    _md(tmp_path / "onboarding" / "markdown", "index")
    (tmp_path / "docs").mkdir()

    assert db.find_docs_root(tmp_path) == tmp_path


def test_find_docs_root_accepts_the_other_conventional_names(
    db: ModuleType, tmp_path: Path
) -> None:
    for name in ("doc", "documentation"):
        root = tmp_path / name
        _md(root / "guide" / "markdown", "index")

        assert db.find_docs_root(tmp_path) == tmp_path / "doc"  # first match wins
        break

    other = tmp_path / "elsewhere"
    _md(other / "documentation" / "guide" / "markdown", "index")

    assert db.find_docs_root(other) == other / "documentation"


def test_find_docs_root_returns_the_start_when_nothing_matches(
    db: ModuleType, tmp_path: Path
) -> None:
    """No convention, no sets — hand back what we were given and let init complain."""
    (tmp_path / "src").mkdir()

    assert db.find_docs_root(tmp_path) == tmp_path


def test_find_docs_root_finds_a_docs_directory_that_holds_config(
    db: ModuleType, tmp_path: Path
) -> None:
    """An already-configured project must be found too, not just an unconfigured one."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "sites.toml").write_text('sets = ["guide"]\n')

    assert db.find_docs_root(tmp_path) == docs


# ------------------------------------------------------------- init at a repo root


def test_init_at_a_repository_root_configures_the_docs_directory(
    db: ModuleType, tmp_path: Path
) -> None:
    """The question that prompted this: run it at the repo root, not in docs/."""
    repo = tmp_path / "acme-widgets"
    (repo / "src").mkdir(parents=True)
    (repo / "docs" / "CONFIGURATION.md").parent.mkdir(parents=True)
    (repo / "docs" / "CONFIGURATION.md").write_text("# Configuring\n")
    _md(repo / "docs" / "onboarding" / "markdown", "index", "01-a")
    _md(repo / "docs" / "development-plans" / "markdown", "index")

    db.main(["init", "--root", str(repo)])

    assert _config(repo / "docs" / "sites.toml")["sets"] == [
        "development-plans",
        "onboarding",
    ]
    assert (repo / "docs" / "onboarding" / "site.toml").exists()
    assert (repo / "docs" / "development-plans" / "site.toml").exists()


def test_init_at_a_repository_root_writes_nothing_outside_docs(
    db: ModuleType, tmp_path: Path
) -> None:
    """Config belongs beside the sets it names, never scattered at the repo root."""
    repo = tmp_path / "acme-widgets"
    _md(repo / "docs" / "guide" / "markdown", "index")
    _md(repo / ".pytest_cache", "README")

    db.main(["init", "--root", str(repo)])

    assert not (repo / "sites.toml").exists()
    assert not (repo / "site.toml").exists()
    assert not (repo / ".pytest_cache" / "site.toml").exists()


def test_init_says_which_directory_it_chose(
    db: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Quietly configuring a directory other than the one asked for is a surprise."""
    repo = tmp_path / "acme-widgets"
    _md(repo / "docs" / "guide" / "markdown", "index")

    db.main(["init", "--root", str(repo)])

    assert "docs" in capsys.readouterr().out


def test_init_then_build_both_work_from_the_repository_root(
    db: ModuleType, tmp_path: Path
) -> None:
    """If init succeeds at the root, the build that follows has to as well."""
    repo = tmp_path / "acme-widgets"
    _md(repo / "docs" / "onboarding" / "markdown", "index", "01-a")
    _md(repo / "docs" / "plan" / "markdown", "index")

    db.main(["init", "--root", str(repo)])
    db.main(["--root", str(repo)])

    assert (repo / "docs" / "onboarding" / "html" / "index.html").exists()
    assert (repo / "docs" / "plan" / "html" / "index.html").exists()


# ------------------------------------------------------- documenting the optionals


def test_the_generated_config_documents_all_three_optional_blocks(
    db: ModuleType, tmp_path: Path
) -> None:
    """Naming a feature without showing it just sends people to the README."""
    _md(tmp_path / "markdown", "index")

    db.main(["init", "--root", str(tmp_path)])

    text = (tmp_path / "site.toml").read_text()
    assert "[titles]" in text
    assert "[concat]" in text
    assert "[[standalone]]" in text


def test_each_optional_block_is_explained_not_just_shown(
    db: ModuleType, tmp_path: Path
) -> None:
    """The ask was explanations of what they *do*, not bare stanzas."""
    _md(tmp_path / "markdown", "index")

    db.main(["init", "--root", str(tmp_path)])

    text = (tmp_path / "site.toml").read_text().lower()
    assert "sidebar" in text  # what [titles] affects
    assert "reading order" in text  # what [concat] produces
    assert "outside the reading chain" in text  # what [[standalone]] is for


def test_the_generated_config_still_parses_to_only_the_active_keys(
    db: ModuleType, tmp_path: Path
) -> None:
    """Everything added is a comment. A stray live line would switch on a feature.

    Silently producing a plan.md or a standalone page nobody asked for is exactly the
    kind of bug that would take ages to trace back to a scaffolding template.
    """
    _md(tmp_path / "markdown", "index")

    db.main(["init", "--root", str(tmp_path)])

    parsed = _config(tmp_path / "site.toml")
    assert set(parsed) == {"brand", "title_suffix"}
    assert "concat" not in parsed
    assert "standalone" not in parsed
    assert "titles" not in parsed


def test_a_flat_set_config_still_parses_to_only_its_active_keys(
    db: ModuleType, tmp_path: Path
) -> None:
    _md(tmp_path, "index")

    db.main(["init", "--root", str(tmp_path)])

    assert set(_config(tmp_path / "site.toml")) == {"brand", "title_suffix", "source"}


_LIVE_LOOKING = re.compile(r"^# (\[|[a-z_]+ *= )")


def _uncomment_examples(config: Path) -> None:
    """Uncomment every line in *config* that looks like configuration, as an editor
    macro or a careless sed would."""
    config.write_text(
        "\n".join(
            line[2:] if _LIVE_LOOKING.match(line) else line
            for line in config.read_text().splitlines()
        )
    )


def test_uncommenting_every_config_looking_line_yields_valid_toml(
    db: ModuleType, tmp_path: Path
) -> None:
    """The examples have to survive being uncommented in bulk.

    Prose must never open a line with a bracket or a `key =`, or uncommenting a
    paragraph produces broken TOML. Caught for real: the explanations used to start
    `# [titles] overrides ...`, indistinguishable from the block header below them.
    """
    _md(tmp_path / "markdown", "index")
    db.main(["init", "--root", str(tmp_path)])

    _uncomment_examples(tmp_path / "site.toml")

    parsed = _config(tmp_path / "site.toml")
    assert "titles" in parsed
    assert "concat" in parsed
    assert "standalone" in parsed


def test_the_uncommented_examples_actually_work(db: ModuleType, tmp_path: Path) -> None:
    """An example that is shown but wrong would be worse than no example at all."""
    _md(tmp_path / "markdown", "index", "01-a")
    (tmp_path / "REFERENCE.md").write_text("# Reference\n\n## A section\n")
    db.main(["init", "--root", str(tmp_path)])

    _uncomment_examples(tmp_path / "site.toml")
    db.main(["--config", str(tmp_path / "site.toml")])

    assert "Overview &amp; contents" in (tmp_path / "html" / "index.html").read_text()
    assert (tmp_path / "all.md").exists()
    assert (tmp_path / "REFERENCE.html").exists()


def test_the_standalone_example_reaches_a_shared_page_from_a_nested_set(
    db: ModuleType, tmp_path: Path
) -> None:
    """A set in a subdirectory reaches a page beside its siblings, one level up.

    The `../` prefix is right there and wrong for a set at the project root, where it
    would point outside the project entirely.
    """
    project = tmp_path / "docs"
    _md(project / "onboarding" / "markdown", "index")
    (project / "REFERENCE.md").write_text("# Reference\n\n## A section\n")
    db.main(["init", "--root", str(project)])

    _uncomment_examples(project / "onboarding" / "site.toml")
    db.main(["--root", str(project), "--set", "onboarding"])

    assert (project / "REFERENCE.html").exists()
    assert (project / "onboarding" / "onboarding.md").exists()


def test_the_documented_config_builds_with_nothing_switched_on(
    db: ModuleType, tmp_path: Path
) -> None:
    """The commented examples must not leak into the build's behaviour."""
    project = tmp_path / "docs"
    _md(project / "onboarding" / "markdown", "index", "01-a")

    db.main(["init", "--root", str(project)])
    db.main(["--root", str(project)])

    built = project / "onboarding"
    assert (built / "html" / "index.html").exists()
    assert not (built / "onboarding.md").exists()  # [concat] stayed off
    assert list(built.glob("*.html")) == []  # [[standalone]] stayed off


def test_the_concat_example_names_the_real_set(db: ModuleType, tmp_path: Path) -> None:
    """A copy-paste example has to be copy-paste correct, not a placeholder."""
    project = tmp_path / "docs"
    _md(project / "onboarding" / "markdown", "index")
    _md(project / "plan" / "markdown", "index")

    db.main(["init", "--root", str(project)])

    assert "--set onboarding" in (project / "onboarding" / "site.toml").read_text()
    assert "--set plan" in (project / "plan" / "site.toml").read_text()


def test_the_concat_example_omits_set_for_a_lone_root_set(
    db: ModuleType, tmp_path: Path
) -> None:
    """A lone root set answers to a bare `docsbuild`, so do not invent a name."""
    _md(tmp_path / "markdown", "index")

    db.main(["init", "--root", str(tmp_path)])

    assert "--set" not in (tmp_path / "site.toml").read_text()


def test_the_report_shows_the_optional_blocks_with_an_example(
    db: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _md(tmp_path / "docs" / "onboarding" / "markdown", "index")

    db.main(["init", "--root", str(tmp_path)])

    out = capsys.readouterr().out
    assert "[titles]" in out
    assert "[concat]" in out
    assert "[[standalone]]" in out
    assert 'command = "docsbuild --set onboarding"' in out  # a real worked example


def test_the_report_keeps_the_copy_the_config_advice(
    db: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The answer to 'why does my copy build differently' has to stay visible."""
    _md(tmp_path / "markdown", "index")

    db.main(["init", "--root", str(tmp_path)])

    assert "site.toml" in capsys.readouterr().out.lower()


# ------------------------------------------------------------------ badge scanning
#
# Badges are opt-in, so a repository whose docs already use `[DONE]` would otherwise
# get a clean build in which every badge had silently become plain text, with nothing
# in the generated config hinting that a `[badges]` table would bring them back. init
# reads the markdown and writes the table for you.


def test_badge_tokens_are_found_in_the_markdown(db: ModuleType, tmp_path: Path) -> None:
    src = tmp_path / "markdown"
    src.mkdir()
    (src / "index.md").write_text(
        "# Cover\n\n- [DONE] a\n- [PLANNED] b\n- [DONE] c\n* [LATER] d\n"
    )

    assert db.scan_badge_tokens(src) == ["DONE", "LATER", "PLANNED"]


def test_badge_tokens_are_ordered_by_how_often_they_appear(
    db: ModuleType, tmp_path: Path
) -> None:
    """Most-used first reads better in the written config; ties break by name."""
    src = tmp_path / "markdown"
    src.mkdir()
    (src / "index.md").write_text(
        "# C\n\n- [RARE] x\n- [COMMON] a\n- [COMMON] b\n- [COMMON] c\n"
    )

    assert db.scan_badge_tokens(src) == ["COMMON", "RARE"]


def test_only_tokens_at_the_head_of_a_list_item_count(
    db: ModuleType, tmp_path: Path
) -> None:
    """The same rule the renderer applies, so what is written is what will render."""
    src = tmp_path / "markdown"
    src.mkdir()
    (src / "index.md").write_text(
        "# C\n\nA paragraph mentioning [NOTATOKEN] inline.\n\n"
        "- work that is [MIDSENTENCE] not at the head\n"
        "- [REAL] this one counts\n"
    )

    assert db.scan_badge_tokens(src) == ["REAL"]


def test_badge_tokens_inside_code_fences_are_ignored(
    db: ModuleType, tmp_path: Path
) -> None:
    """A fenced example of the syntax is documentation, not a declaration."""
    src = tmp_path / "markdown"
    src.mkdir()
    (src / "index.md").write_text(
        "# C\n\n```markdown\n- [FENCED] an example\n```\n\n- [REAL] actual use\n"
    )

    assert db.scan_badge_tokens(src) == ["REAL"]


def test_init_writes_a_live_badges_table_for_the_tokens_it_found(
    db: ModuleType, tmp_path: Path
) -> None:
    """The case that prompted this: the config should just work, not need editing."""
    project = tmp_path / "docs"
    src = project / "plan" / "markdown"
    src.mkdir(parents=True)
    (src / "index.md").write_text(
        "# Plan\n\n- [DONE] a\n- [PLANNED] b\n- [DROPPED] c\n"
    )

    db.main(["init", "--root", str(project)])

    badges = _config(project / "plan" / "site.toml")["badges"]
    assert badges == {"DONE": "Done", "PLANNED": "Planned", "DROPPED": "Dropped"}


def test_a_generated_badges_table_actually_renders_pills(
    db: ModuleType, tmp_path: Path
) -> None:
    """End to end: init then build, and the badges are pills without anyone editing."""
    project = tmp_path / "docs"
    src = project / "plan" / "markdown"
    src.mkdir(parents=True)
    (src / "index.md").write_text("# Plan\n\n- [DONE] shipped\n- [PLANNED] later\n")

    db.main(["init", "--root", str(project)])
    db.main(["--root", str(project)])

    html = (project / "plan" / "html" / "index.html").read_text()
    assert '<span class="badge done">Done</span>' in html
    assert '<span class="badge planned">Planned</span>' in html


def test_a_set_with_no_badge_tokens_gets_only_the_commented_example(
    db: ModuleType, tmp_path: Path
) -> None:
    _md(tmp_path / "markdown", "index")

    db.main(["init", "--root", str(tmp_path)])

    text = (tmp_path / "site.toml").read_text()
    assert "[badges]" in text  # documented alongside the other optional blocks
    assert "badges" not in _config(tmp_path / "site.toml")  # but not switched on


def test_init_warns_about_a_token_with_no_matching_style(
    db: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An undeclared style renders an unstyled pill; guessing a colour is worse."""
    project = tmp_path / "docs"
    src = project / "plan" / "markdown"
    src.mkdir(parents=True)
    (src / "index.md").write_text("# Plan\n\n- [DONE] a\n- [BUILT] b\n")

    db.main(["init", "--root", str(project)])

    out = capsys.readouterr().out
    assert "BUILT" in out
    assert "DONE" not in out.split("BUILT")[1]  # only the unstyled one is named


# --------------------------------------------------------------------- humanising


def test_humanise_turns_a_directory_name_into_a_label(db: ModuleType) -> None:
    assert db.humanise("development-plans") == "Development Plans"
    assert db.humanise("onboarding") == "Onboarding"
    assert db.humanise("api_reference") == "Api Reference"


# --------------------------------------------------------------- init, single set


def test_init_writes_one_site_toml_and_no_sites_index(
    db: ModuleType, tmp_path: Path
) -> None:
    """A single doc set needs no index listing itself; keep that shape clean."""
    project = tmp_path / "docs"
    _md(project / "markdown", "index", "01-a")

    db.main(["init", "--root", str(project)])

    assert (project / "site.toml").exists()
    assert not (project / "sites.toml").exists()


def test_init_writes_a_config_the_build_can_immediately_use(
    db: ModuleType, tmp_path: Path
) -> None:
    """The whole point: init then build, with nothing written by hand in between."""
    project = tmp_path / "docs"
    _md(project / "markdown", "index", "01-a")

    db.main(["init", "--root", str(project)])
    db.main(["--root", str(project)])

    assert (project / "html" / "index.html").exists()
    assert (project / "html" / "01-a.html").exists()


def test_a_lone_set_in_a_subdirectory_still_gets_an_index(
    db: ModuleType, tmp_path: Path
) -> None:
    """`docs/onboarding/` alone: the config is not at the root, so an index is needed.

    Without one, `docsbuild` run in `docs/` finds no config and fails, even though init
    just wrote `onboarding/site.toml`. The index is what says where the sets are, so it
    is required whenever they are nested — not only when there are several.
    """
    project = tmp_path / "docs"
    _md(project / "onboarding" / "markdown", "index", "01-a")

    db.main(["init", "--root", str(project)])
    db.main(["--root", str(project)])

    assert _config(project / "sites.toml")["sets"] == ["onboarding"]
    assert (project / "onboarding" / "html" / "index.html").exists()


def test_a_set_at_the_root_needs_no_index(db: ModuleType, tmp_path: Path) -> None:
    """The mirror case: config at the root is found directly, so no index is written."""
    project = tmp_path / "docs"
    _md(project / "markdown", "index")

    db.main(["init", "--root", str(project)])

    assert not (project / "sites.toml").exists()


def test_init_guesses_the_brand_from_the_surrounding_directories(
    db: ModuleType, tmp_path: Path
) -> None:
    """`docs/` inside a checkout means the parent is usually the project name."""
    project = tmp_path / "acme-widgets" / "docs"
    _md(project / "markdown", "index")

    db.main(["init", "--root", str(project)])

    text = (project / "site.toml").read_text()
    assert 'brand = "acme-widgets"' in text or "acme-widgets" in text


# ------------------------------------------------------------- init, several sets


def test_init_writes_an_index_and_a_config_per_set(
    db: ModuleType, tmp_path: Path
) -> None:
    project = tmp_path / "docs"
    _md(project / "onboarding" / "markdown", "index", "01-a")
    _md(project / "development-plans" / "markdown", "index")

    db.main(["init", "--root", str(project)])

    assert (
        'sets = ["development-plans", "onboarding"]'
        in (project / "sites.toml").read_text()
    )
    assert (project / "onboarding" / "site.toml").exists()
    assert (project / "development-plans" / "site.toml").exists()


def test_init_then_build_all_produces_every_set(db: ModuleType, tmp_path: Path) -> None:
    """End to end on the layout the user asked about."""
    project = tmp_path / "docs"
    _md(project / "onboarding" / "markdown", "index", "01-a")
    _md(project / "development-plans" / "markdown", "index", "01-goal", "02-status")

    db.main(["init", "--root", str(project)])
    db.main(["--root", str(project), "--all"])

    assert len(list((project / "onboarding" / "html").glob("*.html"))) == 2
    assert len(list((project / "development-plans" / "html").glob("*.html"))) == 3


def test_init_names_a_flat_set_s_source_explicitly(
    db: ModuleType, tmp_path: Path
) -> None:
    """`source` is only written when it differs from the default."""
    project = tmp_path / "docs"
    _md(project / "notes", "index")
    _md(project / "guide" / "markdown", "index")

    db.main(["init", "--root", str(project)])

    assert _config(project / "notes" / "site.toml")["source"] == "."
    assert "source" not in _config(project / "guide" / "site.toml")


# ------------------------------------------------------------ init is not destructive


def test_init_keeps_an_existing_config(db: ModuleType, tmp_path: Path) -> None:
    """Silently eating a hand-tuned config would be worse than no scaffolding."""
    project = tmp_path / "docs"
    _md(project / "markdown", "index")
    (project / "site.toml").write_text('brand = "Mine"\ntitle_suffix = "Mine"\n')

    db.main(["init", "--root", str(project)])

    assert (
        project / "site.toml"
    ).read_text() == 'brand = "Mine"\ntitle_suffix = "Mine"\n'


def test_init_force_overwrites_an_existing_config(
    db: ModuleType, tmp_path: Path
) -> None:
    project = tmp_path / "docs"
    _md(project / "markdown", "index")
    (project / "site.toml").write_text('brand = "Mine"\ntitle_suffix = "Mine"\n')

    db.main(["init", "--root", str(project), "--force"])

    assert "Mine" not in (project / "site.toml").read_text()


def test_init_reports_what_it_wrote_and_what_it_kept(
    db: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "docs"
    _md(project / "onboarding" / "markdown", "index", "01-a")
    _md(project / "plan" / "markdown", "index")
    (project / "plan" / "site.toml").write_text('brand = "B"\ntitle_suffix = "T"\n')

    db.main(["init", "--root", str(project)])

    out = capsys.readouterr().out
    assert "onboarding" in out and "2" in out  # detected, with its page count
    assert "kept" in out.lower()  # the existing plan/site.toml
    assert "docsbuild" in out  # the next command to run


def test_init_keeps_an_existing_sites_index(db: ModuleType, tmp_path: Path) -> None:
    """The index may have been hand-ordered, or a set left out on purpose."""
    project = tmp_path / "docs"
    _md(project / "guide" / "markdown", "index")
    _md(project / "plan" / "markdown", "index")
    (project / "sites.toml").write_text('sets = ["plan", "guide"]\n')

    db.main(["init", "--root", str(project)])

    assert _config(project / "sites.toml")["sets"] == ["plan", "guide"]


def test_init_warns_about_a_set_the_index_does_not_list(
    db: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Otherwise a newly added set gets a config and still silently never builds."""
    project = tmp_path / "docs"
    _md(project / "guide" / "markdown", "index")
    _md(project / "newcomer" / "markdown", "index")
    (project / "sites.toml").write_text('sets = ["guide"]\n')

    db.main(["init", "--root", str(project)])

    out = capsys.readouterr().out
    assert "newcomer" in out
    assert "not listed" in out


def test_init_on_a_directory_with_no_markdown_says_so(
    db: ModuleType, tmp_path: Path
) -> None:
    with pytest.raises(SystemExit) as err:
        db.main(["init", "--root", str(tmp_path)])

    assert "no markdown" in str(err.value).lower()
