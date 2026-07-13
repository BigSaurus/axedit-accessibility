# Axe-Edit III — UIA ground truth

Every fix in the app module is derived from a real UIA capture of the running
app (`VSCode/.tmp/amp_tree.json`, 409 controls, amp page + grid visible).
This is the reference so future edits don't drift back into guesswork.

## Framework
- Native **JUCE** app. Root: `WindowControl`, name `Axe-Edit III`, class
  `JUCE_19ee7d9f5cc`. **Not Qt, not a web view** — no CDP/JS injection; the
  correct vehicle is an NVDA app module over the UIA / IAccessible tree.
- One legacy doc mislabels the context menus "Qt"; the dump shows JUCE. The
  *symptom* it describes (right-click "add block" menu visible only via
  IAccessible2, invisible to UIA) is still real — that stays a separate
  sub-project.

## Control shapes (verbatim from the capture)

| Thing | Role | Name pattern | Value pattern? | Notes |
|---|---|---|---|---|
| Param knob/slider | `SliderControl` (11) | `Gain: 3.33, Modifier Disabled` | **none** | Value is in the name. No value-change event. |
| Amp/effect model | `ComboBoxControl` | `: Friedman HBE V2` | none | Leading colon; value in name. |
| Config combo | `ComboBoxControl` | `Input Select: Sum L+R`, `Bypass Mode: Thru` | none | |
| Grid cell | `RadioButtonControl` (84) | `Grid row R column C: <block>, Active\|Bypassed` | `On`/`Off` readonly + Toggle 0/1 | **Double state** — see below. Empty cells: `... : Empty`; shunts: `... : Shunt`. |
| Routing graphic | `RadioButtonControl` (156 + 13) | `JackComponent` / `CableComponent` | `Off` | **Noise.** No row/column identity. |
| Scene/transport | `ButtonControl` | `Scene 1: Off`, `Bypass: Off`, `Channel A: Off` | | State in the name. |
| Preset / scene | `EditControl` | `Preset Name: Djentlemanly`, `Scene Number: S01` | | |

Role counts in the capture: 253 RadioButton, 59 Button, 46 Text, 17 Edit,
12 Custom, 11 Slider, 5 MenuItem, 4 ComboBox, 1 Window, 1 Image.

## The grid double-state, precisely
A grid cell RadioButton carries **two independent on/off meanings**:
- Toggle/Value (`On`/`Off`) = *is this the currently SELECTED block* (only one
  cell is `On` at a time — the Amp cell in the capture: `toggle=1, value=On`).
- The `, Active` / `, Bypassed` suffix in the **name** = the block's *bypass*
  state (e.g. `Drive 1A, Active` has `toggle=0, value=Off`).

Default NVDA reads both → "Drive 1A, Active … not checked", which sounds
contradictory. Fix: `_AxeEditGridCell._get_states` drops
CHECKED/SELECTED/PRESSED/HALFCHECKED. The name already says Active/Bypassed;
focus already tells you which cell you're on.

Grid indices are **0-based**: rows 0–5, columns 0–13 — matches the owner's
"Row.Column" convention.

## The noise, precisely
`156 × JackComponent + 13 × CableComponent = 169` named RadioButtons with no
identity. The old filter only skipped *unnamed* structural controls, so all
169 slipped through. Fix: `_AxeEditNoise` marks them layout-only (skipped by
object nav / review cursor) and the app module swallows their focus event.
Toggle with **NVDA+Shift+J** if a live session shows any are actually needed
for routing.
