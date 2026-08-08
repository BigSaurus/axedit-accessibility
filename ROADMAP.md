# Roadmap

What's planned and what's open for contribution. This add-on makes Fractal
Audio's JUCE editors fully accessible with NVDA. New here? See
[CONTRIBUTING.md](CONTRIBUTING.md) — and note you don't need a Fractal unit to
help; many items can be built against a diagnostic dump.

Each item below links to a GitHub issue where the work happens. Items under
"Further ahead" don't have issues yet.

<!-- BEGIN AUTO (generated from open issues; do not edit by hand) -->

## Known issues
- **NVDA+Shift+F lands on the wrong control in the Cab block** — #2

## Good first issues
- **Announce preset number and name when the preset changes** — #3
- **Open a block's right-click menu from the keyboard** — #4
- **Keyboard shortcuts for Import / Export Preset** — #5
- **Command to speak the current effects chain** — #6

## Planned / help wanted
- **FM3-edit and FM9-edit support** — #1

<!-- END AUTO -->

## Further ahead
Larger pieces, gated on harder problems. Not yet open as issues.

- **Announce and navigate parameter-page titles** — speak the page you land on
  when moving through a block's parameter pages with PgUp/PgDn, and make those
  pages first-class navigable items.
- **Cab IR selector** — announce the loaded impulse response and make it easy to
  change by arrow key (the in-panel selector; the Cab Manager's own IR list is
  drawn pixels with no accessibility identity, so it can't be made browsable).
- **Label the Setup-menu controls** — input type/source, stereo vs mono, and the
  other unlabelled dropdowns in the Setup windows.
- **Keyboard-only block cabling** — connect blocks without the mouse. Hard: the
  routing graphics carry no identity in the accessibility tree, so this is the
  write side of a known wall. Likely needs a companion tool that reads and
  writes the preset's routing data.
- **Speak a block's signal routing** — same identity wall. An in-app estimate
  from block positions is possible now; an accurate version (including diagonal
  cables) would need a companion tool that reads the preset.
- **Right-click "add block" menu** — currently exposed only via IAccessible2 and
  not yet navigable; its own sub-project.
