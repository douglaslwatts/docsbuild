# Writing pages

A page is a markdown file in `markdown/`. That is the whole rule — there is no list of
pages to update, no index to register it in, no build manifest.

## How a page gets its place and its name

Three things are worked out from the file itself:

- **Whether it exists.** Every `*.md` in the source directory is a page.
- **Where it sits.** Pages sort by filename, except one named `index`, which is always
  first. Numbering files `01-`, `02-` makes filename order and reading order the same
  thing.
- **What it is called.** The page's own first `# heading` becomes its sidebar title.

So adding a page means creating the file. Nothing else is required.

## The markdown you can use

| You write | You get |
|---|---|
| `# Heading` through `###### Heading` | Headings, with anchor links on `##` and `###` |
| `- item` or `* item` | A bullet list |
| `1. item` | A numbered list |
| `` `code` `` | Inline code |
| ```` ``` ```` fenced blocks | A code block, with nothing inside it interpreted |
| `> quoted` | A blockquote |
| `**bold**`, `*italic*` | Bold and italic |
| `[label](page.md)` | A link, rewritten to `page.html` in the built site |
| `\| a \| b \|` pipe tables | A table that scrolls sideways if it is too wide |
| `---` on its own line | A horizontal rule |

Long list items may wrap onto indented continuation lines; they stay part of the item.

## Two traps

**Do not nest italics inside bold.** This does not render:

```markdown
- **The part *emphasised* inside bold.**
```

The pattern that finds bold text is "two asterisks, characters that are not asterisks,
two asterisks" — the inner `*emphasised*` breaks the match and the raw `**` shows up on
the page. Pick one or the other. This limit is deliberate and pinned by a test, so it
cannot quietly change.

**Write links as `.md`, not `.html`.** Point at the markdown file:

```markdown
See [Configuring the build](02-configuring.md).
```

The link then works when someone reads the source on GitHub, *and* in the built site,
because the builder rewrites the extension on the way out.

## Status badges

A list item beginning with a token you have declared renders as a coloured pill instead of
literal text:

- [DONE] Something finished, marked rather than deleted.
- [NEXT] The thing being worked on now.
- [LATER] Real, agreed, and not yet started.

Badges are **opt-in**: they come from a `[badges]` table in `site.toml`, so a project that
declares none sees every bracketed word as plain text. This guide declares `DONE`, `NEXT`,
`LATER` and `BUILT` — see [Configuring the build](02-configuring.md).

A token you have *not* declared is left alone, which is why writing `[TODO]` in a sentence
never becomes a badge by accident. Nor does a token mid-sentence: only one at the very
start of a list item counts.

---

[← Previous: Example guide](index.md) · [Contents](index.md) ·
[Next: Configuring the build →](02-configuring.md)
