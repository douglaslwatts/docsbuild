# Status badges

**A declared token at the head of a list item renders as a coloured pill.** This is the
one feature that is entirely this tool's invention — markdown has no syntax for it and no
extension provides it. This page covers what it is for, how it is implemented against a
parser that knows nothing about it, why it is off by default, and the two bugs that
implementation had.

## What it looks like

You write:

```markdown
- [DONE] The voice loop, end to end.
- [NEXT] Live testing with a real user.
- [PLANNED] Packaging as a signed application.
```

You get three list items, each opening with a small coloured pill reading Done, Next or
Planned.

## What it is for

A document that records the state of work — a development plan, a roadmap, a migration
checklist — needs to mark things finished. The obvious approach is to delete finished
items, but then the document stops being a record of what was decided and why. Marking
instead of deleting keeps the history legible, and the badge makes the status scannable
rather than something you have to read for.

## They are opt-in, and that matters

Declare the tokens your documents use, per doc set:

```toml
[badges]
DONE    = "Done"
NEXT    = "Next"
BUILT   = { label = "Built", style = "done" }
```

**With no `[badges]` table, nothing is special.** `[DONE]` stays as literal text.

That default is deliberate. Badges started life as a hardcoded dictionary of six tokens —
one project's vocabulary, baked into a general tool. Any other project would have
inherited a status language it never chose, and a document writing `[DONE]` for some
entirely different reason would have found it silently turned into a green pill.

The trade-off is a trap in the other direction: a project whose docs *already* use these
tokens gets a clean build in which every badge has quietly become plain text.
[`docsbuild init`](09-init.md) closes that by scanning your markdown and writing the table
for you, declaring exactly the tokens you actually use.

### The two config spellings

```toml
DONE  = "Done"                                # colour from the lowercased token
BUILT = { label = "Built", style = "done" }   # borrow another token's colour
```

A bare string is the label, and the pill's colour comes from the lowercased token — `DONE`
uses the `done` style. The table form is for a token whose lowercase is not one of the
styles the stylesheet defines, or one that should reuse another's colour.

The bundled stylesheet defines five: `done`, `next`, `later`, `planned`, `dropped`. A
token pointing at anything else renders as an unstyled pill until you add the CSS —
`init` will warn you by name when that is about to happen. It does not guess a colour,
because a guess would look deliberate and be wrong.

Parsing lives in `_badge_styles`, which normalises both spellings into
`token -> (css class, label)`.

## How it is implemented

markdown-it has no concept of this, so it cannot be a parser extension. It is a
**transform over the token stream after parsing** — a *core rule*, in markdown-it's
terms — plus a render rule for the new token type it introduces.

*Tokens* here are markdown-it's intermediate representation: parsing produces a flat list
of them (`bullet_list_open`, `list_item_open`, `inline`, and so on), and rendering walks
that list. Working at this level means the rule sees the document's real structure rather
than guessing from text.

`_badge_rule` walks the tokens looking for each `list_item_open`, finds that item's own
first `inline` token, and if its content starts with a declared token:

1. strips the token text from the content and from the first text child
2. prepends a synthetic `badge` token carrying the CSS class and label
3. adds `class="lb"` to the `<li>`, which the stylesheet uses to suppress the normal bullet

A matching render rule turns the `badge` token into `<span class="badge done">Done</span>`.

## Where it only fires

A token counts **only at the very start of a list item**. Writing "work that is [DONE]
mid-sentence" leaves it as text. So does `[TODO]` if you have not declared `TODO`. Both
are important: a bracketed word in prose must never become a pill by accident.

## The two bugs, both found by chasing test coverage

Neither would have been caught by looking at output, and both are worth knowing about
because they say something about the shape of the problem.

### An outer item stealing its child's badge

The scan for "this item's first inline token" walked forward through the token list until
it hit `list_item_close`. But a list item containing only a nested list has no inline
token of its own — so the scan **crossed into the nested item** and found *its* content.

```markdown
-
  - [DONE] child
```

The pill rendered inside the child, correctly. But `class="lb"` was applied to the
**outer** `<li>`. Two different elements styled for one badge: the outer item lost its
bullet for no reason, and the inner one kept a bullet it should not have had.

The fix is a boundary list — the scan now also stops at `bullet_list_open` and
`ordered_list_open`, so an item only ever considers its own content.

### A badge fighting a reference link

Markdown has *reference-style links*: `[LABEL]` becomes a link if a matching
`[LABEL]: url` definition appears anywhere in the document. So this:

```markdown
- [DONE] shipped

[DONE]: https://example.com/changelog
```

…parses `[DONE]` as a link. The badge rule matched on the raw text anyway, and rendered
**both** — a pill announcing "Done", immediately followed by the very link text it was
meant to replace.

The fix: if the item's first child is not a plain text token, markdown has already claimed
that syntax for something else, and markdown's meaning wins.

Both bugs were found the same way — by pushing coverage to 100% and asking what input
would reach an unexercised branch. Neither is likely in practice. Both would have been
baffling to debug from a screenshot.

---

[← Previous: The renderer](05-the-renderer.md) · [Contents](index.md) ·
[Next: Self-contained pages →](07-self-contained-pages.md)
