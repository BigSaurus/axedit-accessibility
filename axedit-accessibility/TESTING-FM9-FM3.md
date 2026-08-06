# Testing the add-on with FM9-Edit or FM3-Edit

Thanks for trying this. This is an NVDA add-on that makes Fractal Audio's editor
software usable with a screen reader. It is **tested and working with Axe-Edit
III**. Support for **FM9-Edit** and **FM3-Edit** is included but has never been
run against the real thing — that is what you are helping with.

You do not need to know anything technical. The most useful thing you can do
takes one keystroke (step 3).

---

## 1. Install

1. Download `axedit-accessibility-0.5.0.nvda-addon`.
2. With NVDA running, press Enter on the downloaded file (or drag it onto the
   NVDA icon in the system tray).
3. Confirm the prompts, and restart NVDA when it asks.

To remove it later: NVDA menu → Tools → Manage add-ons → select it → Remove.

## 2. Check that it loaded at all

Open FM9-Edit (or FM3-Edit) and arrow onto the grid.

- **If block cells read as something like "Grid row 2 column 5: Amp 1A,
  Active"** and the arrow keys move you around the grid — it loaded. Go to
  step 3.
- **If nothing sounds different from before**, the add-on probably isn't
  attaching to the program. That is a one-line fix on my end, but I need to know
  the program's exact name:
  1. Press Ctrl+Shift+Escape to open Task Manager.
  2. Go to the **Details** tab.
  3. Find the row for the editor and report the exact name shown, including
     capitalisation (I am expecting `FM9-Edit.exe`).

  Then do step 3 anyway — it still works.

## 3. The important bit: send a dump (one keystroke)

With the editor open and focused, press **NVDA+Shift+D**.

NVDA will say "Collecting controls, one moment", then tell you how many controls
it found and the name of a file it saved to your **Desktop**. It will be called
something like `fractal-edit-dump-fm9-edit.json`.

**Send me that file.** It describes every control in the window and is enough
for me to fix almost anything without needing the hardware. It contains no
personal information — just control names, positions and states.

If NVDA+Shift+D does nothing at all, that itself is the answer to step 2 — say
so and skip to step 4.

## 4. If it did load, try these and tell me what happened

No need to be thorough. Even "1 and 2 fine, 4 said nothing" is useful.

| # | Do this | Expected |
|---|---------|----------|
| 1 | Arrow around the grid | Each cell speaks once: block name and Active/Bypassed. Should feel quick, not sluggish. |
| 2 | Press Enter on a block | Says "Selected <block>" and that block's parameters load. |
| 3 | Press Space on a block | Bypasses/enables it, **keeps focus on the same cell**, and speaks the new state. |
| 4 | Focus a knob, press arrow keys | Speaks the new value, e.g. "Gain: 3.40". |
| 5 | Tab to a Bypass or Channel button, press Enter | Toggles it and says "checked" or "not checked". |
| 6 | Press NVDA+Ctrl+5 | Jumps to row 2, column 5 of the grid. |
| 7 | Press NVDA+Shift+F | Jumps to the first parameter knob of the selected block. |

Also worth mentioning if you notice it:

- Anything that reads out as meaningless noise while tabbing around.
- Anything that says the **opposite** of what is true (a control that is on but
  reads as off, or vice versa).
- Any place where focus vanishes and you have to hunt for it.

## 5. Known limitations (no need to report these)

- The routing/cabling between blocks is not readable. The connection graphics
  carry no identity in the accessibility layer, so there is nothing to read.
- The right-click "add block" menu is not accessible yet.
- Grid navigation shortcuts assume the main signal chain is on row 2.

---

Full command list: NVDA menu → Tools → Manage add-ons → select this add-on →
Help. Project home: https://github.com/BigSaurus/axedit-accessibility
