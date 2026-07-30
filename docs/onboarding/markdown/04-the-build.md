# What a build actually does

A build is four steps. Two of them are obvious, one is easy to overlook, and the **order**
of the last two is a safety property rather than an implementation detail. The function is
`build_site`, and it is worth reading alongside this page.

## The four steps

1. **Read** every markdown file that discovery found. If one has vanished since it was
   discovered, stop immediately.
2. **Convert** each one to HTML and wrap it in the page layout — all in memory, nothing
   written yet.
3. **Delete** every `.html` file in the output directory that no longer has a markdown
   source.
4. **Write** the new pages.

Then, if the set asked for them, the optional extras: standalone pages and the
concatenated single file. Those are covered in [Concatenation and standalone
pages](10-extras.md).

## Step 1: fail fast

`read_sources` reads every page up front and raises if one is missing:

```python
raise SystemExit(f"missing markdown source: {md_path}")
```

This can only happen if a file disappears between discovery and reading — an editor
mid-save, a `git checkout` in another terminal. Rare, but the alternative is a site that
builds "successfully" with a page silently absent from it, which you might not notice for
weeks.

## Step 2: convert everything before touching the disk

Every page is rendered into a dictionary in memory:

```python
rendered = {
    f"{slug}.html": page_shell(...) for index, (slug, title) in enumerate(pages)
}
```

Nothing has been written at this point. That matters for step 3.

## Step 3: prune, and why it exists

`prune_stale` deletes any `.html` in the output directory that is not in the set of pages
about to be written.

Without this, renaming a page leaves its old output behind forever. Rename
`09-shopping.md` to `11-shopping.md`, rebuild, and `09-shopping.html` is still sitting
there: still opening in a browser, still turning up in a site search, still showing
content that no longer matches any source file. Nothing ever cleans it up, because a build
that only *writes* has no reason to look at what is already there.

The scope is deliberately narrow — `html_dir.glob("*.html")`, so:

- only files ending `.html`
- only files **directly inside** the output directory, not in subdirectories
- never the markdown, which lives above the output directory

Your `.md` files are never at risk. But note the corollary: if you point `output` at a
directory containing hand-written HTML, the build will delete it. With the default
`output = "html"` that cannot happen, because the directory holds nothing but generated
pages.

Every removal is printed. A rename that silently deleted a page would be exactly as bad as
one that silently kept a stale copy.

## Why deleting comes third and not first

This looks backwards. The natural instinct is to clear the output directory and then write
into it.

Consider what happens if the build crashes half-way through — a malformed file, a
permissions error, a disk full, an exception in a renderer rule:

- **Delete first, then convert:** the old pages are gone and the new ones were never
  written. You have no documentation at all, and you find out when someone opens a link.
- **Convert first, then delete, then write:** the crash happens during conversion, before
  anything on disk was touched. The existing site is exactly as it was.

By converting everything into memory before removing anything, a failure is guaranteed to
leave the previous build intact. The window between "delete" and "write" is a handful of
filesystem calls with no computation in it, which is about as small as it can be made
without writing to temporary files and renaming.

`write_pages` is where this ordering is enforced:

```python
def write_pages(html_dir: Path, rendered: dict[str, str]) -> list[str]:
    html_dir.mkdir(parents=True, exist_ok=True)
    removed = prune_stale(html_dir, set(rendered))
    for name, html in rendered.items():
        (html_dir / name).write_text(html)
    return removed
```

The function takes the fully-rendered pages as an argument, which makes the ordering hard
to get wrong: you cannot call it before rendering is finished, because you have nothing to
pass it.

## What a page is wrapped in

`page_shell` builds the document around a converted fragment:

- the **contents sidebar** (`toc`), with the current page marked `active`
- **Previous / Next buttons** (`nav`), above and below the article, derived from the page's
  index in the reading order
- the **`<title>`**, which is the page's title plus the set's `title_suffix`
- the **stylesheet**, copied in whole — see [Self-contained pages](07-self-contained-pages.md)
- a tiny script that applies your saved light/dark preference before the page paints, so
  switching themes does not flash

The first and last pages get a disabled placeholder instead of a dangling button:

```python
prev = pages[index - 1] if index > 0 else None
```

## Reading the output

A build prints what it did:

```
Built 19 pages into /home/you/acme/docs/guide/html
Removed 1 stale page(s): 09-shopping.html
```

The second line only appears when something was removed. That is the line to watch after a
rename — it is your confirmation that the cleanup happened, and the file it names is the
one that no longer has a source.

---

[← Previous: How pages are discovered](03-page-discovery.md) · [Contents](index.md) ·
[Next: The renderer →](05-the-renderer.md)
