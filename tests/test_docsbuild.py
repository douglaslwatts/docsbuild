"""Tests for the markdown converter and the page chrome.

Every doc set a project builds goes through this one module, so a bug here breaks all of
them at once. That is the whole reason these tests exist: before them, the two rendering
bugs this converter shipped — list items that wrap across lines, and italics nested
inside bold — were both found by eye, in output, after the fact.

They pin the converter's real contract, including the limitations that are *documented*
rather than fixed, so "the README says X" and "the code does X" cannot drift apart.

The ``db`` fixture is just the module. It is a fixture rather than a plain import
because these tests were written when the module had to be loaded by path, and keeping
the name costs nothing while keeping the test bodies stable.
"""

import re
from pathlib import Path
from types import ModuleType

import pytest

import docsbuild


@pytest.fixture
def db() -> ModuleType:
    return docsbuild


# --------------------------------------------------------------------------- blocks
#
# These assert *semantics* — that a list is a list, that a link points where it should —
# rather than exact HTML strings. The exact strings were pinned when the converter was
# hand-written; they all changed when it became markdown-it-py, and every one of those
# changes was cosmetic. Semantic assertions survive a renderer swap, which is the whole
# point of writing them this way.


def _tags(html: str, tag: str) -> int:
    return len(re.findall(rf"<{tag}[ >]", html))


def test_headings_get_anchor_ids_at_h2_and_h3(db: ModuleType) -> None:
    """Deep enough for an in-page contents panel, shallow enough to stay meaningful."""
    out = db.md_to_html("# Top\n\n## Where it stands\n\n### Detail\n\n#### Deeper")

    assert '<h2 id="where-it-stands">' in out
    assert '<h3 id="detail">' in out
    assert "<h1>" in out and "id=" not in out.split("<h2")[0]
    assert "<h4 id=" not in out


def test_paragraphs_are_paragraphs(db: ModuleType) -> None:
    out = db.md_to_html("First line\nwrapped onto a second.\n\nA separate paragraph.")

    assert _tags(out, "p") == 2


def test_horizontal_rule_and_blockquote(db: ModuleType) -> None:
    out = db.md_to_html("> quoted words\n\n---\n")

    assert "<blockquote>" in out and "quoted words" in out
    assert "<hr>" in out


def test_code_fence_content_is_not_interpreted(db: ModuleType) -> None:
    """Nothing inside a fence may be treated as markdown or as HTML."""
    out = db.md_to_html("```\n- **not a list**\n<b>not bold</b>\n```")

    assert "<pre>" in out and "<code>" in out
    assert "<ul>" not in out
    assert "<strong>" not in out
    assert "&lt;b&gt;" in out


# ---------------------------------------------------------------------------- lists


def test_a_wrapped_list_item_stays_one_item(db: ModuleType) -> None:
    """A bullet continued on an indented line is one item, not an item plus a stray
    paragraph — and inline markup spanning the break must still render."""
    out = db.md_to_html(
        "- **Bold start.** A sentence continuing\n  onto a second line."
    )

    assert _tags(out, "li") == 1
    assert _tags(out, "ul") == 1
    assert "<strong>Bold start.</strong>" in out
    assert "onto a second line" in out


def test_consecutive_bullets_form_one_list(db: ModuleType) -> None:
    out = db.md_to_html("- one\n- two\n- three")

    assert _tags(out, "ul") == 1
    assert _tags(out, "li") == 3


def test_numbered_list_renders_as_ol(db: ModuleType) -> None:
    out = db.md_to_html("1. first\n2. second")

    assert _tags(out, "ol") == 1
    assert _tags(out, "li") == 2
    assert "<ul>" not in out


def test_lists_nest(db: ModuleType) -> None:
    out = db.md_to_html("- top\n  - child\n    - grandchild\n- sibling")

    assert _tags(out, "ul") == 3
    assert _tags(out, "li") == 4
    assert "top - child" not in out  # the old flattening bug


def test_a_blank_line_between_items_makes_one_loose_list(db: ModuleType) -> None:
    """CommonMark: still one list, its items wrapped in paragraphs for looser spacing.

    The hand-written converter produced two separate lists here. That was wrong, and the
    stylesheet has a rule keeping the added paragraphs from opening a gap mid-item.
    """
    out = db.md_to_html("- a\n\n- b")

    assert _tags(out, "ul") == 1
    assert _tags(out, "li") == 2


