# Packaging & the appliance (M4)

**High level:** turn the development checkout into a signed, notarized `Jarvis.app` that owns its
microphone permission, starts itself at boot, and survives rebuilds. Design settled; no code yet.

> The bundle is not polish. On an appliance with no screen and no sighted user, a microphone
> permission that can be silently revoked is an **unrecoverable failure**, so the signed identity
> is a *reliability* requirement.

Jarvis today is `uv sync && uv run jarvis-voice` from a terminal. Three separate things are blocked
behind that: the [proposed voice-controlled restart](10-updates-and-lock.md), the always-locked
screen posture, and M6 shopping — all of which need a stable app identity and hands-free boot.

Scope for this milestone is the **packaging spine only**. SearXNG is deliberately deferred: it is
independent work and blocks nothing.

## Definition of done

1. `Jarvis.app` builds reproducibly from a clean checkout with one command.
2. It is Developer ID–signed and notarized, and `spctl` accepts it.
3. It holds a **microphone** TCC grant that survives a reboot **and a rebuild + reinstall**.
4. `launchd` starts it at login and restarts it if it crashes.
5. A full power cycle returns to a listening appliance with zero interaction.

## Step 0 — prove the permission story first

Everything else here is ordinary work that is **worthless if TCC doesn't hold**. Before any real
effort, build a ~30-line stub app that opens the microphone, records one second, and exits. Bundle,
sign, notarize and `launchd`-load it exactly as Jarvis will be, then verify the grant is attributed
to **Jarvis** (not Terminal, not Python), survives a reboot, and — the one that matters — survives a
**rebuild and reinstall** under the same Developer ID.

Two things are already known to be wrong and must be fixed first:

- **No signing identity is installed.** `security find-identity -v -p codesigning` reports **0 valid
  identities**; the Developer ID certificate has to be in place before anything else.
- **The current mic grant is attached to a disposable interpreter** — a uv-managed CPython under
  `~/.local/share/uv/python/…`, ad-hoc/linker-signed with no Team ID, on a shared cache path that
  `uv` will replace on its next upgrade. That fragile identity is precisely what the bundle exists
  to eliminate.

**Go / no-go:** if the grant does not survive a rebuild, stop and reconsider the posture rather than
build toward a machine that can go deaf with no way to recover.

## Bundle shape

The running process must **be** the bundle's main executable or TCC attributes the grant elsewhere,
so the interpreter goes inside:

```
Jarvis.app/Contents/
  Info.plist            CFBundleIdentifier com.jarvis.voice, NSMicrophoneUsageDescription,
                        LSBackgroundOnly (no Dock icon), LSMinimumSystemVersion
  MacOS/Jarvis          the embedded python-build-standalone interpreter
  Resources/
    lib/python3.x/...   the venv's site-packages, vendored
    prompts/spoken_style.txt
    config.default.yaml
    openwakeword/       models baked in at BUILD time
```

`uv`'s managed Pythons *are* python-build-standalone builds and are designed to be relocatable, so
the interpreter can be copied in. A hand-rolled bundle is preferred over py2app/PyInstaller: this
native dependency set (`mlx`, `mlx-whisper`, `onnxruntime`, `sounddevice`/PortAudio, `piper-tts`,
`numpy`) is exactly what those tools handle worst, and a hand-rolled layout keeps the signing story
legible.

**The constraint that shapes everything: any write inside a signed bundle invalidates its
signature.** Nothing mutable may live in the `.app`.

## The work

- [PLANNED] **Relocate the paths** — the only real source change. `cli.py` and `voice/voice_cli.py`
  both derive a `_PROJECT_ROOT` from `__file__` and hang `config.yaml`, `prompts/spoken_style.txt`
  and `models/piper` off it. A new `paths.py` resolves resources from `Contents/Resources` when
  bundled and the repo root in a checkout, with all mutable state under the existing `~/.jarvis`
  root already used by `NoteStore` and `ConversationStore`. On first run it **seeds**
  `~/.jarvis/config.yaml` from a bundled default, so config survives an app update.
- [PLANNED] **`scripts/build_app.py`** — clean staging venv, vendor the interpreter and
  site-packages, bake the wake-word models, stamp `Info.plist` from `pyproject.toml`, then
  `codesign --options runtime` inner-out, `notarytool submit --wait`, `stapler staple`, and
  `spctl --assess` as the build's own gate.
- [PLANNED] **Model provisioning, split by where it can legally write.** The openWakeWord ONNX
  models currently download into **site-packages** at startup — a write that would break the
  signature — so they are **baked in at build time**. The Piper voice moves to
  `~/.jarvis/models/piper` (already parameterized). Whisper keeps its Hugging Face cache. Every
  first-run download must complete **before the screen locks for good**.
- [PLANNED] **Two `launchd` agents** — `com.jarvis.ollama.plist` running `ollama serve`, and
  `com.jarvis.voice.plist` running the bundle, both `RunAtLoad` + `KeepAlive`, logging into
  `~/.jarvis/logs/`. GUI-session **agents, not daemons**: the mic grant is per-user and needs a user
  session. `launchd` gives no ordering guarantee between the two, so the startup check must **retry
  with backoff and speak** if the backend is unreachable.
- [PLANNED] **`scripts/install.sh`** — Ollama install and model pulls → copy to `/Applications` →
  first launch **while someone can see the screen**, to answer the mic prompt → pre-warm the Piper
  and Whisper downloads → seed config and Keychain entries → bootstrap the agents → apply the
  appliance settings → reboot and verify by ear. The appliance settings come **last**, because once
  the screen locks for good nothing needing a click can ever be approved again.

