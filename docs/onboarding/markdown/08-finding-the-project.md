# Finding the project

Type `docsbuild` with no arguments and something has to work out what you meant. This page
explains that search, the directories it refuses to look in, and the two bugs the original
version had — both of which produced *wrong* results rather than errors, which is the worse
failure.

## The command line

```
docsbuild                      build every set in the project found from here
docsbuild --set NAME           build one named set
docsbuild --config PATH        build one site.toml directly
docsbuild --root DIR           use DIR as the project root instead of searching

docsbuild init                 write config for every doc set found here
docsbuild init --force         replace existing config instead of keeping it
```

`--config` is the unambiguous form: you name the file, nothing is searched.

## The search, when you give it nothing

`find_root` walks **upwards** from your working directory, the way `git` finds a
repository. At each level it checks for a `sites.toml` or a `site.toml` — and also glances
**down** into a conventional documentation directory: `docs/`, `doc/`, `documentation/`.

So all of these work:

```bash
cd acme-widgets            && docsbuild    # the repository root
cd acme-widgets/docs       && docsbuild    # the docs root
cd acme-widgets/src        && docsbuild    # a sibling directory
cd acme-widgets/docs/guide && docsbuild    # inside a doc set
```

Two precedence rules resolve the ambiguity:

- **Config at a level beats a `docs/` inside it.** If you are standing somewhere that is
  itself configured, that is the answer.
- **A nearer level beats a farther one.** The walk stops at the first match going up.

`--root` skips the upward walk entirely and uses the directory you name — but still steps
into its `docs/` if that is where the project lives. So `--root ~/acme` and
`--root ~/acme/docs` both work and resolve to the same place.

The downward glance is what makes running from a repository root sensible, and it has to
happen at *every* level of the upward walk rather than only at the start. Without that,
`cd src && docsbuild` would fail even though `../docs/sites.toml` exists two steps away —
and the error would suggest configuring `src/`, which is precisely wrong advice.

## Directories the search will not enter

Scanning skips:

- anything whose name starts with `.` — `.git`, `.venv`, `.pytest_cache`, `.tox`
- a deny-list of dependency and build trees: `node_modules`, `__pycache__`, `venv`,
  `dist`, `build`, `target`, `vendor`, `site-packages`, `htmlcov`

This is not tidiness. Without it, `.pytest_cache/README.md` is a markdown file in a
subdirectory, and detection dutifully reported `.pytest_cache` as a documentation set.
`init` would have written a `site.toml` **inside your pytest cache**. A vendored tree is
worse: `node_modules` can hold thousands of markdown files, none of them yours.

The rule lives in `_scannable`.

## How detection decides what is a doc set

`detect_sets` applies three rules in order:

1. `root/markdown/` exists → **the root itself is the set**, and the only one.
2. Otherwise, **every subdirectory holding markdown** is a set — nested
   (`sub/markdown/*.md`) or flat (`sub/*.md`).
3. Otherwise, loose `*.md` at the root make it a **single flat set**.

Rule 1 returning exclusively is forced by the config format, not by preference.
`sites.toml` names sets by *subdirectory*, so a set living at the root cannot be listed in
an index sitting in that same directory. A project cannot mix the two, so detection has to
choose, and an explicit `markdown/` directory is the unambiguous signal.

**Rule 3 coming last is the important one**, and it was originally first.

## The bug that made rule 3 last

The original rule was "markdown at the root wins over scanning subdirectories" — added so
that a single-set project's own pages would not be mistaken for a directory of separate
sets. Reasonable, and far too greedy.

A documentation root very commonly holds one loose `.md`: a README, a changelog, a
reference page kept outside the reading chain. With rule 3 checked first, that **one file**
made the whole directory look like a one-page doc set, and the real sets beneath it were
never scanned:

```
$ detect_sets(voice-companion/docs)
  name=''  source='.'  pages=1        # <- just CONFIGURATION.md
```

`init` then wrote a config describing that single file and missed two complete doc sets.
Not an error — a confident, wrong answer.

Loose files at a documentation root are genuinely ambiguous: they are as likely to be a
README as a page. So they now count only when there is nothing better, which is what
"rule 3 last" means. When real sets are found alongside a loose file, `init` **names the
file it passed over** and suggests `[[standalone]]` if it should be part of a set —
because silently ignoring it would be the same class of mistake as silently consuming it.

## The related bug, one level up

A second, subtler version of the same thing. `_as_set` decides whether a single directory
is a doc set — and it had the same greedy rule that `detect_sets` had just been fixed for.

At a repository root, `docs/` contains `CONFIGURATION.md`, so `_as_set` called `docs` a
one-page flat set. Which meant `docs` was never recognised as the *container* of two real
sets.

The fix is the same rule in both places: **a directory that holds doc sets is a container,
not a set.** Fixing the symptom at one depth and leaving identical logic wrong at the other
is what let it through, and it is worth remembering as a pattern — when you fix a rule,
check whether the same rule exists somewhere else.

## When nothing is found

The error distinguishes two different problems, because they have different fixes:

```
… found markdown but no config (onboarding, development-plans).
Run `docsbuild init` here to write one.
```

versus:

```
no sites.toml or site.toml in … or any parent directory —
run this inside a docs project, or pass --root/--config
```

The first means "your documents are here, they just are not configured". The second means
"there is no documentation here at all". Collapsing them into one message would send you
looking in the wrong place.

---

[← Previous: Self-contained pages](07-self-contained-pages.md) · [Contents](index.md) ·
[Next: docsbuild init →](09-init.md)
