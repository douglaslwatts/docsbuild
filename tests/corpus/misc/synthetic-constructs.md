# Every construct the converter supports

This page exists because the rest of the corpus is real documentation, and real
documentation turned out to contain **no nested lists and no images at all**. That left
the two constructs most recently fixed with no corpus coverage whatsoever, which is
exactly the blind spot the harness was built to remove.

Everything below is deliberately synthetic. Add to it whenever the converter learns
something new.

## Emphasis

Plain, *italic*, **bold**, and **bold with *italic* nested inside it** — the last of
which was a documented limitation until it wasn't.

Inline `code`, and `**not bold**` in backticks, which must stay literal.

## Nested lists

- Top level item
  - Second level
    - Third level, to prove recursion rather than a special case for one depth
  - Back to second level
- Another top-level item that wraps onto
  a continuation line, with **bold spanning the break**
  - and a child list after that continuation

1. Ordered at the top
   1. Ordered inside ordered
   2. A sibling
2. Back to the top level
   - An unordered child of an ordered parent

- [DONE] A badge on a top-level item
  - [NEXT] A badge on a nested item, which must still render as a pill

## Images

![A diagram with alt text](diagram.png)

An image ![inline in a sentence](icon.png) among prose.

## Tables with alignment

| Left | Centre | Right | Default |
|:-----|:------:|------:|---------|
| a | b | c | d |
| longer cell | x | y | z |

## Everything else

> A blockquote, with **bold** and a [link](index.md) inside it.

```python
# A fenced block. Nothing in here is interpreted:
# **not bold**, ![not an image](x.png), - not a list
```

---

A horizontal rule above this paragraph.