# --------------------------------------------------------------------------- tables


def test_pipe_table_renders_header_and_rows(db: ModuleType) -> None:
    out = db.md_to_html("| a | b |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |")

    assert _tags(out, "th") == 2
    assert _tags(out, "td") == 4
    assert "<thead>" in out and "<tbody>" in out


def test_table_is_wrapped_for_horizontal_scroll(db: ModuleType) -> None:
    """A wide table must scroll inside its own box rather than widening the page."""
    out = db.md_to_html("| a |\n|---|\n| 1 |")

    assert '<div class="tbl"><table>' in out
    assert out.count("</table></div>") == 1


def test_table_column_alignment_is_honoured(db: ModuleType) -> None:
    out = db.md_to_html("| L | C | R |\n|:--|:-:|--:|\n| a | b | c |")

    assert 'style="text-align:left"' in out
    assert 'style="text-align:center"' in out
    assert 'style="text-align:right"' in out


# --------------------------------------------------------------------------- badges
#
# Badges are this tool's own convention, not markdown: a token at the head of a list
# item becomes a pill. They are opt-in per doc set, so a project declaring none sees
# every bracketed word as plain text.

_BADGES = {"DONE": ("badge done", "Done"), "NEXT": ("badge next", "Next")}


def test_status_token_becomes_a_badge_pill(db: ModuleType) -> None:
    out = db.md_to_html("- [DONE] finished work", badges=_BADGES)

    assert '<span class="badge done">Done</span>' in out
    assert 'class="lb"' in out
    assert "[DONE]" not in out


def test_a_badge_works_on_a_nested_item(db: ModuleType) -> None:
    out = db.md_to_html("- [DONE] top\n  - [NEXT] child", badges=_BADGES)

    assert '<span class="badge done">Done</span>' in out
    assert '<span class="badge next">Next</span>' in out


def test_unknown_bracket_token_is_left_alone(db: ModuleType) -> None:
    """So `[TODO]` in a sentence never becomes a pill by accident."""
    out = db.md_to_html("- [TODO] still ordinary text", badges=_BADGES)

    assert "[TODO] still ordinary text" in out
    assert "badge" not in out


def test_no_badges_are_rendered_when_none_are_declared(db: ModuleType) -> None:
    """Opt-in: a general project must not inherit another's status vocabulary."""
    out = db.md_to_html("- [DONE] finished work")

    assert "[DONE] finished work" in out
    assert "badge" not in out


def test_a_token_only_counts_at_the_head_of_an_item(db: ModuleType) -> None:
    out = db.md_to_html("- work that is [DONE] mid-sentence", badges=_BADGES)

    assert "[DONE] mid-sentence" in out
    assert "badge" not in out


def test_badge_config_accepts_a_bare_label_or_an_explicit_style(db: ModuleType) -> None:
    """A bare string derives the style from the token; the table form overrides it."""
    parsed = db._badge_styles(
        {"DONE": "Done", "BUILT": {"label": "Built", "style": "done"}}
    )

    assert parsed == {
        "DONE": ("badge done", "Done"),
        "BUILT": ("badge done", "Built"),
    }


def test_badge_config_absent_or_malformed_yields_nothing(db: ModuleType) -> None:
    assert db._badge_styles(None) == {}
    assert db._badge_styles("not a table") == {}


def test_a_list_item_holding_only_a_nested_list_is_not_a_badge_candidate(
    db: ModuleType,
) -> None:
    """An item with no text of its own has no inline token to inspect."""
    out = db.md_to_html("-\n  - child", badges=_BADGES)

    assert _tags(out, "ul") == 2
    assert "badge" not in out


def test_an_empty_outer_item_does_not_steal_its_child_s_badge(db: ModuleType) -> None:
    """The pill and its `lb` class must land on the same element — the child's.

    The scan for an item's own first inline token used to cross into nested items, so
    an outer item with no text of its own took the `lb` class while the pill rendered
    inside the child: two different elements styled for one badge.
    """
    out = db.md_to_html("-\n  - [DONE] child", badges=_BADGES)

    outer, marker, inner = out.partition("<ul>\n<li>\n<ul>")
    assert marker, out
    assert 'class="lb"' not in outer
    assert 'class="lb"' in inner


