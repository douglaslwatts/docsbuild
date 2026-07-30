# Roadmap & milestones

Development is incremental, milestone by milestone. Completed milestones are kept here and
marked done — the plan is a running record, not a to-do list that erases its history.

| # | Milestone | State |
|---|---|---|
| Step 0 | Scaffold + first red/green cycle | Done |
| M0 | Conversation brain (text only) | Done |
| M1 | Voice loop (push-to-talk) | Done |
| M2 | Hands-free + controls (wake word, barge-in) | Done |
| M3 | **The father tests it — tune to him (most important)** | **Next** |
| M4 | Port to Mac Mini; signed `.app`; `launchd` auto-start; SearXNG | Later |
| M5 | Robustness & niceties (offline messaging, health checks, skills) | Later |
| M6 | Secure shopping subsystem (built last, tested hardest) | Later |

## The milestones in words

- [DONE] **M0–M2.** The text brain, the push-to-talk voice loop, and full hands-free operation
  with wake word, barge-in, and voice controls. Plus everything layered on since: memory,
  conversation-flow polish, and the [notes/lists subsystem](06-notes-lists.md).
- [NEXT] **M3 — the father tests it.** Real sessions on the prototype, tuning wake-word
  sensitivity, listening patience (`trailing_silence_seconds`), answer length, voice, and
  speaking rate *to him*. This is the most important step: the whole point is that it works for
  one specific person. Every audio path is still unconfirmed by ear.
- [LATER] **M4 — port to a Mac Mini appliance.** An always-on, silent box that boots straight
  into a listening state with zero interaction: auto-login, never sleep, auto-start and
  crash-restart via `launchd`, a private self-hosted search (SearXNG), and a signed `.app`
  bundle that owns the microphone permission. The packaging spine — bundle, signing, `launchd`,
  and the hardware the Mini needs — is designed in
  [Packaging & the appliance](09-packaging.md); SearXNG is deliberately deferred out of it.
- [LATER] **Proposed alongside M4 — spoken update reports, voice-controlled restart, and an
  always-locked screen.** Written up in [Proposed: updates & locked screen](10-updates-and-lock.md)
  and **still being thought out** — recorded so the reasoning and the dead ends survive, not
  because it is committed.
- [LATER] **M5 — robustness.** Graceful offline messaging, health checks, and small high-value
  skills (time, reminders, news reading).
- [LATER] **M6 — secure shopping.** The hardest, highest-stakes subsystem; ship last, test
  hardest. See [Secure shopping](11-shopping.md).

## Personalization & speaker identity (future — HIGH effort)

- [LATER] Identify *who* is speaking to load the right profile (interests, recurring topics,
  preferred voice-rate / answer-length). **Personalization only, never authorization.** It
  builds **on top of** Step 2's persistence (adds a `user_id` dimension); the dependency runs
  one way only. Needs a new local voiceprint model (SpeechBrain ECAPA-TDNN / Resemblyzer), an
  enrollment flow, and a match threshold that needs live tuning.

Boundaries reserved now: the wake word does **not** identify anyone ("Hey Jarvis" works for
everyone); an **unknown voice gets a full conversation but zero stored data**, with no silent
enrollment ever.
