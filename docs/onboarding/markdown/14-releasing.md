# Releasing a version

**docsbuild is not published to a package index, so a release is a git tag.** Projects that
use it pin that tag; nothing else identifies a version. This page covers the numbering scheme,
how to cut a release, the two ways a project can consume one, and a trap that will otherwise
cost you an afternoon of testing the wrong code.

## Why there are versions at all

docsbuild is not on PyPI — the Python Package Index, the public repository that `pip install`
and `uv tool install` read from by default. It lives in a git repository instead, which means
there is no version number for anyone to look up and no "latest release" page.

What a consuming project pins instead is a **git tag**: a permanent, human-readable name for
one specific commit. So the tag *is* the release. If no tag existed, a project could only
depend on a branch, which silently changes underneath it every time someone pushes.

## The numbering scheme

Tags are **semantic versioning with a `v` prefix** — `v0.1.0`, `v0.2.0`, `v1.0.0`.

Semantic versioning ("semver") is the widespread convention of `MAJOR.MINOR.PATCH`, where each
position signals how disruptive a change is. Translated into what actually changes in this
tool:

| Bump | Means | Example |
|---|---|---|
| **patch** — `v0.1.1` | A fix. Same inputs, better output. | A renderer bug; a badge edge case. |
| **minor** — `v0.2.0` | Something new, nothing broken. | A new `site.toml` key; a new flag. |
| **major** — `v1.0.0` | Existing configs stop working. | Renaming or removing a config key. |

The `v` prefix is the dominant git convention and keeps tags obviously distinct from bare
numbers elsewhere in a repository.

**The tag and `pyproject.toml`'s `version` move together.** They are two records of the same
fact, and letting them disagree means the installed package reports one version while the tag
claims another — which is exactly the sort of thing nobody notices until they are debugging
something else.

## Cutting a release

Four steps, in this order:

```bash
# 1. Bump the version in pyproject.toml to match the tag you are about to create.
# 2. Commit it, along with whatever the release contains.
git commit -am "..."

# 3. Tag it. -a makes an *annotated* tag: a real object with an author, date and message,
#    rather than a bare pointer. Releases should be annotated.
git tag -a v0.1.0 -m "v0.1.0 — first tagged release"

# 4. Push the branch and the tag. Pushing a branch does NOT push tags.
git push origin main
git push origin v0.1.0
```

Step 4 catches people, because `git push` says `Everything up-to-date` about the branch and
says nothing at all about the tag you forgot. Until the tag is on the remote, no consumer can
resolve it — their lockfile resolves the tag server-side, not from your machine.

**A tag can point at a commit that is not on `main`.** If you tag while on a side branch, the
tag still pushes and still resolves for consumers, because they fetch the tag directly rather
than walking a branch. But the release then sits outside your mainline history until that
branch merges. It is not broken, and it needs no re-tagging once merged — a fast-forward makes
the tagged commit reachable from `main` automatically — but it is worth knowing you have done
it rather than discovering it later.

## How a project consumes a release

Two patterns, and the difference between them is not stylistic.

### As a standalone tool

```bash
uv tool install git+https://github.com/douglaslwatts/docsbuild@v0.1.2
```

`uv tool install` puts a command on your `PATH` in its own isolated environment. docsbuild's
own dependencies — `markdown-it-py` and friends — live in *that* environment and never appear
in the project you are documenting. This is the right choice if you just want the command.

### As a development dependency

Pinned in the consuming project's `pyproject.toml`:

```toml
[dependency-groups]
dev = ["docsbuild"]

[tool.uv.sources]
docsbuild = { git = "https://github.com/douglaslwatts/docsbuild.git", tag = "v0.1.2" }
```

Now `uv sync` installs it alongside the project's other dev tools, so anyone who can run the
tests can build the docs, with no separate install step. The trade-off is real though:
**docsbuild's dependencies do land in that project's dev dependency tree.** They stay out of
its runtime dependencies — a dev group is not shipped — but `markdown-it-py` becomes importable
in that project's environment. If that matters to you, use the standalone install instead.

A **lockfile** (`uv.lock`) records the exact commit the tag resolved to, so the build stays
reproducible even though a tag is, in principle, a movable label.

### Access, because the repository is public

Neither pattern needs credentials. The repository is public, so an `https://` clone works
everywhere without setup — your machine, a colleague's, a second laptop, or continuous
integration (a service that builds and tests a project automatically on every push). There are
no keys to distribute and nothing to configure.

SSH is still the right remote for *pushing*, since that does have to prove who you are:

```bash
git remote set-url origin git@github.com:douglaslwatts/docsbuild.git
```

That is a maintainer's concern, though. It never reaches consumers, who only ever read.

What can still fail is the **tag**. If it is missing from the remote — nearly always because it
was created locally and never pushed — the consumer's `uv sync` fails **for the whole project**,
tests included, not just the docs build. The error names the revision it could not find rather
than the package, so it points at the real cause.

## The trap: editing docsbuild while a project depends on it

**uv supports editable installs for local paths only, not for git sources.** An *editable*
install points the environment at your working tree, so every save takes effect immediately. A
git-pinned dependency instead gets a built copy — so editing your docsbuild checkout changes
nothing in the consuming project. That is correct behaviour, and it makes iterating painful:
every one-line renderer fix would need its own tag.

The way round it is to **shadow** the pinned copy in that project's environment:

```bash
uv pip install -e ../../docsbuild        # point the venv at your working tree
uv run --no-sync docsbuild --all         # edit, rebuild, repeat
uv sync                                  # put the pinned tag back
```

**`--no-sync` is mandatory, and this is the part that will waste your time.** A plain `uv run`
first reconciles the environment against the lockfile — normally a kindness — which
*uninstalls your editable copy and reinstalls the pinned release before your command runs*. The
build then succeeds, looks right, and tells you nothing about your change, because your change
was not in it. `--no-sync` means "run against the environment as it stands."

Two more things worth holding on to:

- The shadow touches **only** the virtual environment. `pyproject.toml` and `uv.lock` are
  untouched, so there is nothing to commit by accident, and any ordinary `uv run` or `uv sync`
  ends it.
- While shadowed you are building from **uncommitted** code. "It built fine for me" is not a
  statement about what anyone else will get until you have re-synced and rebuilt.

## Upgrading a project to a new release

```bash
# after bumping the tag in pyproject.toml
uv lock --upgrade-package docsbuild
```

Bumping the tag alone is not enough — the lockfile still pins the old commit until told
otherwise, and `uv sync` follows the lockfile.

---

[← Previous: How it got here](13-history.md) · [Contents](index.md)
