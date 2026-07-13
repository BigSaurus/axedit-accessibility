# Axe-Edit NVDA add-on — backlog

Deferred ideas, with enough context to pick up cold. Shipped work lives in the
module + `LIVE_TEST_CHECKLIST.md`; ground truth in `UIA_GROUND_TRUTH.md`.

## Cell routing / cabling readout  (deferred 2026-07-12, owner request)
**Want:** a command on a grid cell that speaks its signal routing — e.g.
"inputs from Drive 1A; outputs to Cab 1A, Reverb 1A."

**Why it's not trivial:** the `CableComponent` (13) and `JackComponent` (156)
elements carry **no identity in the UIA tree** — no endpoints, no row/col — which
is exactly why they're suppressed as noise. So true wiring (especially diagonal
cross-row cables) **cannot be read from the accessibility tree**. The grid-cell
names give block + position only.

**Two ways to build it when revisited:**
1. **Position-based estimate (in-add-on, no device, instant).** On a cell,
   report non-empty neighbors in column c-1 (likely inputs) and c+1 (likely
   outputs) from the cached grid index. Must be spoken as an *estimate* — it
   cannot see diagonal cables, so it will be wrong on merges/splits. Cheap;
   good for orientation only.
2. **Accurate via preset data (separate tool + device/preset).** Read the real
   connection graph from the current preset using the SysEx codec / MCP grid
   tools (`preset_body_decode.py`, or the axe-fx-midi MCP `grid_read` /
   `get_topology_info` / `describe_preset`), then have the add-on speak it.
   Precise, includes diagonals; but needs the device or a saved preset, won't
   reflect *unsaved* edits, and is a bigger cross-process build (NVDA add-on is
   pure Python with no MIDI). Would likely be a companion helper the add-on
   talks to, not in-process.

Owner picked "leave it out for now, keep as backlog" (2026-07-12).

## Tab-confinement (pain point c)  — live check
No static evidence exists for whether focus gets trapped in a region after
object-nav. Confirm in a live session (see checklist item 7); only build a fix
if it reproduces.

## Right-click "add block" menu  — IAccessible2 sub-project
The context menu is exposed via IAccessible2, invisible to UIA; injected arrows
don't drive it. A proper vision-free "place a block" flow is a separate project
(comtypes has no IA2 interfaces; would need to hand-define them). Tracked in the
main Axe-Fx interaction strategy doc.

## Nice-to-haves (unprioritised)
- Number-key column jumps (NVDA+Shift+0-9) are hardcoded to row 2 (`_MAIN_ROW`)
  and cover columns 0-9 only. If presets that use other rows become common,
  make the target row follow the last-focused grid row, or add a modifier for a
  second row. Columns 10-13 are reachable via arrows / End.
- Announce the current param **page** on PgUp/PgDn (JUCE may not; same re-read
  pattern as sliders could catch it).
- Speak channel (A/B/C/D) changes on the amp/block when switched.
- A "where am I" command that reads row/col + block + bypass for the focused
  grid cell on demand.
