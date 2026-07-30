# The goal & constraints

**High level:** the real goal is *not* an autonomous operating system — that was only ever a
means. It is to give a man who was blinded in the 1980s, before personal computers, and has
never used one independently, a machine he can operate **entirely by voice**. He loves to
learn; the dream is that he asks questions aloud, has an AI search the web, and gets spoken,
information-dense but concise answers — and holds long, natural conversations.

This reframes the project from a risky, self-modifying autonomous OS into a **reliable,
private, voice-first appliance**. For a machine someone depends on daily, reliability and
polish beat autonomy. He only ever touches the voice layer — never the OS or the screen.

## Non-negotiable design constraints (his stated needs)

1. **Voice is the entire interface** — hands-free; he cannot use a keyboard or a screen reader.
2. **Concise but complete answers** — dense with real information, no padding; spoken, so even
   tighter than text. Lead with the answer, then offer to go deeper.
3. **Patient listening** — waits through his pauses, never cuts him off mid-sentence.
4. **Barge-in** — he can interrupt a reply by speaking.
5. **Privacy-first** — brain, speech, and all personal data stay local. Only web-search
   *queries* leave the device, via a privacy-respecting search.
6. **Voice online shopping (later, hardest)** — assemble a cart by voice, but **spending
   requires both his fingerprint (Touch ID) and the maintainer's remote approval**, paid via a
   limited virtual card.

## What this means for every decision

Because one specific person depends on this, the plan consistently favors:

- **Determinism over model judgment** wherever a wrong guess is costly — routing, freshness,
  command parsing, and every filesystem path are decided in tested code, not left to the LLM.
- **Confirmation over silent action** — because he can't glance at a screen to catch a
  mis-hear, anything that writes or deletes is read back and waits for a spoken "yes."
- **Honesty over smoothness** — Jarvis must never *pretend* it did something (saved a file,
  reorganized a list) it didn't do; a false confirmation is worse than an apology.

These three principles recur throughout the pages that follow.
