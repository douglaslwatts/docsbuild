# Example guide

*A complete docsbuild project, in four files.*

> This directory is the smallest thing that builds. Copy it, rename it, replace the
> prose, and you have your own documentation site.

Everything you see here comes from three markdown files and a nine-line `site.toml`. The
sidebar on the left, the Previous / Next buttons, the styling, and this page's position
at the front of the reading order were all worked out from the directory — none of them
is configured anywhere.

## Build it

```bash
cd example
docsbuild
open html/index.html
```

## Contents

1. [Writing pages](01-writing-pages.md) — the markdown you can use, and the two traps.
2. [Configuring the build](02-configuring.md) — every `site.toml` key.

---

[Next: Writing pages →](01-writing-pages.md)
