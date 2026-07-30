# The renderer

**Markdown conversion is done by `markdown-it-py`, a conformant CommonMark parser.**
docsbuild adds four custom rules on top. This page explains what the library gives you,
what the four rules do, and why the tool no longer converts markdown itself.

*CommonMark* is the formal specification of markdown. Plain markdown was never precisely
defined, so different tools disagreed about edge cases; CommonMark pins the behaviour
down. A conformant parser means what renders on GitHub renders here.

## What you can write

Everything in CommonMark: headings, paragraphs, lists nested to any depth, emphasis, code
spans and fences, blockquotes, images, links (both inline and reference-style), autolinks,
hard line breaks, horizontal rules.

Plus four extensions, enabled in `_renderer`:

| Extension | Syntax | Source |
|---|---|---|
| Tables | `\| a \| b \|` with `\|:---:\|` alignment | markdown-it core |
| Strikethrough | `~~gone~~` | markdown-it core |
| Footnotes | `[^1]` and `[^1]: the note` | `mdit-py-plugins` |
| Task lists | `- [ ]` and `- [x]` | `mdit-py-plugins` |

## What you cannot write: raw HTML

The parser is created with `html=False`, so `<kbd>Esc</kbd>` renders as visible text
rather than as an element.

This is deliberate and worth keeping. Letting markup through would mean either trusting
every document the tool is ever pointed at, or shipping an HTML sanitiser. A sanitiser is
a substantial dependency that has to be maintained against new bypasses, and getting it
wrong means a documentation build becomes a way to inject script into a page. Escaping is
the honest default.

## The four custom rules

These are the reason this is a tool and not a three-line library call. Each is a *render
rule* — a function markdown-it calls when it reaches a particular kind of token.

### 1. Links: `.md` becomes `.html`

You write links pointing at markdown files:

```markdown
See [configuration](11-configuration.md).
```

That link works when someone reads the source on GitHub. The `link_open` rule rewrites the
extension so it also works in the built site.

The same rule handles **cross-set links** — a link from one doc set into another, written
through the other set's source directory:

```
../../plan/markdown/01-goal.md   →   ../../plan/html/01-goal.html
```

It does this by replacing `/{source}/` with `/{output}/`, using the *current* set's
directory names. That is a real limitation worth knowing: if two sets in one project use
different directory names, links between them need writing by hand. The converter is only
given one set's configuration, so it has no way to know the other's.

### 2. Headings: anchor ids

The `heading_open` rule adds an `id` to `<h2>` and `<h3>` elements, using `slug` to turn
the heading text into a URL-safe string. "Where it stands" becomes
`id="where-it-stands"`.

These exist so an in-page contents panel can link to sections — used by [standalone
pages](10-extras.md) — and so you can link to a section from elsewhere. Only `h2` and `h3`
get them: deep enough to be useful, shallow enough that the ids stay meaningful.

### 3. Tables: a scroll wrapper

`table_open` and `table_close` wrap every table in `<div class="tbl">`, which the
stylesheet makes horizontally scrollable. A wide table then scrolls inside its own box
instead of making the whole page scroll sideways — the failure mode where one oversized
table ruins the layout of an otherwise fine page.

### 4. Status badges

The one feature that is pure invention rather than a markdown extension. It gets [its own
page](06-badges.md).

## Why this is not hand-written any more

It used to be. docsbuild originally carried its own markdown converter — about 225 lines,
a line-scanner that dispatched on the shape of each line. It was well tested and it worked
for the documents it was written against.

It was replaced because "works for the documents it was written against" is not the same
as "works". Probing it with markdown a general user would plausibly write found **three
cases producing wrong output**, as opposed to unsupported output:

| Written | Produced |
|---|---|
| `![A diagram](diagram.png)` | `!<a href="diagram.png">A diagram</a>` — a stray `!` and a link instead of an image |
| `- top` / `  - child` | `<li>top - child</li>` — the child absorbed into its parent, marker and all |
| `**bold with *italic* inside**` | visible `**` on the page |

Those were fixed by hand. But the deeper problem remained: reference links, footnotes,
autolinks, strikethrough, task lists and hard breaks all rendered as literal text, and
completing the subset meant hand-writing a CommonMark parser — several hundred more lines,
still not conformant at the edges, maintained as a permanent side quest.

The clinching argument was about dependencies. The no-dependency rule existed because the
builder used to live *inside* the repository it built, where "a fresh clone can rebuild
the docs with nothing installed" was a real promise. As a tool you *install*, that promise
does not apply: `uv tool install` puts it in its own isolated environment, so your
project's dependency tree is untouched and whether docsbuild needs a parser is invisible
to you.

That holds exactly as stated for the standalone install. A project that instead pins
docsbuild as a **development dependency** does take its dependencies into that project's
dev group — they stay out of what it ships, but `markdown-it-py` becomes importable there.
Both consumption patterns are set out in [Releasing a version](14-releasing.md).

So the constraint that made a hand-written converter necessary had already stopped
applying. The swap deleted 225 lines and made the markdown correct.

It also fixed a bug nobody had noticed. The old code matched code spans with
`` `([^`]+)` `` — single backticks only — so a double-backtick span like
`` `` `code` `` `` was mangled. On the page that documented the converter, a sentence
explaining *"code spans are pulled out first so nothing inside them is reinterpreted"* was
rendering its own example of `**not bold**` as actually bold. It had been wrong for
months. See [How it is tested](12-testing.md) for why no test caught it.

---

[← Previous: What a build actually does](04-the-build.md) · [Contents](index.md) ·
[Next: Status badges →](06-badges.md)
