# Proposed: updates, restart & the locked screen

> **Status: PROPOSED — still being thought out.** Nothing here is committed. It is written down so
> the reasoning survives, the dead ends are not re-derived, and the open questions are visible. Some
> of it depends on [packaging (M4)](09-packaging.md) landing first; parts of it may not be built at
> all.

**High level:** three related ideas — keep the screen locked at all times without costing Jarvis any
function, let Jarvis *say* when macOS updates are waiting, and let him restart the machine on
request.

## The always-locked screen

The goal, in the maintainer's words: if his father has a sighted visitor, there should be **no
chance of them getting into the computer** without being let in deliberately. The machine sits
behind a lock screen permanently; Jarvis answers questions, searches the web, and takes notes from
behind it.

This works because **a locked screen does not suspend the session** — audio playback and dictation
keep running, so the voice loop is unaffected.

- [DROPPED] **No auto-login at all.** The obvious reading of "never unlocked" — don't log in until a
  human does — is a dead end. Microphone access is governed by TCC, which is **per-user and needs a
  live GUI session**; a pre-login process cannot hold a mic grant. PPPC profiles delivered by MDM
  can only ever **deny** Camera and Microphone, never pre-grant them. A pre-login Jarvis is
  therefore deaf by construction.
- [PLANNED] **Auto-login, then lock immediately and permanently.** Delivers the same security
  property — a visitor faces a password prompt — while giving Jarvis the logged-in session its
  microphone grant requires.

### What actually performs the lock

Deliberately **appliance configuration, not Jarvis code**, so the security property does not depend
on Jarvis having started correctly:

```
defaults write com.apple.screensaver askForPassword -int 1
defaults write com.apple.screensaver askForPasswordDelay -int 0
defaults -currentHost write com.apple.screensaver idleTime -int 60
sudo pmset -a sleep 0 disksleep 0 standby 0     # SYSTEM sleep off; display sleep is fine
sudo systemsetup -setcomputersleep Never
```

Optionally a third agent, `com.jarvis.lock.plist`, running `open -a ScreenSaverEngine` at boot so
the unlocked window is sub-second rather than `idleTime`. It must be **`RunAtLoad` only, never
`KeepAlive`** — with `KeepAlive`, `launchd` would relaunch the screensaver the instant anyone
dismissed it and the machine could never be unlocked at all. The `idleTime` setting stays regardless
as the fallback that carries the property if the agent fails.

**Note:** `CGSession -suspend`, which most guides still recommend for this, **no longer exists in
macOS 26** — verified, the binary is gone.

### Consequences and open questions

- **FileVault stays off.** Auto-login requires it, and hands-free boot requires auto-login. This
  posture defends against a visitor, not a thief; the disk-at-rest exposure is the trade-off already
  recorded in [Constraints](07-constraints.md). Jarvis's own data stays encrypted with Keychain-held
  keys regardless.
- **A Magic Keyboard with Touch ID becomes a hardware requirement**, not an accessory — it is how
  his father admits a visitor. Jarvis **cannot** type the password: Secure Input blocks synthetic
  keystrokes at the lock window, by design. The maintainer's escape hatch is
  `sudo killall ScreenSaverEngine` over SSH.
- **This reverses earlier advice.** An earlier pass recommended the screensaver off with
  `askForPassword 0`; this posture inverts it. Noted so the contradiction is not mistaken for drift.
- **Open question — does Touch ID work on the first unlock after a reboot?** Apple requires a
  password rather than Touch ID for the first *login* after a restart. But under auto-login that
  login has already happened automatically, so whether the first *screen unlock* accepts Touch ID is
  genuinely unclear. If it does not, nobody can be admitted until someone types the password once
  per reboot. **This needs testing during the M4 spike** — it is the question most likely to sink
  the posture.
- **Open question — does this survive daily life?** The posture has not been tried with the person
  who has to live behind it. Worth deferring until after M3.

## Reporting available updates

- [PLANNED] **Unblocked — needs nothing from M4.** `softwareupdate -l --no-scan` returns in ~2.7 s
  with no privileges required (a full scan is far too slow for a voice turn), and `sw_vers` gives
  the current version. That is fast enough to answer "are there any updates?" inside a normal
  exchange, plus a once-a-day mention piggybacked on the existing end-of-exchange hook in
  `voice_cli.run_hands_free_loop`. This is the piece most likely to ship first, and it could ship
  independently of everything else here.

## Installing updates and restarting

- [LATER] **Blocked on packaging.** A restart command is meaningless — and untestable — until Jarvis
  reliably comes back by itself. It should stay gated behind an `autostart-verified` marker that the
  maintainer creates only after hearing a full reboot cycle work end to end.
- [PLANNED] **Tier 1 before Tier 2.** macOS `AutomaticallyInstallMacOSUpdates` is already on, so the
  real gap is *knowing* and *triggering the restart* — not installing. Announce-and-restart is worth
  building before anything that stores an admin password.
- [PLANNED] **Only same-major updates install.** 26.5.2 → 26.6 yes; 26.x → 27.0 refused and escalated
  to the maintainer. A major upgrade can change the login window, the audio stack, or the TCC
  database — none of which a blind user should meet alone.
- [DROPPED] **Shutdown.** Excluded at every layer — no enum member, no argv template, and the
  allowlist rejects `-h now`. A powered-off machine is one his father cannot turn back on
  unaided, and there is no recovery by voice from a box that is off. Jarvis counter-offers a
  restart instead.

### Subprocess safety (the part that must not be got wrong)

If any of this is built, it goes behind one narrow choke point:

- A single `system/runner.py` as the **only** `subprocess` import in the codebase.
- A **closed-enum argv builder** plus an allowlist — never string interpolation. No speech-derived
  or model-derived string ever reaches a command line.
- The admin password, if ever stored, is a **zero-argument callable resolved at the instant of
  use** and piped to `softwareupdate --stdinpass` on stdin — never an argv element, never logged,
  never in a `repr`, never in an exception. This follows [security invariant #1](12-security.md):
  the model never holds secrets.

## What has to be true before any of this is built

1. [Packaging (M4)](09-packaging.md) lands, including a microphone grant that survives a rebuild.
2. A full reboot cycle has been heard to work, end to end, by the maintainer.
3. The Touch ID question above is answered on real hardware.
4. **M3 has happened.** His father has used Jarvis daily, and the posture has been tried against
   how he actually lives with the machine — not against how it looks on paper.
