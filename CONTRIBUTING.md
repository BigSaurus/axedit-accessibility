# Contributing

Thanks for your interest in improving this add-on. It makes Fractal Audio's
editor software — Axe-Edit III, and experimentally FM9-Edit and FM3-Edit — fully
accessible with the NVDA screen reader. Contributions are welcome, **including
from people who don't own the hardware** (see "You don't need a Fractal unit"
below).

## What it is, technically
- An NVDA app module, written in pure Python. No MIDI, no external services.
- Shared logic lives in `appModules/fractalEditCore.py`; each editor gets a thin
  shim (`axe-edit iii.py`, `fm9-edit.py`, `fm3-edit.py`) that imports it.
- The editors are native JUCE apps. Accessibility comes through the UIA /
  IAccessible tree — values often live in a control's *name*, change events
  frequently don't fire, and some controls report contradictory state. Most of
  the add-on's work is papering over exactly that.

## Build and install (for development)
From `tools/nvda-addon/` on Windows with PowerShell:
- `./install_dev.ps1` copies the app module into NVDA's developer scratchpad;
  then press **NVDA+Ctrl+F3** to reload. (Requires NVDA → Preferences →
  Settings → Advanced → "Enable loading custom code from Developer Scratchpad".)
- `./build_addon.ps1` packages a `.nvda-addon` you can install normally.

## You don't need a Fractal unit — the dump workflow
The single most useful artifact is a **diagnostic dump**. With the editor open
and focused, press **NVDA+Shift+D**: the add-on writes a JSON file to your
Desktop describing every control in the window — role, name, state, value, and
on-screen position. It contains no personal information, just the control tree.

That dump is enough to write and reason about most fixes **without owning the
hardware**. If you're picking up an issue, ask for (or attach) the relevant
dump. Two labels tell you what a task needs:
- **can-do-from-dump** — writable and checkable against a dump alone.
- **needs-hardware** — needs a live editor + NVDA session to verify (JUCE event
  timing, whether a key is safe to intercept, how a menu behaves).

## The reference docs
- `docs/UIA_GROUND_TRUTH.md` — the map of the accessibility tree: control roles,
  name patterns, the grid's double-state, the routing "noise." Start here.
- `docs/LIVE_TEST_CHECKLIST.md` — how to validate a change in a live session.

## The verification loop (please read)
Because this is an accessibility tool, "it compiles" isn't "it works." Every
change ultimately needs a live editor + NVDA pass to confirm the speech is
right. If you have the hardware, run the relevant checklist items and say what
you heard. If you don't, that's fine — write it against a dump, open the PR, and
the maintainer or a hardware-owning tester will verify before it ships. A good
PR may wait a little for a hardware session; that's normal here.

## Working an issue
1. Comment on the issue to say you're taking it (so two people don't duplicate).
2. Match the surrounding code — naming, structure, and the existing "re-read on
   change" and focus-restore patterns in the core.
3. Open a PR that references the issue (e.g. "Fixes #12") and say whether you
   verified live or against a dump.

## Reporting a bug or requesting a feature
Open an issue. If it's about a specific screen, attach a dump (NVDA+Shift+D) —
it helps enormously.
