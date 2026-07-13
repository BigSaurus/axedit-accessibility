# Axe-Edit III Accessibility (NVDA add-on)

Makes **Axe-Edit III** — Fractal Audio's editor for the Axe-Fx III — usable with
the **NVDA** screen reader.

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
- **No routing-graphic spam** — the 169 unlabelled jack/cable graphics are
  suppressed.
- **Fast 2D grid navigation** — arrows, Home/End, Enter-to-select, and
  number-key jumps to any column on the main row.

## Keyboard commands

### On a grid cell
| Key | Action |
| --- | --- |
| Arrow keys | Move between grid cells (2D) |
| Home / End | First / last column of the row |
| Enter | Select the block so its parameters load |

### Anywhere in Axe-Edit
| Key | Action |
| --- | --- |
| NVDA+Ctrl+0 … 9 | Jump to row 2, that column (NVDA+Ctrl+5 = the amp) |
| NVDA+Shift+A | Amp block |
| NVDA+Shift+E | Effects grid |
| NVDA+Shift+F | First parameter of the current block |
| NVDA+Shift+P | Preset selector |
| NVDA+Shift+S | Scene selector |
| NVDA+Shift+I | Announce full info about the focused control |
| NVDA+Shift+G | Toggle 2D grid navigation (default on) |
| NVDA+Shift+J | Toggle jack/cable noise suppression (default on) |
| NVDA+Shift+Space | Activate a mouse-only control |

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

## Known limitations
- Number-key column jumps target row 2 (Axe-Edit's default chain row); use
  arrows for other rows.
- The right-click "add block" menu is exposed only via IAccessible2 and is not
  yet accessible — planned as separate work.

## License
GNU General Public License v2 — see [LICENSE](LICENSE).

Author: **Big Saurus**
