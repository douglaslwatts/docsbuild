# What it is, and what it deliberately isn't

**docsbuild reads a directory of markdown files and writes a directory of HTML files.**
That is the whole job. This page describes the shape of the program end to end, then the
scope decisions — the things it refuses to do, and why refusing them is the point.

## The one-sentence version

Point it at a directory containing markdown. It works out which files are pages, what
order they go in, and what each is called; converts each to HTML; wraps each in a page
layout with a contents sidebar and Previous / Next buttons; and writes the results
somewhere alongside.

```
docs/guide/                       docs/guide/
  site.toml         docsbuild       site.toml
  markdown/         ────────►       markdown/
    index.md                          index.md
    01-setup.md                       01-setup.md
                                    html/
                                      index.html
                                      01-setup.html
```

## What a "self-contained page" means

Most site generators produce a directory of HTML files plus a stylesheet, some fonts, and
maybe JavaScript, all linked together. Open one of those HTML files directly from disk and
it usually renders unstyled, because the links to those other files assume a web server.

docsbuild instead **copies the entire stylesheet into every page it writes**, inside a
`<style>` tag. The result is that each page is one complete file. Double-click it, email
it to someone, move it to another machine — it looks the same, with no server involved.

The cost is that every page carries its own copy of the CSS, so the pages are bigger and a
browser cannot cache the stylesheet across them. For documentation read out of a checkout,
that trade is clearly worth it. [Self-contained pages](07-self-contained-pages.md) goes
into the detail.

## The parts, and where they live

Everything is in one file, `src/docsbuild/__init__.py`, in these groups:

| Group | What it does | Key functions |
|---|---|---|
| **Rendering** | Markdown to an HTML fragment | `_renderer`, `md_to_html` |
| **Page chrome** | Wraps a fragment in the page layout | `toc`, `nav`, `page_shell`, `standalone_page` |
| **Discovery** | Works out the page list from the directory | `discover_pages`, `first_h1` |
| **Build** | Reads, renders, prunes, writes | `build_site`, `read_sources`, `write_pages`, `prune_stale` |
| **Config** | Reads `site.toml` into a frozen dataclass | `load_site`, `SiteConfig` |
| **Location** | Works out what project you mean | `find_root`, `find_docs_root`, `site_configs` |
| **Scaffolding** | Writes config for a project that has none | `detect_sets`, `init_project` |

*Chrome* is the standard term for the furniture around a page's content — in this case the
sidebar, the title, and the navigation buttons. It has nothing to do with the browser.

One file is a deliberate choice, not laziness. The whole program is about 1,200 lines
including its docstrings, it has no internal layering worth enforcing, and keeping it in
one file means the entire tool can be read top to bottom in one sitting. Splitting it into
a package is easy later, and should wait until there is a reason.

## What it deliberately does not do

Each of these is a decision, not a gap:

**No themes or templates.** There is one stylesheet and one page layout. If you want a
different look, edit the CSS. Making the layout pluggable would mean inventing a template
language or adopting one, and every consumer would then have to learn it.

**No plugins.** Nothing loads code from your project. The behaviour you get is the
behaviour in this file, which means reading this guide is sufficient to know what a build
will do.

**No search index, no navigation config, no versioning, no sidebars-within-sidebars.**
Those are the features that make a documentation site into a documentation *platform*, and
each one adds configuration that every user then has to understand.

**No raw HTML in your markdown.** Writing `<kbd>Esc</kbd>` in a page renders those angle
brackets as visible text, not as an element. Allowing HTML through would mean either
trusting every document completely, or shipping a sanitiser — and a sanitiser is a large
dependency that has to be kept current against new attacks. Escaping is the honest default
for a tool whose input might come from anywhere.

**No asset copying.** If you write `![diagram](picture.png)`, the tool emits an `<img>` tag
pointing at `picture.png` and does nothing else — it will not find that file and copy it
next to your built page. You have to put it where the built page will look.

## What it does do, that a markdown library alone would not

If the job were only "markdown to HTML", you would use `markdown-it-py` directly in three
lines. The value here is the surrounding work:

- **Discovery.** No page list to maintain. Add a file, it appears in the sidebar and in
  the reading order. See [How pages are discovered](03-page-discovery.md).
- **Reading order.** Sidebar, Previous / Next buttons, and a coherent sequence, all derived
  from the same source.
- **Cleanup.** Renaming a page deletes the stale output. Without that, the old page keeps
  working in a browser and turning up in searches, showing content that no longer exists
  anywhere in the source.
- **Links that work in both places.** You write links to `.md` files, so they resolve when
  someone browses the source on GitHub; the build rewrites them to `.html`.
- **Zero-config start.** Two lines of configuration, or none at all if you let
  [`docsbuild init`](09-init.md) write them.

## Who it is for

A project that wants its documentation written in plain markdown, kept in the repository
next to the code, and rendered into something readable — without adopting a toolchain,
learning a template language, or adding a build dependency to the project itself.

If you want the full apparatus — search, versioned docs, API autodoc, themes — use Sphinx
or MkDocs. They are better at that, and this tool is not trying to compete with them.

---

[← Previous: Overview](index.md) · [Contents](index.md) ·
[Next: Doc sets →](02-doc-sets.md)
