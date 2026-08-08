# Changelog

## 0.9.0
- **Create cables between blocks from the keyboard.** Axe-Edit's routing was
  entirely mouse-driven, so building or fixing signal connections was out of
  reach. Now press **NVDA+Shift+C** on a block to start a cable from its output,
  move to another block, and press it again to connect to that block's input.
  Series, parallel and diagonal routing all work through this. Press it again on
  the same block, or press Escape, to cancel. Because Axe-Edit's cables carry no
  accessible identity, the connection is confirmed by speaking it ("Connected
  Drive 1 to Amp 1") rather than by reading it back; reading what's *already*
  wired is not yet possible and is planned as separate work.

## 0.8.0
- **Open the top menus from the keyboard.** The Preset, Block, Tools, Settings
  and Help menus are mouse-only in Axe-Edit; they now open with **Alt+P**,
  **Alt+B**, **Alt+T**, **Alt+S** and **Alt+H** respectively.
- **No more silent trap on the model list.** Pressing Enter on a model selector
  opens Axe-Edit's full-window model picker, whose entries are unlabelled
  graphics with no accessible identity -- so focus landed on a completely silent
  element. NVDA now announces that the list is open but inaccessible and tells
  you to press Escape and change the model with the arrow keys instead.

## 0.7.3
- **Landing on the combo after a channel switch is much faster.** The combo is
  now located before the toggle (while the layout is stable) and focused the
  instant the switch drops focus, with tight retries and a cached reference so
  repeated channel changes never re-scan the window.

## 0.7.2
- **Re-enabling a block no longer cuts off its announcement.** Turning a block
  back on reloads its whole parameter panel -- a heavier rebuild than bypassing
  -- whose events were interrupting the spoken state. The quiet window after a
  Space bypass now covers that longer, heavier churn for any control.
- **On/off buttons are buttons again, with correct state.** Presenting them as
  check boxes made NVDA call them "read only", which was confusing. They are now
  ordinary buttons relabelled to the truthful "Channel C off" / "Channel C on"
  (read from the control's real value, since its own name is unreliable).
- **Landing on the combo after a channel switch is quicker** (starts at ~80ms
  instead of ~250ms).

## 0.7.1
- **Bypassing a block no longer gets its announcement cut off.** Axe-Edit fires
  name/state changes on the block as it rebuilds, and NVDA was announcing those
  over the top of the state we just spoke. Those churn events are now held back
  briefly so the announcement is heard cleanly.
- **Toggling a channel now keeps you able to Tab.** Channel switches clear
  keyboard focus and the channel buttons themselves cannot be re-focused, so
  focus now lands on the adjacent combo box just below the channels -- a normal
  control you can Tab and Shift+Tab from.

## 0.7.0
- **Bypassing a block no longer interrupts itself or reads the wrong state.**
  The previous version re-read the cell's name shortly after Space to confirm
  the toggle, but Axe-Edit updates that name slowly, so it often read the *old*
  state ("Active" right after bypassing) and cut off the correct announcement.
  Space now simply speaks the new state once and restores focus quietly.
- **On/off buttons now report the truth.** A live dump showed Axe-Edit's names
  for these are unreliable ("Channel D: On" while the control was actually
  off). They are now presented as check boxes whose checked state comes from
  the control's real value, not its misleading label.
- **Enter on an on/off button no longer breaks Tab.** Activating a channel or
  bypass button clears Axe-Edit's keyboard focus entirely, which left Tab and
  Shift+Tab with nothing to move from. The add-on now activates without a
  synthesized click and patiently re-anchors focus on the button (verifying it
  actually landed) across Axe-Edit's rebuild, so Tab keeps working.

## 0.6.0
- **Bypassing a block with Space is now instant and keeps focus.** Space
  speaks the new state right away (e.g. "Amp 1D, Bypassed") instead of waiting
  for Axe-Edit to rebuild the cell, restores focus to the block quietly, and
  double-checks the real state a moment later. The previous version waited on
  the rebuild and could feel as slow as before, or slower.
- **The on/off buttons (Channel A-D, Bypass, Scene Ignore, the scene buttons)
  now respond to Enter without losing focus.** These are a different control
  type from a normal button, which is why earlier versions never attached to
  them; they are now matched by name. Press Enter to toggle; focus returns to
  the button and NVDA speaks its new state. They stay presented as buttons.
- Diagnostic dumps (NVDA+Shift+D) now also record enough to identify a
  control's role, which is how the on/off-button issue above was pinned down.

## 0.5.0
- **Experimental support for FM9-Edit and FM3-Edit.** All the behaviour moved
  into a shared module, and each editor now gets a small app module that binds
  it. Fractal's editors share a JUCE codebase and this add-on keys off the
  control-naming patterns that codebase generates, so the fixes are expected to
  carry across &mdash; but **only Axe-Edit III has been tested**. Feedback from
  FM9 and FM3 owners is what will move these out of "experimental".
- **NVDA+Shift+D saves a diagnostic dump** of the current editor window to your
  Desktop: every control, its name, role, state, value and position. This is
  what makes confirming a new editor possible without owning the hardware
  &mdash; open the editor, press the key, send the file.

## 0.4.0
- **Space no longer loses focus.** Bypassing or re-enabling a block with Space
  made Axe-Edit rebuild the grid cell and drop keyboard focus, leaving you to
  hunt for a control again. Focus is now restored to the same cell and its new
  state is spoken ("Amp 1A, Bypassed"). If you have already arrowed to another
  cell, you are left where you are rather than yanked back.
- **On/off buttons are usable from the keyboard.** Buttons like *Bypass*,
  *Scene Ignore*, *Channel A&ndash;D* and the scene buttons were mouse-only.
  **Enter** now toggles them and speaks the result. Space is deliberately left
  alone, since Space is the grid's bypass gesture.
- **On/off buttons now report the truth.** Their name suffix is stale &mdash;
  Axe-Edit labels the *active* channel "Channel A: Off" while the control's
  actual value is On. State is now taken from the control's value and the
  misleading suffix is dropped, so they read as plain checked / not checked
  checkboxes.
- Grid size is now measured from the running application instead of being
  hardcoded to the Axe-Fx III's 6&times;14, so a differently-shaped grid
  navigates correctly.

## 0.3.3
- **Fixed the packaged add-on failing to install** ("missing a file or invalid
  file format"). The `manifest.ini` wrongly wrapped its fields in an `[add-on]`
  section and left the comma-containing `description` unquoted, so NVDA's
  manifest validator rejected it. Fields are now at the root level and
  `description` is triple-quoted, matching NVDA's manifest format. (The dev
  scratchpad install was unaffected, which masked the bug.)

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
