# Constraints & caveats

Deliberate calls and known limits — recorded so they are never mistaken for oversights.

## Voice & audio

- **Wake phrase is openWakeWord's built-in `hey_jarvis`.** The companion was renamed so identity
  and wake word match. `hey_jarvis` is now the **permanent** wake word; custom wake-word
  training is **dropped from M3** (revisit only if a truly custom name is wanted).
- **The mid-sentence interrupt is the wake word.** While Jarvis speaks, the only listener is the
  wake-word barge-in monitor — deliberately wake-word-only so it doesn't fire on Jarvis's own
  voice (no acoustic echo cancellation yet). So "Hey Jarvis" cuts it off; the "stop talking"
  phrases can't be *heard* mid-sentence. An attempt to at least halt playback when the phrases
  *are* captured didn't work and sits on the unmerged `make_stop_phrases_active` branch.
  Phrase-based interrupt needs a custom "stop" model or AEC — deferred.
- **`listening.trailing_silence_seconds: 3.0` is the father's to tune at M3** — he is
  long-winded. The config comment stays as a flag.
- **`mlx-whisper` pins numpy down to 2.4.6** (via numba). The suite passes.

## Weather, identity & multi-user

- **Home/default weather location is deferred.** "What's the weather tomorrow?" with no city is
  *not* solved yet — a configurable home location ties to the future per-voice **profile** work.
- **Voice identity is personalization only — never an authorization factor.** A wrong voiceprint
  costs a slightly-wrong answer style; a wrong auth factor costs money. **Touch ID guards money;
  voice never does.**
- **Multi-shopper isolation is an open design problem.** Touch ID proves *a* enrolled finger was
  presented, not *whose* — macOS won't say. **Single-shopper is the supported case.**

## Appliance & platform

- **FileVault off + auto-login (recommended trade-off).** Hands-free boot is incompatible with
  FileVault's pre-boot password. Residual risk (physical theft) is already contained by the
  limited virtual card + no-spend-without-approval gate. Keeping FileVault on is valid but costs
  a remote unlock on every cold boot.
- **Automatic microphone request deferred to M4** — done properly when Jarvis is packaged as a
  signed `.app` bundle with `NSMicrophoneUsageDescription`. In dev, macOS auto-prompts on first
  mic access. Note this is a **reliability** requirement, not polish: the grant is currently
  attached to a disposable uv-managed interpreter path. See
  [Packaging & the appliance](09-packaging.md).
- **M4 hardware note:** the Mac Mini has **no built-in Touch ID**; shopping needs an Apple Magic
  Keyboard with Touch ID on the target machine. Prototype biometrics on the MacBook; settle
  appliance hardware at M4/M6.
- **Memory sizing is set by the two resident Ollama models**, measured at ~37 GB together as
  configured today — so the Mini needs **48 GB** (64 GB preferred), and **iPads and iPhones cannot
  host Jarvis at all** for architectural reasons, not performance ones. Both are worked through in
  [Packaging & the appliance](09-packaging.md).
- **The always-locked-screen posture is proposed, not decided.** The bullet above records the
  currently-shipping trade-off; a stricter posture (auto-login followed by a permanent lock, so a
  sighted visitor cannot get in) is written up in
  [Proposed: updates & locked screen](10-updates-and-lock.md) with its open questions. It would
  **reverse** the screensaver advice above, so the two should not be read as agreeing.

## Latency

- **Answer latency** on search-heavy turns is dominated by the answer model's generation time —
  the next lever if it ever needs to be faster.
