# `docsbuild init`

**A build needs a `site.toml`, and `init` writes one for a project that has none.** It
finds your doc sets by looking for markdown, fills in what it can infer, and is explicit
about what it cannot. This page covers what it produces, the rules it follows, and the
line it draws between inferring and guessing.

## The problem it solves

The build keys off configuration files, not directory names. So a repository that already
has `docs/guide/markdown/*.md` — real documentation, written long before anyone heard of
this tool — cannot build until a config exists. Writing that by hand is a small task, but
it is a small task you have to read the reference to do, and it stands between you and
seeing anything work.

## What a run looks like

Run it from the repository root; it finds the docs directory itself.

```
$ cd acme-widgets && docsbuild init

Using docs/ as the docs root.

Detected 2 doc set(s) in /home/you/acme-widgets/docs:
  development-plans         15 pages   (markdown/)
  guide                     19 pages   (markdown/)

Note: CONFIGURATION.md at the top level is not a doc set.
      If it should be a page of one of these, add a [[standalone]]
      entry to that set's config.

Wrote development-plans/site.toml
Wrote guide/site.toml
Wrote sites.toml

Note: BUILT has no matching style in the bundled stylesheet, so it
      renders as an unstyled pill. Add CSS for it, or point it at
      one of: done, next, later, planned, dropped — e.g.
        BUILT = { label = "Built", style = "done" }

Edit the brand strings, then build:
  docsbuild
```

Config is written **inside `docs/`**, never at the repository root, so `sites.toml` sits
beside the sets it names.

## What it infers

**The sets themselves,** by looking for markdown rather than for names — see
[Finding the project](08-finding-the-project.md) for the detection rules and the
directories it refuses to enter. Whether you have one set or five, and whatever they are
called, is not something it needs told.

**The layout of each set** — nested (`markdown/`) or flat. `source = "."` is written only
for a flat set, since nested is the default and writing defaults out is noise.

**Whether an index is needed.** A set in a subdirectory needs a `sites.toml`; a set at the
project root does not.

**The badge tokens your documents use.** `scan_badge_tokens` reads the markdown and
declares exactly the tokens it finds, most frequent first:

```toml
[badges]
DONE    = "Done"
PLANNED = "Planned"
DROPPED = "Dropped"
```

This applies the same rule the renderer does — a bracketed capitalised word at the head of
a list item — and skips fenced code, because a fenced example of the syntax is
documentation rather than a declaration. So what `init` writes is what will render.

That last inference exists because of a trap. [Badges](06-badges.md) are opt-in, so a
project whose docs are full of `[DONE]` would otherwise get a clean build in which every
badge had silently become plain text, with nothing in the generated config to suggest why.

## What it refuses to guess

**Brand strings are a guess, and say so.** The label comes from humanising the directory
name; the project prefix from the directory above the docs root, which for `docs/` inside
a checkout is usually the repository name. The generated file's first line tells you to
edit them.

**`[titles]`, `[concat]` and `[[standalone]]` cannot be inferred at all.** They encode
intent that simply is not in the filesystem: whether a page's sidebar label should differ
from its heading, whether you want a single-file export, whether a page belongs outside the
reading chain. Every generated config carries a **commented, filled-in example of each**,
with a note on what it does, so you can uncomment what you want without going back to the
reference.

**A badge style it does not recognise.** It names the token and shows how to point it at
one of the defined styles. Picking a colour would look deliberate and be wrong — the
token's meaning belongs to your project.

## The commented examples are uncommentable

The examples in a generated config are filled in for *that* set — the `[concat]` command
names the real set, and the `[[standalone]]` paths use `../` only when the set is in a
subdirectory. They are meant to be uncommented, so they have to be correct.

They also have to survive being uncommented **in bulk**, by an editor macro or a careless
`sed`. That is why **the prose never opens a line with a bracket or a `key =`.** It used
to: each explanation began with the block's own name, so `# [titles] overrides the label…`
sat directly above `# [titles]`, and uncommenting the paragraph produced broken TOML. A
test now uncomments every config-looking line in a generated file and asserts the result
still parses with all the features live.

## It does not overwrite

An existing `site.toml` is kept and reported as kept. `--force` opts in to replacing it.
Scaffolding that silently ate a hand-tuned config would be far worse than no scaffolding.

An existing `sites.toml` is kept too — you may have ordered it deliberately, or left a set
out on purpose. But silence there would be its own trap: a newly added set would get a
config and still never build. So any detected set missing from the index is **named**:

```
Note: newcomer not listed in sites.toml, so `--all` will skip it.
      Add it to `sets` there if you want it built.
```

## What it cannot reproduce

If you are copying a project whose docs already build a particular way, scaffolding a fresh
config will produce **different HTML**. `brand` and `title_suffix` appear in the sidebar
and `<title>` of every page, so a different guess diffs every file — and a missing
`[concat]` or `[[standalone]]` means those outputs are not produced at all.

To reproduce another project's docs exactly, **copy its `site.toml` files.** They are the
source of truth. `init` is for projects that do not have them yet, and the closing lines of
its own output say so.

---

[← Previous: Finding the project](08-finding-the-project.md) · [Contents](index.md) ·
[Next: Concatenation and standalone pages →](10-extras.md)
