# Changelog

## 0.3.2
- Remapped the column-jump commands from NVDA+Shift+digit to **NVDA+Ctrl+digit**
  to avoid a conflict with another add-on.

## 0.3.1
- Added **NVDA+Ctrl+0 through 9** (originally Shift): jump straight to the main
  signal row (row 2), that column — e.g. the amp is column 5. Works from
  anywhere in Axe-Edit, not just on the grid.

## 0.3.0
- Grid navigation performance: the 84 cells are cached and stale speech is
  cancelled, so fast movement no longer chokes; each cell is announced once.
- **Home / End** on a grid cell jump to the first / last column of the row.
- **Enter** on a grid cell selects that block so its parameters load.
- **NVDA+Shift+F** jumps to the first parameter of the current block (chosen by
  screen position, i.e. the first knob).

## 0.2.0
- Rewritten against the real Axe-Edit UIA tree (native JUCE, not Qt).
- Slider/knob values are spoken when changed with the arrow keys (value lives in
  the control name; no change event fires).
- Amp/effect model combo values spoken on change.
- Grid cells report block + bypass state cleanly, without the contradictory
  "Active … not checked".
- Suppressed 169 jack/cable routing-graphic controls (toggle: NVDA+Shift+J).
- Added 2D arrow-key grid navigation (toggle: NVDA+Shift+G).
- Section-jump shortcuts and keyboard activation of mouse-only controls.

## 0.1.0
- Initial prototype: combo re-read, basic toggle-state fix, section shortcuts.