def test_a_token_markdown_already_claimed_as_a_link_is_not_badged(
    db: ModuleType,
) -> None:
    """A `[TOKEN]: url` definition makes `[TOKEN]` a reference link. That wins.

    Badging it as well rendered both the pill and the link — the pill announcing work
    done, immediately followed by the very text it was meant to replace.
    """
    out = db.md_to_html("- [DONE] x\n\n[DONE]: http://e.com", badges=_BADGES)

    assert '<a href="http://e.com">DONE</a>' in out
    assert "badge" not in out


def test_an_item_that_is_nothing_but_a_badge_renders_the_pill_alone(
    db: ModuleType,
) -> None:
    out = db.md_to_html("- [DONE]", badges=_BADGES)

    assert '<span class="badge done">Done</span></li>' in out


def test_a_badge_can_be_followed_immediately_by_markup(db: ModuleType) -> None:
    """The pill is prepended to the item's children, so what follows still renders."""
    out = db.md_to_html("- [DONE] **shipped**", badges=_BADGES)

    assert '<span class="badge done">Done</span><strong>shipped</strong>' in out


def test_an_empty_link_destination_is_left_empty(db: ModuleType) -> None:
    """Nothing to rewrite, and inventing a target would be worse than leaving it."""
    out = db.md_to_html("[a]()")

    assert '<a href="">a</a>' in out


# --------------------------------------------------------------------------- inline


def test_code_spans_are_not_interpreted(db: ModuleType) -> None:
    out = db.md_to_html("write `**not bold**` and `<html>` literally")

    assert "<strong>" not in out
    assert "&lt;html&gt;" in out


def test_double_backtick_code_spans_can_contain_backticks(db: ModuleType) -> None:
    """The hand-written converter mangled these, and one of its own doc pages used them.

    It rendered a double-backtick span with the inner text *actually bolded* — on the
    page whose sentence explained that code spans are protected from exactly that.
    """
    out = db.md_to_html("Stash `` `code` `` spans")

    assert "<code>`code`</code>" in out
    assert out.count("<code>") == 1


def test_markdown_links_are_rewritten_to_html(db: ModuleType) -> None:
    """Authored as `.md` so the sources read on GitHub; built as `.html`."""
    out = db.md_to_html("see [status](02-status.md) for detail")

    assert 'href="02-status.html"' in out


def test_cross_doc_set_links_are_repointed_at_html(db: ModuleType) -> None:
    out = db.md_to_html("[x](../../onboarding/markdown/04-wake-word.md)")

    assert 'href="../../onboarding/html/04-wake-word.html"' in out


def test_a_non_markdown_link_is_untouched(db: ModuleType) -> None:
    out = db.md_to_html("[a](https://example.com) and [b](diagram.png)")

    assert 'href="https://example.com"' in out
    assert 'href="diagram.png"' in out


def test_bold_and_italic(db: ModuleType) -> None:
    out = db.md_to_html("**bold** and *italic*")

    assert "<strong>bold</strong>" in out
    assert "<em>italic</em>" in out


def test_italics_nest_inside_bold(db: ModuleType) -> None:
    """Long a documented limit of the hand-written converter, now simply correct."""
    out = db.md_to_html("**bold with *italic* inside**")

    assert "<strong>bold with <em>italic</em> inside</strong>" in out
    assert "**" not in out


def test_html_in_prose_is_escaped(db: ModuleType) -> None:
    """Deliberate: rendering markup from a document would need trust or a sanitiser."""
    out = db.md_to_html("press <kbd>Esc</kbd> to stop")

    assert "&lt;kbd&gt;" in out
    assert "<kbd>" not in out


def test_images_render_as_images(db: ModuleType) -> None:
    out = db.md_to_html("![A diagram](diagram.png)")

    assert '<img src="diagram.png" alt="A diagram">' in out
    assert "!<a" not in out


def test_an_image_src_is_left_exactly_as_written(db: ModuleType) -> None:
    """No asset copying and no path rewriting: an image is a file, not a page.

    Unlike a page link it gets neither the `.md` swap nor the cross-set redirect, so the
    file has to sit where the *built* page looks for it.
    """
    out = db.md_to_html("![alt](assets/picture.png)")

    assert 'src="assets/picture.png"' in out


# ------------------------------------------------- what CommonMark brought with it
#
# Each of these rendered as visible literal text under the hand-written converter and
# was listed in the README as unsupported. They work now — CommonMark plus the table,
# strikethrough, footnote and task-list plugins — and these tests keep that list
# honest in the other direction.


