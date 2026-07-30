# Onboarding guide

An in-depth, page-by-page explanation of how docsbuild works — the build, the renderer,
discovery, scaffolding, and the reasoning behind each. It is the place to send someone who
is going to change this code.

## Reading it

Read the markdown in `markdown/` (start at `index.md`), or build the HTML for the
browsable version with a sidebar and Previous / Next links:

```bash
uv run docsbuild --set onboarding
open html/index.html
```

`html/` is **generated and not tracked by git**, so a fresh clone has none until you build.

**This guide is built by the tool it documents.** That is deliberate: a change that breaks
the build stops these pages rendering, so the guide cannot rot silently past the point of
being buildable.

## Layout

- `markdown/` — the pages. **This is the source of truth**; never edit the generated HTML.
- `site.toml` — this set's configuration. It was written by `docsbuild init` and then
  edited, which is the workflow the guide describes.
- `../sites.toml` — the index naming this set.

## Editing it

1. Edit the relevant page(s) in `markdown/`.
2. Rebuild with the command above.

**Write for a competent developer new to this codebase.** A page should be readable end to
end by anyone from a junior to a principal engineer without external lookups. Explain
project-specific terms on first use *on each page* — doc set, chrome, token stream, core
rule, CommonMark — because each page has to stand on its own; assume the reader has not
read the others. Depth is fine, difficulty is not: go as deep as the subject needs, in
language that stays easy.

Prefer explaining *why* over restating *what*. The code says what it does; the guide is
where the reasoning lives, including the decisions that turned out wrong first.

## Adding a page

1. Create `markdown/<NN>-<slug>.md` starting with a `# Heading` — that becomes its sidebar
   title. Two digits, so filename order and numeric order agree.
2. Add it to the contents list in `markdown/index.md`.
3. Wire the footer links: the new page gets a `← Previous · Contents · Next →` line, and
   the page before it gains a `Next →` link.
4. Rebuild.

The sidebar and the Previous / Next buttons come from the directory automatically — only
the in-page footer line and the contents list are written by hand.

Avoid backticks in an `# H1`: the heading text is used verbatim in the sidebar, where
markdown is not rendered, so they show up as literal characters. If a page needs them, add
a `[titles]` override in `site.toml` — `09-init` does exactly that.

## Two things that will surprise you

**`ruff format` reformats the Python inside these pages.** Ruff formats fenced `python`
blocks in markdown, so a snippet you laid out by hand may come back re-wrapped. That is
mostly a good thing — the examples are guaranteed to be validly formatted — but it means
your spacing is not final. (`ruff check` does *not* lint them, so a snippet using
undefined names like `page_shell(...)` is fine.)

**Rebuild after editing the stylesheet.** The CSS is copied into every page at build time,
so editing `src/docsbuild/style.css` and refreshing the browser does nothing at all.
