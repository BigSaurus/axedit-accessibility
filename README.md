# Axe-Edit III Accessibility (NVDA add-on)

Makes **Axe-Edit III** — Fractal Audio's editor for the Axe-Fx III — usable with
the **NVDA** screen reader. Experimental, untested support for **FM9-Edit** and
**FM3-Edit** is also included (Fractal's editors share a JUCE codebase; if you
own an FM9 or FM3, see [below](#other-fractal-editors)).

Axe-Edit is a native JUCE application whose controls tend to hide their value in
the control name, fire no change events, and report contradictory state. This
add-on fixes those so you can hear what you're doing and move around the grid by
keyboard.

> Early release — it already handles the day-to-day editing flow, and more
> features plus regular updates are coming.

## Features
- **Values spoken as you change them** — knobs and combo boxes are re-read after
  each arrow key (e.g. "Gain: 3.40"), instead of silence.
- **Clean grid-cell state** — each cell says its block and bypass state
  ("Amp 1A, Active") instead of the default contradictory "Active … not checked".
- **Bypass without losing focus** — Space on a grid cell bypasses/enables the
  block and speaks the new state instantly; focus stays put (Axe-Edit normally
  drops it entirely).
- **Mouse-only on/off buttons made usable** — Bypass, Scene Ignore, Channel A–D
  and the scene buttons respond to Enter, relabelled to their true state.
- **Top menus from the keyboard** — Alt+P/B/T/S/H open the Preset, Block, Tools,
  Settings and Help menus.
- **No routing-graphic spam** — the 169 unlabelled jack/cable graphics are
  suppressed.
- **Fast 2D grid navigation** — arrows, Home/End, Enter-to-select, and
  number-key jumps to any column on the main row.
- **Create cables from the keyboard** — connect one block's output to another
  block's input (series, parallel and diagonal) with **NVDA+Shift+C** on the
  source block, then again on the target. No mouse drag.

## Keyboard commands

### On a grid cell
| Key | Action |
| --- | --- |
| Arrow keys | Move between grid cells (2D) |
| Home / End | First / last column of the row |
| Enter | Select the block so its parameters load |
| Space | Bypass / enable the block, keeping focus |
| NVDA+Shift+C | Start a cable from this block; press again on another block to connect its output to that block's input. Press on the same block, or Escape, to cancel |

### On an on/off button (Bypass, Scene Ignore, Channel A–D, scenes)
| Key | Action |
| --- | --- |
| Enter | Toggle it. For a channel button, focus then lands on the combo box just below the channels so Tab keeps working |

### Anywhere in Axe-Edit
| Key | Action |
| --- | --- |
| NVDA+Ctrl+0 … 9 | Jump to row 2, that column (NVDA+Ctrl+5 = the amp) |
| Alt+P / B / T / S / H | Open the Preset / Block / Tools / Settings / Help menu |
| NVDA+Shift+A | Amp block |
| NVDA+Shift+E | Effects grid |
| NVDA+Shift+F | First parameter of the current block |
| NVDA+Shift+P | Preset selector |
| NVDA+Shift+S | Scene selector |
| NVDA+Shift+I | Announce full info about the focused control |
| NVDA+Shift+G | Toggle 2D grid navigation (default on) |
| NVDA+Shift+J | Toggle jack/cable noise suppression (default on) |
| NVDA+Shift+Space | Activate a mouse-only control |
| NVDA+Shift+D | Save a diagnostic dump of the window to the Desktop |

## Install
1. Download the latest `.nvda-addon` from the
   [Releases](https://github.com/BigSaurus/axedit-accessibility/releases) page.
2. Open the file (or drag it onto the NVDA tray icon). Confirm the install.
3. Restart NVDA if prompted, then open Axe-Edit III.

A one-time "untrusted add-on" prompt is normal for add-ons not yet in the NVDA
Add-on Store.

## Compatibility
- Minimum NVDA: 2022.1
- Last tested NVDA: 2026.1
- Axe-Edit III (native JUCE build)

## Building from source
Requires Windows + PowerShell. From `tools/nvda-addon/`:

```powershell
# Package the add-on
./build_addon.ps1

# Or install into NVDA's developer scratchpad for testing
./install_dev.ps1   # then NVDA+Ctrl+F3 to reload
```

## Other Fractal editors
FM9-Edit and FM3-Edit share Axe-Edit's JUCE codebase, so the same fixes are
expected to apply — but only Axe-Edit III has been tested against hardware. If
you own an FM9 or FM3: open the editor, press **NVDA+Shift+D**, and send the
file that lands on your Desktop along with a note on what did and didn't work.
That dump is enough to confirm support and fix whatever is off.

## Known limitations
- Cables can be **created** (NVDA+Shift+C) but not yet **read back** — Axe-Edit's
  cables carry no accessible identity, so the add-on can't tell you what is
  already wired, and it confirms a new cable by speaking the intended connection
  rather than by reading it. Reading existing routing is planned separately.
- Number-key column jumps target row 2 (Axe-Edit's default chain row); use
  arrows for other rows.
- The right-click "add block" menu is exposed only via IAccessible2 and is not
  yet accessible — planned as separate work.
- Pressing Enter on a model selector opens Axe-Edit's full-window model picker,
  whose entries are drawn graphics with no accessible identity. NVDA warns you
  the list is open but unreadable — press Escape and change the model with the
  arrow keys instead.

## License
GNU General Public License v2 — see [LICENSE](LICENSE).

Author: **Big Saurus**