def test_reference_style_links_work(db: ModuleType) -> None:
    out = db.md_to_html("[label][ref]\n\n[ref]: https://example.com")

    assert '<a href="https://example.com">label</a>' in out
    assert "[label][ref]" not in out


def test_footnotes_work(db: ModuleType) -> None:
    out = db.md_to_html("Text.[^1]\n\n[^1]: The note.")

    assert "footnote-ref" in out
    assert "The note." in out
    assert "[^1]" not in out.split("footnote-ref")[0]


def test_autolinks_work(db: ModuleType) -> None:
    out = db.md_to_html("<https://example.com>")

    assert '<a href="https://example.com">' in out


def test_strikethrough_works(db: ModuleType) -> None:
    out = db.md_to_html("~~gone~~")

    assert "<s>gone</s>" in out
    assert "~~" not in out


def test_task_lists_work(db: ModuleType) -> None:
    out = db.md_to_html("- [ ] todo\n- [x] done")

    assert out.count('type="checkbox"') == 2
    assert "checked" in out
    assert "[ ]" not in out


def test_two_space_hard_breaks_work(db: ModuleType) -> None:
    out = db.md_to_html("line one  \nline two")

    assert "<br>" in out


# ----------------------------------------------------------------------- prune_stale


def test_prune_removes_stale_pages(db: ModuleType, tmp_path: Path) -> None:
    """A renamed or deleted page's old HTML is cleaned up."""
    (tmp_path / "01-intro.html").write_text("current")
    (tmp_path / "99-old.html").write_text("stale")

    removed = db.prune_stale(tmp_path, {"01-intro.html"})

    assert removed == ["99-old.html"]
    assert not (tmp_path / "99-old.html").exists()


def test_prune_keeps_pages_in_the_keep_set(db: ModuleType, tmp_path: Path) -> None:
    kept = tmp_path / "01-intro.html"
    kept.write_text("current")

    db.prune_stale(tmp_path, {"01-intro.html"})

    assert kept.read_text() == "current"


def test_prune_leaves_non_html_files_alone(db: ModuleType, tmp_path: Path) -> None:
    """Only generated pages are candidates — never stylesheets or other assets."""
    css = tmp_path / "style.css"
    css.write_text("body{}")
    image = tmp_path / "diagram.png"
    image.write_text("not really a png")

    removed = db.prune_stale(tmp_path, set())

    assert removed == []
    assert css.exists()
    assert image.exists()


def test_prune_reports_every_removal_sorted(db: ModuleType, tmp_path: Path) -> None:
    """The build prints what it deleted, so a rename is visible rather than silent."""
    for name in ("09-shopping.html", "10-security.html", "11-approach.html"):
        (tmp_path / name).write_text("stale")

    removed = db.prune_stale(tmp_path, set())

    assert removed == ["09-shopping.html", "10-security.html", "11-approach.html"]


def test_prune_on_empty_directory_is_a_no_op(db: ModuleType, tmp_path: Path) -> None:
    """A fresh clone has no generated directory contents; that must not error."""
    assert db.prune_stale(tmp_path, {"01-intro.html"}) == []


# ------------------------------------------------------------------ page discovery


def _write_pages(d: Path, pages: dict[str, str]) -> None:
    for name, h1 in pages.items():
        (d / f"{name}.md").write_text(f"# {h1}\n\nBody.\n")


def test_discovery_takes_titles_from_each_file_s_first_heading(
    db: ModuleType, tmp_path: Path
) -> None:
    """The page list is derived from the directory, not hand-maintained."""
    _write_pages(tmp_path, {"01-first": "The First Page", "02-second": "The Second"})

    assert db.discover_pages(tmp_path) == [
        ("01-first", "The First Page"),
        ("02-second", "The Second"),
    ]


def test_discovery_puts_index_first(db: ModuleType, tmp_path: Path) -> None:
    """A cover page sorts after digits alphabetically, so it is special-cased."""
    _write_pages(tmp_path, {"02-b": "B", "index": "Cover", "01-a": "A"})

    assert [slug for slug, _ in db.discover_pages(tmp_path)] == [
        "index",
        "01-a",
        "02-b",
    ]


def test_discovery_applies_title_overrides(db: ModuleType, tmp_path: Path) -> None:
    """The sidebar label may differ from the page's H1 — usually a shorter form."""
    _write_pages(tmp_path, {"index": "Jarvis — Onboarding Guide"})

    pages = db.discover_pages(tmp_path, titles={"index": "Overview & contents"})

    assert pages == [("index", "Overview & contents")]


