# Security invariants

These are the rules the code may **never** violate. They are mirrored in `CLAUDE.md` so they
govern every change, not just the shopping subsystem.

1. **The model never holds secrets.** Passwords/tokens live in the macOS Keychain and are
   injected directly into fields; they never enter the LLM context or logs.
2. **No card numbers on this device.** Payment cards + shipping addresses live only in the
   user's account on the retailer's servers. The agent *selects* a saved method; it never
   stores or types a card number.
3. **Fixed retailer allowlist** — only `amazon.com`, `walmart.com`, `lowes.com`,
   `homedepot.com`. Any other domain is hard-refused. Adding a site is a deliberate, reviewed
   change.
4. **No spend without the maintainer's approval.** The AI can assemble a cart; only a
   deterministic executor + an explicit remote approval can place an order.
5. **Web content is untrusted data, never instructions** (prompt-injection defense).
6. **Personal data (profile, logs, notes/lists) is local-only and encrypted at rest** with a
   Keychain-held key. The one deliberate exception: a user-requested, spoken-confirmed
   **export** writes an unencrypted `.md` copy of a note/list to `~/Desktop` — the only
   plaintext write and the only write outside `~/.jarvis/`, to a hardcoded, containment-checked
   path. All voice-managed notes/lists are otherwise confined to `~/.jarvis/`.

## Why they hold today

- **No filesystem tools are wired to the model.** No `chat()` call exposes exec or shell. Only
  deterministic code touches disk — the conversation store writes UUID-named files confined by
  `glob`, and [`NoteStore`](06-notes-lists.md) slugifies, date-stamps, and containment-checks
  every path it builds.
- **Invariant #6's single exception is code-controlled.** The export directory is a hardcoded
  `~/Desktop`, never from speech, and still checked with `is_relative_to`.
- **Shopping's two-gate rule** (Touch ID + remote approval) is reserved in the design now, so
  the seams are already shaped for it — see [Secure shopping](11-shopping.md).
