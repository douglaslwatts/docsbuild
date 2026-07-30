# Secure shopping (M6)

**High level:** the highest-stakes subsystem, and the reason the whole project is built the way
it is. It ships **last** and is tested **hardest**. Design is locked; no code yet.

> Core rule: **the AI can assemble a cart; only a deterministic executor plus the maintainer's
> approval can spend.** Built as an isolated, deterministic subsystem — *not* another AI skill.

## The safeguards (all mandatory)

- **Two independent gates, both required.** **Touch ID** answers *"is the father physically here
  and authorizing?"*; the maintainer's **push approval** answers *"is this purchase
  sanctioned?"*. Neither replaces the other. **Voice is never an authorization factor** — it is
  spoofable by a recording, the TV, or a cloned voice.
- **Fixed retailer allowlist** — `amazon.com`, `walmart.com`, `lowes.com`, `homedepot.com`. Any
  other domain is hard-refused, so he can never land on a scam listing.
- **The model never holds secrets.** Retailer credentials live in the Keychain (ideally under a
  biometry `SecAccessControl` ACL), injected into fields, never in the model context or logs.
- **No card numbers on the device.** Cards + addresses live only in the user's retailer account;
  the agent *selects* a saved method (verified by last-4), never types one.
- **Bounded payment** — a dedicated/virtual card with per-transaction and monthly caps, the
  final backstop.
- **Prompt-injection defense** — product titles and reviews are untrusted data; the approval
  gate and executor sit outside the model, so a malicious listing cannot instruct a purchase.
- **Graceful failure for a blind user** — 2FA / step-up / biometry lockout **escalates to the
  maintainer**, never strands the father at a dead end.

## How it stays contained

The subsystem is deterministic code with the model kept strictly to cart *assembly*. The two
gates, the allowlist, the credential handling, and the bounded card are each independent — any
one failing aborts the purchase. These constraints are already written into
[the security invariants](12-security.md) so the rest of the codebase honors them before the
subsystem is even built.