def test_discovery_falls_back_to_the_slug_when_a_page_has_no_heading(
    db: ModuleType, tmp_path: Path
) -> None:
    (tmp_path / "07-orphan.md").write_text("No heading here.\n")

    assert db.discover_pages(tmp_path) == [("07-orphan", "07-orphan")]


def test_explicit_order_overrides_discovery(db: ModuleType, tmp_path: Path) -> None:
    """A set that needs a hand-picked order can still declare one."""
    _write_pages(tmp_path, {"a": "A", "b": "B", "c": "C"})

    pages = db.discover_pages(tmp_path, order=["c", "a"])

    assert [slug for slug, _ in pages] == ["c", "a"]


def test_explicit_order_rejects_a_missing_page(db: ModuleType, tmp_path: Path) -> None:
    """Fail loudly rather than silently dropping a page from the guide."""
    _write_pages(tmp_path, {"a": "A"})

    with pytest.raises(SystemExit):
        db.discover_pages(tmp_path, order=["a", "nope"])


# ------------------------------------------------------------------ concatenation


def test_concat_turns_sibling_links_into_in_document_anchors(db: ModuleType) -> None:
    """In the single-file build, page links must jump within the document."""
    out = db.concat_links(
        "See [status](02-status.md).", {"02-status": "where-it-stands"}, {"02-status"}
    )

    assert out == "See [status](#where-it-stands)."


def test_concat_uses_the_real_page_list_not_a_naming_convention(
    db: ModuleType,
) -> None:
    """A page whose name isn't ``index`` or ``NN-slug`` must still be linked.

    The old regex guessed at the convention and would silently miss ``appendix.md``.
    """
    anchors = {"appendix": "the-appendix"}
    out = db.concat_links("[x](appendix.md)", anchors, {"appendix"})

    assert out == "[x](#the-appendix)"


def test_concat_leaves_links_to_other_doc_sets_as_links(db: ModuleType) -> None:
    """Only pages *in this set* become anchors; anything else stays a real link."""
    out = db.concat_links("[x](../../onboarding/markdown/04-wake-word.md)", {}, set())

    assert "](#" not in out


def test_concat_fixes_the_relative_depth_of_cross_set_links(db: ModuleType) -> None:
    """The concatenated file sits one directory above ``markdown/``.

    So every ``../../`` in a page source is one level too many once inlined. This is a
    depth rule, not a rule about any particular sibling doc set.
    """
    out = db.concat_links("[x](../../onboarding/markdown/04-wake-word.md)", {}, set())

    assert out == "[x](../onboarding/markdown/04-wake-word.md)"


def test_anchor_matches_github_heading_style(db: ModuleType) -> None:
    assert db.anchor("Where it stands") == "where-it-stands"
    assert db.anchor("Notes, lists & to-dos") == "notes-lists--to-dos"


# ------------------------------------------------------------------------- config


def _site(tmp_path: Path, body: str) -> Path:
    (tmp_path / "markdown").mkdir()
    _write_pages(tmp_path / "markdown", {"index": "Cover"})
    (tmp_path / "style.css").write_text("body{}")
    cfg = tmp_path / "site.toml"
    cfg.write_text(body)
    return cfg


def test_config_resolves_paths_relative_to_the_config_file(
    db: ModuleType, tmp_path: Path
) -> None:
    """So a set can be built from any working directory, or another repo entirely."""
    cfg = _site(
        tmp_path,
        'brand = "B"\ntitle_suffix = "T"\n'
        'source = "markdown"\noutput = "html"\nstyle = "style.css"\n',
    )

    site = db.load_site(cfg)

    assert site.source == tmp_path / "markdown"
    assert site.output == tmp_path / "html"
    assert site.style == tmp_path / "style.css"
    assert site.brand == "B"


def test_config_defaults_keep_the_common_case_empty(
    db: ModuleType, tmp_path: Path
) -> None:
    """A set with nothing unusual needs only its two brand strings."""
    cfg = _site(tmp_path, 'brand = "B"\ntitle_suffix = "T"\nstyle = "style.css"\n')

    site = db.load_site(cfg)

    assert site.source == tmp_path / "markdown"
    assert site.output == tmp_path / "html"
    assert site.titles == {}
    assert site.order is None
    assert site.standalone == []
    assert site.concat is None
