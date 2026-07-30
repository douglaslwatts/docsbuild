# docsbuild — onboarding

*An in-depth tour of how this tool works, for someone who has never seen it.*

> **docsbuild turns a directory of markdown files into a browsable website.** You write
> `.md` files; it produces `.html` files with a contents sidebar and Previous / Next
> links. Every page it produces is self-contained — you can double-click one and it opens
> correctly, with no web server and no missing files.

This guide explains the whole program: what it does, why each piece works the way it does,
and where the surprises are. It assumes you know Python and have used markdown. It does
**not** assume you know anything about documentation tooling, static site generators, or
this project's history — everything else is explained as it comes up.

**Every page stands on its own.** You can read straight through with the Previous / Next
buttons, or jump to whichever page answers your question. Terms specific to this project
or its domain are explained the first time they appear on *each* page, so nothing depends
on you having read the others.

## Try it before you read about it

Nothing here will make much sense without seeing the output. It takes about a minute:

```bash
cd docsbuild
uv sync
uv run docsbuild --set onboarding
open docs/onboarding/html/index.html
```

That command just rebuilt the page you are reading. The tool documents itself with itself,
which is a deliberate check: if a change breaks the build, this guide stops rendering.

## Contents

1. [What it is, and what it deliberately isn't](01-what-it-is.md) — the shape of the whole
   program in one page, and the scope decisions behind it.
2. [Doc sets: the central idea](02-doc-sets.md) — the one concept everything else hangs
   off, and why the tool has no notion of "a guide" or "a plan".
3. [How pages are discovered](03-page-discovery.md) — where the page list, the reading
   order and the titles come from, given that none of them is written down.
4. [What a build actually does](04-the-build.md) — the four steps, and why the order of
   two of them is a safety property rather than an implementation detail.
5. [The renderer](05-the-renderer.md) — CommonMark via `markdown-it-py`, and the four
   custom rules that make it this tool rather than a library call.
6. [Status badges](06-badges.md) — the one feature that is pure invention, how it is
   implemented against a parser that knows nothing about it, and why it is opt-in.
7. [Self-contained pages](07-self-contained-pages.md) — why the stylesheet is copied into
   every page, what that costs, and what it buys.
8. [Finding the project](08-finding-the-project.md) — how the command works out what to
   build when you give it nothing to go on.
9. [`docsbuild init`](09-init.md) — the scaffolding command, what it can infer from a
   directory of markdown, and what it deliberately refuses to guess.
10. [Concatenation and standalone pages](10-extras.md) — the two optional outputs, both
    off by default, and what each is for.
11. [Configuration reference](11-configuration.md) — every key in `site.toml` and
    `sites.toml`, with defaults.
12. [How it is tested](12-testing.md) — two very different test strategies, why both
    exist, and the bug classes each one catches.
13. [How it got here](13-history.md) — the decisions that shaped the current design,
    including the ones that were wrong first.
14. [Releasing a version](14-releasing.md) — the tagging scheme, how a project pins a
    release, and the one trap that makes you test the wrong code.

---

[Next: What it is, and what it deliberately isn't →](01-what-it-is.md)
