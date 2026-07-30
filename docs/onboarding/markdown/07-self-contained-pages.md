# Self-contained pages

**The entire stylesheet is copied into every page the build writes.** Not linked — copied,
into a `<style>` tag in the `<head>`. This page explains what that means precisely, what it
costs, what it buys, and the one consequence that surprises people.

## What the output actually contains

Look in a built `html/` directory and you will find nothing but `.html` files. No CSS file,
no fonts, no JavaScript, no assets directory. Open one of those pages and search it:

- `<link rel="stylesheet">` — **zero**
- `<style>` blocks — **exactly one**
- `style="..."` attributes on elements — **zero**

That last one matters, and it is where the description "inline styles" would mislead. This
is not CSS sprayed onto individual elements. It is the whole stylesheet, selectors intact,
sitting in one `<style>` tag.

That distinction is not academic. Element-level inline styles cannot express media queries
or attribute selectors at all — light/dark theming would be impossible. The cascade, the
media query and the theme switch all behave exactly as they would with a linked
stylesheet. The only difference is where the bytes live. The bundled sheet has about 85
selector blocks, a `@media (prefers-color-scheme)` rule, and attribute selectors driving
the theme toggle; all of them survive intact.

## How it works

Two lines, in two places. `build_site` reads the stylesheet once per build:

```python
style = site.style.read_text()
```

and `_shell` embeds that string in the document:

```python
f"<style>{style}</style>\n{THEME_SCRIPT}\n</head>\n<body>\n"
```

Every page in the set gets the same string. `THEME_SCRIPT` is a very small script that
reads your saved light/dark preference and applies it *before the page paints*, so
switching themes does not produce a flash of the wrong one.

## What it costs

Duplication, and it is not trivial:

Measured on the guide you are reading, with the bundled stylesheet:

```
stylesheet             10 KB
one built page         19 KB   — the CSS is about half of it
15 pages in this set  152 KB   of duplicated CSS
```

Every page also re-parses that CSS, and a browser cannot cache it across pages the way it
would a single `style.css`.

## What it buys

Any single page is a complete document. Move it, email it, drop it on a USB stick, open it
from a random directory — it renders identically. There is no server, no relative-path
assumption, and no possibility of a missing asset.

For documentation read out of a checkout, that is the right side of the trade. The usual
failure mode of a linked stylesheet — you open `index.html` from disk, and it renders as
unstyled text because the CSS path assumed a server root — simply cannot happen.

If these pages were served over HTTP to many readers, a linked and cached stylesheet would
win instead. They are not, so it does not.

## The consequence that surprises people

**Editing the stylesheet and refreshing the browser does nothing.** The CSS is baked in at
build time. You have to rebuild:

```bash
uv run docsbuild --set onboarding
```

This catches everyone once. If a style change appears to have no effect, that is the
reason.

## Which stylesheet

Whichever the doc set names, and the default is *not* in your project:

```toml
style = "../style.css"    # your own
                          # omitted: the one bundled inside docsbuild
```

Omit the key and you get `src/docsbuild/style.css` from the installed package. That is what
makes a two-line configuration viable — a project with one doc set does not have to invent
a stylesheet before it can build anything.

The trade-off is worth stating: **omitting `style` means you inherit upstream styling.** If
docsbuild's bundled sheet changes, your pages change on the next rebuild. Naming your own
pins it. Neither is wrong; they are different choices about who owns the look.

Because the sheet is inlined either way, your built pages are self-contained regardless.
There is never a dangling reference to a file inside `site-packages`.

## If you are writing CSS for it

The classes the build produces, beyond ordinary markdown elements:

| Class | On | What it is |
|---|---|---|
| `.layout` | wrapper | the sidebar-plus-main grid |
| `.toc` | `<nav>` | the contents sidebar |
| `.toc a.active` | link | the current page in the sidebar |
| `.nav.top` / `.nav.bottom` | `<div>` | the Previous / Next button rows |
| `.prev` / `.next` | `<a>` or `<span>` | a button, or a disabled placeholder |
| `.brand` | `<a>` | the label at the top of the sidebar |
| `.tbl` | `<div>` | the horizontal-scroll wrapper around a table |
| `.badge` | `<span>` | a [status pill](06-badges.md), plus a style class |
| `li.lb` | `<li>` | an item carrying a badge, so its bullet is suppressed |

Theming uses CSS custom properties defined in `:root`, with a
`@media (prefers-color-scheme: dark)` block and `:root[data-theme="..."]` overrides that
the toggle sets. If you write your own sheet and want the theme switch to keep working,
those attribute selectors are the contract.

---

[← Previous: Status badges](06-badges.md) · [Contents](index.md) ·
[Next: Finding the project →](08-finding-the-project.md)
