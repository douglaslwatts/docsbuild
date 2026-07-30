# How it got here

The current design makes more sense if you know what it replaced. This page is the short
version of how docsbuild came to exist and why several decisions look the way they do —
including the ones that were wrong first.

None of this is required reading. It is here because "why is it like this?" is usually a
better question than it sounds, and the answers are not always guessable from the code.

## It started as a script inside another repository

docsbuild began as `docs/docsbuild.py` in a project called voice-companion — a private
voice assistant, entirely unrelated to documentation tooling. That project had two sets of
documentation, an onboarding guide and a development plan, and wanted them rendered as
browsable HTML without adopting a toolchain.

Before that, it was **two** scripts: a `build.py` in each documentation directory, mostly
duplicated. Every converter bug had to be found and fixed twice. Consolidating them into
one shared program was the first real step, and it is why the concept of a
[doc set](02-doc-sets.md) exists at all — two sets forced the question of what varies
between them, and the answer became `site.toml`.

## Being extracted forced the interesting questions

When the program was lifted out into its own project, the surprise was how little was
actually tied to its original home: grepping about 600 lines for anything project-specific
found **three docstring lines and nothing in the code**. The config layer had already done
the work.

But *decoupled from any one repository* turned out not to mean *droppable onto one*. Three
things had to change, and each was discovered by trying it:

**The project root could not be found.** `--root` defaulted to the module file's own
directory, which after installation resolves inside `site-packages`. That became the
upward-and-downward search in [Finding the project](08-finding-the-project.md).

**Every project had to supply a stylesheet,** because `style` defaulted to a file next to
the config. Bundling one inside the package is what makes a two-line config possible.

**Nothing knew how to configure a project that had none.** That became
[`docsbuild init`](09-init.md).

## Three bugs that shaped the design

Each of these produced a confident wrong answer rather than an error, which is the failure
mode worth designing against.

**A single stray markdown file hid every real doc set.** Detection checked the root for
markdown *first*, so one `CONFIGURATION.md` at a documentation root made the whole
directory look like a one-page set — and the two real sets beneath it were never scanned.
Loose files at a root are now a last resort, checked only when nothing better is found.

**Scanning entered directories it had no business in.** `.pytest_cache/README.md` was
reported as a documentation set; `init` would have written a config inside a pytest cache.
Hence the [exclusions](08-finding-the-project.md).

**The badge rule stole badges from nested items,** applying the styling class to one
element and the pill to another. Found by chasing test coverage, not by looking at pages.

## The hand-written converter, and why it went

For most of its life this tool converted markdown itself — about 225 lines, a line-scanner
dispatching on the shape of each line. It was tested, it was documented, and its
limitations were written down honestly: no nested lists, no footnotes, no reference links,
italics-inside-bold known broken.

Two things ended it.

First, probing it with markdown a general user would plausibly write found cases producing
**wrong** output rather than merely unsupported output — images rendering as links with a
stray `!`, nested list items absorbed into their parents. "Documented limitation" is a
reasonable position; "renders your image as a broken link" is not.

Second, and more decisive: **the constraint that justified it had quietly expired.** The
no-dependency rule existed because the builder lived *inside* the repository it built,
where a fresh clone rebuilding docs with nothing installed was a real promise. As an
installed tool, that promise does not apply — install it standalone and your project's
dependency tree is untouched by what docsbuild needs. (Pin it as a *development*
dependency instead and its dependencies do reach that project's dev group; see
[Releasing a version](14-releasing.md).) Nobody had noticed the constraint stop applying,
because nobody had reason to re-examine it.

Once that was clear, the choice was obvious: hand-write several hundred more lines toward a
CommonMark parser that still would not be conformant at the edges, or depend on one that
is. The swap deleted 225 lines and made the markdown correct.

The [testing strategy](12-testing.md) is what made it safe. Because the corpus harness
asserts invariants rather than exact HTML, it survived the swap unchanged and could verify
it — 34 of 35 real pages rendering byte-identical visible text, and the one difference
being a bug the old converter had been shipping for months.

## What is still deliberately absent

Rejected on purpose, so that "why doesn't it…" has an answer:

- **Themes, templates, plugins.** Each turns a tool into a platform, and a platform has
  configuration everyone must learn.
- **Raw HTML passthrough.** Would require trusting every input or shipping a sanitiser.
- **Asset copying.** Would need rules about what counts as an asset and where it goes.
- **Recursive page discovery.** One-dimensional reading order is what makes a single
  Previous / Next chain coherent.

## Things a future change should know

- **A rule that exists in two places must be fixed in both.** The greedy-loose-markdown bug
  was fixed in `detect_sets` and left wrong in `_as_set`, one level up, where it caused the
  same failure a week later.
- **Semantic assertions outlive implementations.** The tests that pinned exact HTML all had
  to be rewritten; the ones asserting properties did not.
- **Verification scripts are code too**, and had bugs three separate times here — see the
  end of [How it is tested](12-testing.md).
- **This guide is built by the tool it documents.** If a change breaks the build, these
  pages stop rendering, which is a check worth keeping.

---

[← Previous: How it is tested](12-testing.md) · [Contents](index.md) ·
[Next: Releasing a version →](14-releasing.md)