## External dependencies — Ollama is the only one

Audited against the installed venv. Everything else ships inside its own wheel:

| Dependency | Native payload | Verdict |
|---|---|---|
| `sounddevice` | bundles `libportaudio.dylib` | self-contained |
| `piper-tts` | bundles `espeak-ng-data` + `espeakbridge.so` | self-contained |
| `openwakeword` | onnxruntime wheel; models download into site-packages | wheel fine, models baked at build |
| `mlx-whisper` | Metal is OS-provided; weights from the HF cache | self-contained |
| **Ollama** | separate binary + service + ~29 GB of models | **the one true external dependency** |

**The app does not install Ollama — the install script does.** Installing it needs admin rights and
lays down a system service; an app that prompted for admin at launch is exactly what a locked-screen
appliance can never satisfy. Install the bare `ollama` binary rather than `Ollama.app`, which brings
a login item and its own auto-updater — two things that could change under the appliance unnoticed.
Jarvis only *checks*, and must **say so aloud** when the backend is missing: `voice_cli.main`
currently `print`s that warning, which is invisible on a machine nobody looks at.

**Near-miss worth recording: ffmpeg.** `mlx_whisper.load_audio()` shells out to the `ffmpeg` CLI —
but only when handed a *path*. `VadRecorder.record()` returns a **numpy array** and
`MlxWhisperTranscriber.transcribe` passes it straight through, so that branch never runs. ffmpeg is
present on the dev MacBook via Homebrew for unrelated reasons, which is exactly how this would have
gone unnoticed until a clean Mini.

- [DROPPED] **Shipping ffmpeg in the bundle.** Nothing calls it; the Homebrew binary is a 431 KB
  stub linking 18 Cellar dylibs so it cannot simply be copied; that build is `--enable-gpl
  --enable-version3`, carrying GPLv3 obligations for a component nothing executes; and it would add
  x264/x265/vpx/av1/openssl parsers to an always-on appliance. The risk it insures against is a
  *future code change*, and the honest fix is a test asserting the transcriber is called with an
  array rather than a `str`, plus building with `/opt/homebrew/bin` off `PATH`. If a later feature
  genuinely needs to decode audio, reach for `soundfile`/libsndfile or AVFoundation first.

## Hardware sizing

Measured as real RSS on the M2 Max / 64 GB prototype, not estimated:

| Component | Measured | Note |
|---|---|---|
| `qwen3.6:27b-mlx` (brain) | **17.7 GB** | weights-bound — identical at `num_ctx` 8192 and 262144 |
| `llama3.2` (router) @ Ollama default | **16.0 GB** | a 2 GB model; the 131,072-token KV cache is the rest |
| `llama3.2` @ `num_ctx: 8192` | **2.9 GB** | same model, 13 GB cheaper |
| Whisper `large-v3-turbo` (MLX) | ~1.5 GB | resident only during a transcribe |
| Piper + openWakeWord + Python | ~1 GB | |

Steady state with both models resident is **~37 GB as configured**, or **~24 GB with the router
context capped** — plus macOS.

- [NEXT] **Cap the router's context.** `llm/ollama_client.py` sets `options` to `{"temperature":
  …}` and nothing else, so every model inherits Ollama's default context and reserves a KV cache
  sized for it. Threading a `num_ctx` through from config is a small change that is invisible on a
  64 GB prototype and decisive on the Mini — it is the difference between needing 48 GB and 64 GB.
  Worth doing **before the machine is bought**.
- [PLANNED] **Buy 48 GB** (64 GB if the budget allows — it matches the prototype, so nothing tuned
  at M3 changes when it moves). 32 GB works *only* with the cap above and leaves 1–2 GB of margin,
  too thin for a box nobody can see or log into. 24 GB and below forces an ~8B brain — a permanent
  quality cut for the one person this exists for. Note that 48/64 GB are M4 Pro–only options.
- [PLANNED] **1 TB storage.** Ollama models are already ~29 GB, and `memory.store_max_gib: 25.0`
  permits the conversation store to reach 25 GB by itself. 512 GB would work and would need
  watching — a failure mode worth removing from an unattended machine.
- [DROPPED] **iPad or iPhone as the host.** Not a headroom problem, an architectural one: Ollama has
  no iOS/iPadOS port and iOS forbids the long-lived server process it needs; third-party apps get no
  always-on background microphone, so **"Hey Jarvis" cannot exist**; per-app memory limits are a few
  GB against a 17.7 GB brain; and this Python codebase with its native wheels has no iOS runtime.
  The sane mobile story is a **thin client** streaming audio to the Mini — a post-M6 idea, not a
  host.

## Risks

1. **The mic grant doesn't survive a rebuild** → Step 0 exists to find this out cheaply.
2. **Native deps don't relocate** (`mlx`, `onnxruntime`, PortAudio dylib paths) → surfaced by the
   spike; fallback is vendoring with explicit `install_name_tool` fixups.
3. **Notarization rejects the embedded interpreter** → hardened runtime plus whatever JIT /
   unsigned-memory entitlements `mlx` needs; discovered at first submission.
4. **A deaf Jarvis behind a locked screen** — if the grant is ever lost, nobody can answer the
   re-prompt. Mitigated by the Developer ID identity plus a **startup self-check that speaks aloud**
   when the microphone is unavailable. Worth building regardless.
5. **A dependency that only works because of Homebrew** — ffmpeg was the near-miss; the build must
   be validated with `/opt/homebrew/bin` off `PATH`, or the next one surfaces only on the Mini.
