# Roadmap & what's next

**High level:** the conversational core is built and works well. What remains is making it an
always-on appliance, hardening it, and adding the two big features that were deliberately
deferred — safe voice shopping and per-person personalization. This page sketches those so
you know where the seams are. The authoritative, detailed plan lives in the plan file
referenced by `CLAUDE.md`.

## Milestones

Development is incremental, milestone by milestone:

- **M0–M2 (done).** The text brain, the push-to-talk voice loop, and full hands-free
  operation with wake word, barge-in, and voice controls — everything this guide describes.
- **M3 — the father tests it.** Real sessions on the prototype, tuning wake-word
  sensitivity, listening patience (`trailing_silence_seconds`), answer length, voice, and
  speaking rate *to him*. This is the most important step: the whole point is that it works
  for one specific person.
- **M4 — port to a Mac Mini appliance.** An always-on, silent box that boots straight into a
  listening state with zero interaction: auto-login, never sleep, auto-start and
  crash-restart via `launchd`, a private self-hosted search (SearXNG), and a signed `.app`
  bundle that owns the microphone permission.
- **M5 — robustness.** Graceful offline messaging, health checks, and small high-value
  skills (time, reminders, news reading).
- **M6 — secure shopping.** The hardest, highest-stakes subsystem; ship last, test hardest.

## The secure shopping subsystem (M6)

The design principle: **the AI can assemble a cart, but only a deterministic executor plus
explicit human approval can spend money.** The safeguards, all mandatory:

- **Two independent gates on every purchase.** The father's **fingerprint (Touch ID)** proves
  he is physically present and authorizing; a trusted maintainer's **remote approval** proves
  the purchase is sanctioned. Neither replaces the other. **Voice is never an authorization
  factor** — a recording or a cloned voice must never be able to spend.
- **A fixed retailer allowlist** — only a few known, official sites — so he can never land on
  a scam listing.
- **The model never holds secrets.** Credentials live in the macOS Keychain; card numbers and
  addresses live only in his account on the retailer's servers. The agent *selects* a saved
  card; it never types one.
- **Web content is untrusted data**, so a malicious product listing cannot instruct a
  purchase. A **bounded virtual card** is the final backstop.

## Personalization & speaker identity (future)

Jarvis will eventually recognize *who* is speaking (a local voiceprint layer) to load that
person's profile — interests, preferred answer length and voice rate. Important boundaries,
reserved in the design now:

- Speaker identity is for **personalization only, never authorization**.
- The wake word does **not** identify anyone — "Hey Jarvis" works for everyone.
- An **unknown voice gets a full conversation but zero stored data**; a profile exists only
  after deliberate enrollment.

## Known deferred refinements

- **"Any speech" barge-in** needs acoustic echo cancellation; today interruption uses the
  wake word (see [Barge-in](11-barge-in.md)).
- **Answer latency** on search-heavy turns is dominated by the answer model's generation
  time — the next lever if it needs to be faster.

## Where this lives in the code

- The invariants that already constrain the code: `CLAUDE.md` (security section).
- Reserved seams: the `Protocol` interfaces in `interfaces.py` keep identity and new tools
  addable without reworking the core.
- The full milestone plan and history: the plan file referenced by `CLAUDE.md`.

---

[← Previous: Notes & lists](16-notes-and-lists.md) · [Contents](index.md) · [Next: How the docs are built →](18-how-the-docs-are-built.md)
