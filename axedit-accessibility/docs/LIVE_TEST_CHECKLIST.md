# Live validation checklist

The code is written against a static UIA capture. It **must be validated in a
live Axe-Edit III + NVDA session** before it's "done" — JUCE event timing and
whether arrow keys are safe to intercept can only be confirmed with real
speech. Everything below is a one-person pass; check each box.

## Install (dev)
1. `powershell tools\nvda-addon\install_dev.ps1`  (copies the app module to
   NVDA's scratchpad).
2. In NVDA: **NVDA+Ctrl+F3** to reload plugins.
3. Switch to Axe-Edit III.

> Note: the scratchpad path only works if NVDA's "Enable loading custom code
> from Developer Scratchpad" is on (NVDA menu → Preferences → Settings →
> Advanced). For a normal install, run `build_addon.ps1` and open the
> resulting `.nvda-addon`.

## Tests

### 1. Slider values on change  (fix #1)
- [ ] Focus a param knob (e.g. Gain). Press Up/Down arrow.
- [ ] NVDA speaks the new value each press, e.g. "Gain: 3.40" — **not silence**,
      and **without** "Modifier Disabled" tacked on every time.

### 2. Amp / effect model on change  (fix #2)
- [ ] Focus the amp model combo. Arrow through models.
- [ ] NVDA speaks each model name (e.g. "Friedman HBE V2") — no leading colon.

### 3. Grid cell reads cleanly  (fix #3)
- [ ] Arrow/tab onto an active block cell.
- [ ] NVDA says something like "Grid row 2 column 4: Drive 1A, Active" —
      **no** trailing "not checked / not selected / off" that contradicts
      "Active".
- [ ] A bypassed block says "... Bypassed"; empty cell says "... Empty".

### 4. Jack/cable noise gone  (fix #4)
- [ ] Object-navigate / tab across the grid area.
- [ ] You do **not** hear "JackComponent" / "CableComponent" repeatedly.
- [ ] Press **NVDA+Shift+J** → "Routing graphics shown" → they come back;
      press again → "hidden" → gone. (Confirms the toggle, and that routing
      still works either way.)

### 5. 2D grid navigation + performance  (new / v0.3.0)
- [ ] Focus a grid cell. Left/Right moves one column; Up/Down moves one row;
      each destination cell is announced.
- [ ] **Hold an arrow / move fast** — it keeps up, no choking or lag backlog
      (v0.3.0 caches the 84 cells and cancels stale speech).
- [ ] Each cell is announced **once** (concise name), not twice.
- [ ] At an edge, NVDA says "Edge of grid" and focus stays put.
- [ ] **Home** jumps to column 0 of the row; **End** to the last column.
- [ ] **Enter** on a cell selects that block ("Selected <block>") and its
      parameters load in the params panel.
- [ ] Press **NVDA+Shift+G** → "Grid arrow navigation off" → arrows fall back
      to Axe-Edit's own behaviour. Confirm nothing important was being blocked.

### 5c. Number-key column jumps  (new / v0.3.1, remapped v0.3.2)
- [ ] From anywhere in Axe-Edit, **NVDA+Ctrl+5** jumps to row 2 column 5 (the
      amp) and announces it. **+0** = input cell; **+9** = column 9.
- [ ] An empty target announces "Grid row 2 column N: Empty" (still moves there);
      a nonexistent grid says "No cell at row 2 column N".
- [ ] Columns 10-13 aren't on the number keys by design — reach them with
      arrows or End.

### 5b. Jump to first parameter  (new / v0.3.0)
- [ ] With a block selected, press **NVDA+Shift+F** → focus lands on the first
      parameter knob (e.g. "Gain: 3.33") — the spot you used to golden-cursor.
- [ ] Works across different block types (lands on the top-left param).

### 6. Section jumps  (carried over)
- [ ] NVDA+Shift+A → Amp block; +E → Effects grid (lands on cell row 0 col 0);
      +P → Preset; +S → Scene. Each announces its label.

### 7. Regression / tab-confinement  (pain point c — unverified statically)
- [ ] After object-nav into a region, can you Tab back out to the rest of the
      UI, or does focus get trapped? Note behaviour — this was the one pain
      point with no static evidence.

## If something's off
- Slider re-read too fast/slow → adjust `_announce_delay_ms` (default 150).
- Grid arrows fighting the app → NVDA+Shift+G off, and reconsider intercepting
  arrows on grid cells (the app may already move focus).
- A jack/cable turns out to be routing-relevant → keep NVDA+Shift+J default,
  or refine `_NOISE_NAMES`.

Once these pass in a live session, the change is good to ship (bump
`lastTestedNVDAVersion` in the manifest if the NVDA version differs).
