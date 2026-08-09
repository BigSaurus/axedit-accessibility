# Axe-Edit III Accessibility - NVDA app module
# Copyright (C) 2026 Big Saurus
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2, as published by the
# Free Software Foundation. This program is distributed WITHOUT ANY WARRANTY.
# See the LICENSE file (GNU GPL v2) distributed with this add-on for details.

"""
appModules/fractalEditCore.py

Shared NVDA app module for Fractal Audio's editor applications.

This module holds all the behaviour. It is bound to individual applications by
thin app modules named after each executable, because NVDA matches app modules
by process name:

    appModules/axe-edit iii.py  -> Axe-Edit III.exe   (Axe-Fx III)  -- verified
    appModules/fm9-edit.py      -> FM9-Edit.exe       (FM9)         -- untested
    appModules/fm3-edit.py      -> FM3-Edit.exe       (FM3)         -- untested

Fractal's editors are built from a common JUCE codebase, and every fix here
keys off naming patterns that codebase generates ("Grid row R column C: ...",
"Label: On/Off", "JackComponent") rather than anything Axe-Fx III specific, so
they are expected to carry across. Only Axe-Edit III has actually been tested;
NVDA+Shift+D writes a diagnostic dump that makes confirming a new editor a
single keystroke for whoever has the hardware.

Axe-Edit III is a NATIVE JUCE application (window class ``JUCE_...``, not Qt
and not a web view). Its UIA tree is rich and well-named, but several controls
lie about their state or bury their value in the name string, which makes the
default NVDA presentation confusing or silent. Every fix below is grounded in a
real UIA capture of the running app (see ``docs/UIA_GROUND_TRUTH.md``).

Fixes applied
-------------
1. Slider / knob values are not spoken when changed with the arrow keys.
   JUCE does not fire a value-change event, and the value lives in the control
   *name* ("Gain: 3.33, Modifier Disabled") with no UIA Value pattern, so NVDA
   has nothing to announce. Solution: intercept the arrow keys, let them
   through, then re-read the (cleaned) name after a short delay.

2. Amp / effect model combo boxes have the same problem: the value is in the
   name (": Friedman HBE V2") and no change event fires. Same intercept-and-
   re-read fix.

3. Grid cells contradict themselves. Each of the 84 grid cells is a
   RadioButton named "Grid row R column C: <block>, Active|Bypassed". The
   RadioButton's own checked/selected state means "is this the currently
   SELECTED block", which is a *different* on/off from the "Active/Bypassed"
   bypass state already in the name -- so NVDA announces e.g.
   "... Drive 1A, Active ... not checked". Solution: drop the selection state
   from the announcement; the block name already carries "Active"/"Bypassed",
   and focus already conveys which cell is selected.

4. 169 unlabelled routing controls (156 "JackComponent" + 13 "CableComponent"
   RadioButtons) are pure screen-reader spam -- they carry no row/column
   identity and nothing to act on. Solution: suppress them from focus and
   object navigation (toggleable with NVDA+Shift+J in case a live session
   shows they are needed for routing).

5. On/off buttons ("Bypass: Off", "Channel A: Off", "Scene 1: Off") are a
   distinct JUCE control role (NVDA role 92, not a normal button, role 9),
   matched by name pattern because a role check missed them. A live dump proved
   two things: their NAME lies (it showed "Channel D: On" while the value was
   "Off"), so they are kept as buttons but relabelled to a truthful
   "<label> on"/"<label> off" read from the value; and activating one clears
   keyboard focus entirely (the stuck state had no focused control at all). So
   Enter activates via the control's own action -- never a synthesised click,
   which worsens the focus loss. For the channel buttons, whose switch triggers
   a large rebuild and which cannot be re-focused at all, focus is then moved to
   the adjacent combo box below them (a normal focusable control) so Tab works
   again; other on/off buttons keep a patient re-focus of themselves.

6. Toggling a block's bypass with Space makes Axe-Edit rebuild the grid cell
   and drop keyboard focus entirely; the rebuild is slow and does not update the
   cell's name for a while. Solution: bypass is a deterministic toggle, so speak
   the expected new state immediately and restore focus quietly in the
   background. We do NOT re-read the name afterwards -- doing so interrupted the
   announcement and read the stale, pre-toggle state.

7. The preset number and name (both EditControls whose value lives in the
   name) change together whenever the preset does. JUCE does NOT fire a usable
   change event on those fields (confirmed live), so we re-read and speak them
   ("Preset 10, Deluxe Verb") a moment after the Ctrl+PageUp / Ctrl+PageDown
   preset-change keystrokes. (The Next/Previous Preset buttons and MIDI program
   changes have no keystroke to hook and are not yet covered.)

8. The grid cell's right-click menu is mouse-driven; the Applications key
   normally sends WM_CONTEXTMENU, which JUCE's grid ignores, so opening a
   block's menu required hand-positioning the mouse over it and
   right-clicking. Solution: bind the Applications key to a synthesized right
   click at the focused cell's own on-screen centre, reusing the same
   ABSOLUTE-coordinate technique the cabling feature (NVDA+Shift+C) needed to
   get JUCE to notice a click at all. Unlike the cabling and bypass paths,
   focus is deliberately NOT restored to the cell afterwards -- a native
   popup menu is about to claim focus of its own accord, and pulling focus
   back would fight it for that focus and could close the menu.

9. The parameter panel's PAGE tabs (Tone, Preamp, Speaker, ...) are a vertical
   column of plain static-text labels: no tab role, no selected state, and the
   value only echoes the name, so which page is current is not in the tree (only
   a colour highlight) and JUCE fires no change event. So, like the sliders, we
   drive and announce it ourselves: keep our own cursor into the discovered
   column, click the target tab (absolute synth click -- the only thing these
   custom widgets honour) and speak its name. The tabs are also overlaid as
   first-class TABs so object navigation reaches them and Enter selects one.

Navigation / commands
----------------------
  Arrows (on a grid cell)  -- move between grid cells, 2D (toggle: NVDA+Shift+G)
  Home / End (on a grid cell) -- jump to the first / last column of the row
  Enter (on a grid cell)   -- select that block so its parameters load
  Space (on a grid cell)   -- bypass / enable the block, keeping focus
  Applications key (on a grid cell) -- open this block's right-click menu at
                   the focused cell, without hand-positioning the mouse
  Enter (on an on/off button) -- toggle it (Space is reserved for block bypass)
  NVDA+Shift+C (on a grid cell) -- start a cable from this block; press again on
                   another block to connect its output to that block's input
                   (Escape, or pressing it on the same block, cancels)
  NVDA+Ctrl+0..9   -- jump straight to row 2, that column (e.g. +5 = the amp)
  NVDA+Shift+A   -- jump to the Amp block
  NVDA+Shift+E   -- jump to the Effects grid (row 0, column 0)
  NVDA+Shift+F   -- jump to the first parameter of the current block
  NVDA+Shift+P   -- jump to the Preset selector
  NVDA+Shift+S   -- jump to the Scene selector
  NVDA+Shift+PageDown / PageUp -- next / previous parameter page (Tone,
                   Preamp, Speaker, ...); Enter on a page tab also selects it
  Alt+P/B/T/S/H  -- open the Preset / Block / Tools / Settings / Help menu
  NVDA+Shift+I   -- announce full info about the focused control
  NVDA+Shift+O   -- speak the current effect chain, left to right (estimated)
  NVDA+Shift+B   -- summarise the selected block's parameters (the shown page)
  NVDA+Shift+J   -- toggle jack/cable noise suppression (default: on)
  NVDA+Shift+G   -- toggle 2D arrow-key grid navigation (default: on)
  NVDA+Shift+Space -- activate the focused control (for mouse-only items)
  NVDA+Shift+D   -- save a diagnostic dump of the window to the Desktop
"""

_ADDON_VERSION = "0.10.0"

import ctypes
import json
import os
import re
import time

import winUser

import appModuleHandler
import api
import controlTypes
import mouseHandler
import NVDAObjects
import speech
import ui
import wx
from logHandler import log
from scriptHandler import script


# ── Ground-truth constants (from the UIA capture) ─────────────────────────────

# Grid cells are named e.g. "Grid row 2 column 5: Amp 1A, Active".
_GRID_RE = re.compile(r"^Grid row (\d+) column (\d+):", re.IGNORECASE)
# Fallback grid size only. The real extent is measured from the running app
# when the cell index is built, so other Fractal editors (whose grids are a
# different shape) work without a code change.
_GRID_ROWS = 6      # Axe-Fx III: rows 0..5
_GRID_COLS = 14     # Axe-Fx III: cols 0..13

# On/off toggle buttons: "Bypass: Off", "Channel A: Off", "Scene 1: Off".
_TOGGLE_NAME_RE = re.compile(r"^(?P<label>.+?):\s*(On|Off)\s*$", re.IGNORECASE)

# The Active/Bypassed suffix on a grid cell's name, and how to flip it.
_CELL_STATE_RE = re.compile(r",\s*(Active|Bypassed)\s*$", re.IGNORECASE)
_STATE_FLIP = {"active": "Bypassed", "bypassed": "Active"}


def _predicted_toggle_text(cell_name):
    """Predict a grid cell's spoken text after a Space bypass toggle.

    "Grid row 2 column 5: Amp 1D, Active" -> "Amp 1D, Bypassed"

    Bypass is a deterministic toggle, so we can speak the expected new state at
    once instead of waiting for JUCE to rebuild the cell (the slow part).
    Returns "" for cells with no Active/Bypassed state to toggle (Shunt/Empty).
    """
    body = _GRID_RE.sub("", cell_name or "").strip(" :")
    m = _CELL_STATE_RE.search(body)
    if not m:
        return ""
    return body[:m.start()] + ", " + _STATE_FLIP[m.group(1).lower()]


def _cable_block_label(cell_name):
    """A grid cell's block label with no state suffix, for cable announcements.

    "Grid row 2 column 5: Amp 1A, Active" -> "Amp 1A"
    "Grid row 0 column 3: Shunt"          -> "Shunt"
    """
    body = _GRID_RE.sub("", cell_name or "").strip(" :")
    return _CELL_STATE_RE.sub("", body).strip()


def _block_summary(cell_name):
    """A grid cell's block label plus its spoken bypass state.

    "Grid row 2 column 5: Amp 1A, Active"    -> "Amp 1A active"
    "Grid row 2 column 8: Delay 1, Bypassed" -> "Delay 1 bypassed"
    "Grid row 0 column 3: Shunt"             -> "Shunt"  (no bypass state)
    "Grid row 0 column 0: Empty"             -> "Empty"
    Returns "" if the name is not a grid cell.
    """
    if not _GRID_RE.match(cell_name or ""):
        return ""
    label = _cable_block_label(cell_name)
    body = _GRID_RE.sub("", cell_name or "").strip(" :")
    m = _CELL_STATE_RE.search(body)
    if not m:
        return label
    return "{0} {1}".format(label, m.group(1).lower())


def _is_placed_block(label):
    """True for a real, placed block -- excludes empty cells and shunts."""
    return bool(label) and label.strip().lower() not in ("empty", "shunt")


# The routing-graphic RadioButtons that carry no useful identity.
_NOISE_NAMES = frozenset({"jackcomponent", "cablecomponent"})

# R7: interactive roles a Setup-panel control might use besides ComboBox and
# Slider (both handled separately in chooseNVDAObjectOverlayClasses). Kept to
# roles a user can actually land on, so an unnamed decorative pane never
# picks up a spoken label it never had before.
_SETUP_LABELLABLE_ROLES = frozenset({
    controlTypes.Role.EDITABLETEXT,
    controlTypes.Role.BUTTON,
    controlTypes.Role.CHECKBOX,
    controlTypes.Role.RADIOBUTTON,
    controlTypes.Role.SPINBUTTON,
})

# Slider names trail a modifier hint we don't want on every keystroke.
_MODIFIER_TRAILER_RE = re.compile(r",\s*Modifier (Disabled|Enabled)\s*$", re.IGNORECASE)

# The preset number/name EditControls: "Preset Number: 0010", "Preset Name: Deluxe Verb".
# One pattern matches both fields, so one overlay class and one tree-walk finds them.
_PRESET_FIELD_RE = re.compile(r"^Preset (?P<field>Number|Name):\s*(?P<value>.*)$", re.IGNORECASE)


def _clean_value_name(name):
    """Tidy a value-in-name string for speaking after an arrow keystroke.

    "Gain: 3.33, Modifier Disabled" -> "Gain: 3.33"
    ": Friedman HBE V2"             -> "Friedman HBE V2"
    """
    if not name:
        return ""
    name = _MODIFIER_TRAILER_RE.sub("", name).strip()
    if name.startswith(":"):
        name = name[1:].strip()
    return name


# The Cab block's LIBRARY value field has no name pattern of its own to match
# -- unlike the sliders/combos above, its value is not folded into its name
# with a label or a colon, and it can be blank when nothing is loaded. It is
# matched instead by position: a plain-text control sitting right after a
# plain-text sibling captioned "LIBRARY".
_CAB_LIBRARY_CAPTION = "library"


def _is_cab_library_value(obj):
    """True for the plain-text control that follows the "LIBRARY" caption."""
    try:
        prev = obj.previous
    except Exception:
        return False
    if prev is None:
        return False
    try:
        return (prev.name or "").strip().lower() == _CAB_LIBRARY_CAPTION
    except Exception:
        return False


def _invoke_control(obj, allow_mouse=True):
    """Activate a control: its own action first, synthesised click as fallback.

    The control's own action (UIA Invoke/Toggle, or the default action) does not
    move the mouse or steal focus, so it is always preferred. A synthesised
    mouse click is only used when ``allow_mouse`` is set -- for controls that
    already lose keyboard focus on activation, a click makes that worse, so the
    caller can forbid it. Returns True if some activation was attempted.
    """
    if obj is None:
        return False
    try:
        obj.doAction(0)
        return True
    except Exception:
        pass
    if not allow_mouse:
        return False
    location = obj.location
    if not location:
        return False
    cx = location.left + location.width // 2
    cy = location.top + location.height // 2
    mouseHandler.executeMouseMoveEvent(cx, cy)
    mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF_LEFTDOWN, cx, cy)
    mouseHandler.executeMouseEvent(winUser.MOUSEEVENTF_LEFTUP, cx, cy)
    return True


# ── Shared mixin: announce value-in-name after an arrow keystroke ──────────────

class _AnnounceAfterArrow(NVDAObjects.NVDAObject):
    """
    Base overlay for controls whose value lives in the name and whose value
    does NOT change via a UIA event (JUCE sliders and combo boxes).

    We let the keystroke through to the app, then re-read the focused control's
    (cleaned) name a moment later, once JUCE has repainted the accessibility
    tree.
    """

    _timer = None
    _announce_delay_ms = 150

    def _cancelTimer(self):
        if self._timer and self._timer.IsRunning():
            self._timer.Stop()
        self._timer = None

    def _scheduleAnnounce(self):
        self._cancelTimer()
        self._timer = wx.CallLater(self._announce_delay_ms, self._announce)

    def _announce(self):
        self._timer = None
        obj = api.getFocusObject()
        if obj is None:
            return
        text = _clean_value_name(obj.name) or (obj.value or "")
        if text:
            speech.speakMessage(text)

    # Honour a real value-change event if JUCE ever fires one.
    def event_valueChange(self):
        self._announce()

    def _passThenAnnounce(self, gesture):
        gesture.send()
        self._scheduleAnnounce()

    @script(gesture="kb:upArrow")
    def script_up(self, gesture):
        self._passThenAnnounce(gesture)

    @script(gesture="kb:downArrow")
    def script_down(self, gesture):
        self._passThenAnnounce(gesture)

    @script(gesture="kb:leftArrow")
    def script_left(self, gesture):
        self._passThenAnnounce(gesture)

    @script(gesture="kb:rightArrow")
    def script_right(self, gesture):
        self._passThenAnnounce(gesture)

    @script(gesture="kb:pageUp")
    def script_pageUp(self, gesture):
        self._passThenAnnounce(gesture)

    @script(gesture="kb:pageDown")
    def script_pageDown(self, gesture):
        self._passThenAnnounce(gesture)

    @script(gesture="kb:home")
    def script_home(self, gesture):
        self._passThenAnnounce(gesture)

    @script(gesture="kb:end")
    def script_end(self, gesture):
        self._passThenAnnounce(gesture)


class _AxeEditSlider(_AnnounceAfterArrow):
    """Param sliders/knobs: value is in the name, no value pattern."""


class _AxeEditComboBox(_AnnounceAfterArrow):
    """Amp/effect model + config combo boxes: value is in the name."""


class _AxeEditCabLibraryValue(_AnnounceAfterArrow):
    """
    The Cab block's LIBRARY value field: a plain-text control, not a combo
    box, identified by ``_is_cab_library_value`` rather than a role or name
    pattern (see there). Its text is the current selection and can be blank
    when nothing is loaded.

    No overrides needed beyond a blank-value fallback: it inherits the same
    intercept-arrow-then-re-read behaviour the sliders and combos above use,
    and ``_clean_value_name`` is a harmless no-op on text with no "Modifier
    Disabled" trailer or leading colon to strip.
    """

    def _get_name(self):
        # A blank value would otherwise be silent both on first Tab-in and
        # after every arrow press, which is the exact bug this fix exists
        # for. Say something concrete instead of nothing.
        cleaned = _clean_value_name(super()._get_name())
        return cleaned if cleaned else "Library: none selected"


# ── Overlay: parameter-panel page tabs (Tone, Preamp, Speaker, ...) ───────────

class _AxeEditPageTab(NVDAObjects.NVDAObject):
    """
    A parameter-panel PAGE tab, e.g. "Tone", "Preamp", "Power Amp", "Speaker",
    "Dynamics".

    In the tree these are plain static text (role STATICTEXT) with no tab role
    and no selected state -- so by default they are inert and easy to miss, and
    which one is active is not exposed at all. This overlay makes them
    first-class: it reports the control as a TAB (so object navigation says
    "Tone  tab"), and Enter selects that page. Selection is a synthesised
    ABSOLUTE-coordinate click -- the only thing these custom JUCE widgets honour
    (same finding as cabling / the right-click menu) -- followed by speaking the
    page name.
    """

    def _get_role(self):
        return controlTypes.Role.TAB

    @script(gesture="kb:enter")
    def script_selectPage(self, gesture):
        name = (self.name or "").strip()
        loc = self.location
        speech.cancelSpeech()
        if loc:
            self.appModule._click_point(
                loc.left + loc.width // 2, loc.top + loc.height // 2
            )
        # Keep the app module's page cursor in sync with a direct pick, so the
        # next NVDA+shift+pageDown/pageUp continues from here.
        try:
            names = list(self.appModule._page_names)
            if name in names:
                self.appModule._page_index = names.index(name)
        except Exception:
            pass
        ui.message(name or "Page")


# ── Overlay: preset number / name fields (announce on any change) ─────────────

class _AxeEditPresetField(NVDAObjects.NVDAObject):
    """
    One of the two preset EditControls: "Preset Number: 0010" or
    "Preset Name: Deluxe Verb". Both update together whenever the preset
    changes -- via the keyboard, the Next/Previous Preset buttons, or a
    change that arrives from outside the app entirely, with no keystroke to
    intercept. Unlike the sliders/combos above, JUCE does fire a nameChange
    event on these two controls, so we listen for it directly; that one hook
    then covers every way the preset can change.
    """

    def event_nameChange(self):
        self.appModule._onPresetFieldChanged(self)


# ── Overlay: on/off toggle buttons (Bypass, Scene, Channel A-D) ───────────────

class _AxeEditToggleButton(NVDAObjects.NVDAObject):
    """
    A JUCE on/off button: "Bypass: Off", "Scene Ignore: Off", "Channel A: Off",
    "Scene 1: Off", etc.

    These are a distinct control role from a normal push button (NVDA role 92,
    not 9), so they are matched by *name pattern* rather than role -- a role
    check missed them entirely. Two facts, both confirmed from a live dump,
    shape how they are handled:

      * Their NAME lies. The dump showed "Channel D: On" while the control's
        value was "Off", and "Channel B: Off" while its value was "On" (with
        the checked-state bit set). Only the value / checked state is truthful.
        They are kept as ordinary buttons (presenting them as a check box made
        NVDA report them as read-only, which was confusing), but relabelled to
        the truthful "<label> on"/"<label> off" so the state is still spoken.

      * Activating one clears keyboard focus entirely -- the dump taken in the
        stuck state had NO focused control, which is why Tab/Shift+Tab did
        nothing. So on Enter we activate via the control's own action (never a
        synthesised mouse click, which makes the focus loss worse) and then
        patiently re-assert focus, verifying it actually landed, until JUCE's
        (large) channel-switch rebuild has settled.

    Space is deliberately NOT bound here -- Space is the grid's own bypass
    gesture, and these buttons are reached by Tab, so Enter is the natural key.
    """

    def _raw_name(self):
        """The underlying UIA name ("Channel A: Off"), before our relabelling."""
        try:
            return super()._get_name() or ""
        except Exception:
            return ""

    def _button_label(self):
        """"Channel A: Off" -> "Channel A" (stable across the On/Off flip)."""
        raw = self._raw_name()
        m = _TOGGLE_NAME_RE.match(raw)
        return m.group("label").strip() if m else raw

    def _is_on(self):
        """True/False from the value (truthful), falling back to checked state."""
        try:
            value = (self.value or "").strip().lower()
        except Exception:
            value = ""
        if value in ("on", "true", "1", "yes"):
            return True
        if value in ("off", "false", "0", "no"):
            return False
        return bool(
            {controlTypes.State.CHECKED, controlTypes.State.PRESSED}
            & super()._get_states()
        )

    def _get_name(self):
        # Keep the native (button) role, but replace the unreliable name with a
        # truthful "<label> on"/"<label> off" so the real state is spoken.
        return "{0} {1}".format(
            self._button_label(), "on" if self._is_on() else "off"
        )

    def _get_states(self):
        # The truthful state is now in the name, so strip the native on/off and
        # read-only style states that would otherwise be announced (and which,
        # for these controls, are confusing or stale).
        states = super()._get_states()
        for s in (
            controlTypes.State.CHECKED,
            controlTypes.State.PRESSED,
            controlTypes.State.HALFCHECKED,
            controlTypes.State.CHECKABLE,
            controlTypes.State.SELECTED,
            controlTypes.State.READONLY,
        ):
            states.discard(s)
        return states

    @script(gesture="kb:enter")
    def script_toggle(self, gesture):
        label = self._button_label()
        box = self.location
        is_channel = label.strip().lower().startswith("channel")
        # Activate via the control's own action only -- no mouse-click fallback,
        # which would clear keyboard focus even harder.
        if not _invoke_control(self, allow_mouse=False):
            gesture.send()
            return
        if is_channel:
            # A channel switch clears keyboard focus and these buttons cannot be
            # re-focused (setFocus does not stick on them). Land on the adjacent
            # combo box (the model/library selector right below the channels) so
            # Tab and Shift+Tab work again. Attempted immediately, re-finding the
            # combo fresh each time (a cached object goes stale across the
            # rebuild and focusing a stale node wedges keyboard focus).
            self.appModule.recover_focus_to_combo(box, 0)
        else:
            # Bypass / Scene Ignore / Scene buttons: try to keep focus on them.
            self.appModule.restore_button_focus(label, box, 0)


# ── Overlay: grid cells (fix the double state) ────────────────────────────────

class _AxeEditGridCell(NVDAObjects.NVDAObject):
    """
    A grid cell RadioButton named "Grid row R column C: <block>, <state>".

    Two independent on/off meanings collide on this one control:
      * the RadioButton's checked/selected state = "is this the SELECTED block"
      * the ", Active" / ", Bypassed" suffix in the name = the bypass state
    NVDA reads both and they contradict.  We drop the selection state from the
    spoken output (focus already tells you which cell you are on) so the cell
    says one coherent thing: the block and its bypass state.

    When 2D grid navigation is enabled, the arrow keys move focus between cells
    instead of doing whatever JUCE does by default.
    """

    def _get_states(self):
        states = super()._get_states()
        # Remove the "am I the selected block" chatter that fights the name.
        for s in (
            controlTypes.State.CHECKED,
            controlTypes.State.SELECTED,
            controlTypes.State.PRESSED,
            controlTypes.State.HALFCHECKED,
        ):
            states.discard(s)
        return states

    # --- 2D navigation -------------------------------------------------------

    def _grid_nav_enabled(self):
        return getattr(self.appModule, "grid_arrows_enabled", True)

    def _rc(self):
        m = _GRID_RE.match(self.name or "")
        if not m:
            return None
        return int(m.group(1)), int(m.group(2))

    def _goto(self, nr, nc):
        """Focus the cell at (nr, nc) and announce it concisely. Returns True
        when handled (including a benign edge stop)."""
        app = self.appModule
        app.ensure_grid_index()
        if not (0 <= nr < app.grid_rows and 0 <= nc < app.grid_cols):
            speech.cancelSpeech()
            ui.message("Edge of grid")
            return True
        target = self.appModule.grid_cell(nr, nc)
        if target is None:
            return False
        # Mark this as a programmatic move so the queued focus event doesn't
        # double-speak (verbosely) on top of our concise announcement.
        self.appModule._last_grid_prog_move = time.time()
        try:
            target.setFocus()
        except Exception:
            # Stale cached object: rebuild the index once and retry.
            self.appModule.invalidate_grid_index()
            target = self.appModule.grid_cell(nr, nc)
            if target is None:
                return False
            self.appModule._last_grid_prog_move = time.time()
            target.setFocus()
        # Cancel any backlog so fast scrolling stays snappy, then speak.
        speech.cancelSpeech()
        ui.message(target.name or "")
        return True

    def _move(self, dRow, dCol):
        rc = self._rc()
        if rc is None:
            return False
        row, col = rc
        return self._goto(row + dRow, col + dCol)

    def _arrow(self, gesture, dRow, dCol):
        if self._grid_nav_enabled() and self._move(dRow, dCol):
            return
        gesture.send()

    @script(gesture="kb:upArrow")
    def script_gridUp(self, gesture):
        self._arrow(gesture, -1, 0)

    @script(gesture="kb:downArrow")
    def script_gridDown(self, gesture):
        self._arrow(gesture, 1, 0)

    @script(gesture="kb:leftArrow")
    def script_gridLeft(self, gesture):
        self._arrow(gesture, 0, -1)

    @script(gesture="kb:rightArrow")
    def script_gridRight(self, gesture):
        self._arrow(gesture, 0, 1)

    @script(gesture="kb:home")
    def script_gridRowStart(self, gesture):
        rc = self._rc()
        if self._grid_nav_enabled() and rc is not None and self._goto(rc[0], 0):
            return
        gesture.send()

    @script(gesture="kb:end")
    def script_gridRowEnd(self, gesture):
        rc = self._rc()
        if self._grid_nav_enabled() and rc is not None:
            self.appModule.ensure_grid_index()
            if self._goto(rc[0], self.appModule.grid_cols - 1):
                return
        gesture.send()

    @script(gesture="kb:enter")
    def script_gridSelect(self, gesture):
        """Select this block so its parameters load in the params panel."""
        block = _clean_value_name(self.name)
        # Strip the "Grid row R column C:" prefix for a tidy announcement.
        block = _GRID_RE.sub("", self.name or "").strip(" :") or block
        if _invoke_control(self):
            speech.cancelSpeech()
            ui.message("Selected {0}".format(block) if block else "Selected")
        else:
            gesture.send()

    # First silent focus-restore attempt after Space; retried gently if focus is
    # still gone. Announcement does NOT wait on these -- we speak the new state
    # up front -- so restoring focus can be unhurried and quiet.
    _REFOCUS_FIRST_MS = 120

    @script(gesture="kb:space")
    def script_gridToggleBypass(self, gesture):
        """Bypass / enable this block, speaking the result immediately.

        The slow part is JUCE rebuilding the cell, which also drops keyboard
        focus and does not update the cell's name for a while. Waiting on that
        made this feel sluggish, and reading the not-yet-updated name announced
        the *old* state. Instead we speak the expected new bypass state once, up
        front (bypass is a deterministic toggle), and quietly restore focus in
        the background. We do NOT re-read the name afterwards -- that was what
        interrupted the announcement and sometimes said "Active" on a block that
        had just been bypassed.
        """
        rc = self._rc()
        predicted = _predicted_toggle_text(self.name or "")
        gesture.send()
        if rc is None:
            return
        if predicted:
            # Instant spoken feedback. Open both suppression windows so the
            # rebuild's focus/name/state churn -- which is heavier when
            # re-enabling a block -- does not cut off what we just spoke.
            now = time.time()
            self.appModule._last_grid_prog_move = now
            self.appModule._last_bypass_time = now
            speech.cancelSpeech()
            ui.message(predicted)
        wx.CallLater(
            self._REFOCUS_FIRST_MS,
            self.appModule.restore_grid_focus, rc[0], rc[1], 0,
        )

    @script(gesture="kb:escape")
    def script_gridCancelCable(self, gesture):
        """Cancel a pending cable with Escape. Only intercepts Escape while a
        cable is armed; otherwise the app keeps its normal Escape behaviour."""
        if not self.appModule.cancel_pending_cable():
            gesture.send()

    @script(
        description="Axe-Edit: Open this block's right-click menu",
        gesture="kb:applications",
    )
    def script_gridContextMenu(self, gesture):
        """Pop this block's right-click menu at the focused cell.

        JUCE's grid cell is mouse-driven for its context menu and ignores the
        Applications key's default WM_CONTEXTMENU, so without this the user
        has to hand-position the mouse over the block and right-click.
        We already have the cell's real on-screen rectangle -- the same one
        the cabling feature reads -- so we reuse it at dead centre (not a
        jack) and fire a synthesized right click there with
        ``_right_click_point``, the same ABSOLUTE-coordinate technique the
        cabling feature needed to get JUCE to notice a click at all.

        A synthesized click drops keyboard focus (confirmed by the cabling
        feature). Here that is the wanted outcome: a native popup menu is
        about to claim focus of its own accord, and calling setFocus back
        onto the grid cell afterwards -- the way the cable/bypass paths do --
        would fight the menu for focus and could close it. So, unlike those
        paths, nothing here restores focus to the cell; whatever the popup
        menu does with focus is left alone. Whether the popup is then
        navigable with NVDA's arrows is a live observation, not something
        this script can guarantee -- see the add-on's live-test notes.
        """
        point = self.appModule._cable_point(self, 0.5)
        if point is None:
            gesture.send()
            return
        label = _cable_block_label(self.name)
        # Suppress this cell's own stale name/state churn (not the general
        # focus-swallow window -- we want the popup menu's own focus event,
        # if JUCE fires one, to reach the user).
        self.appModule._last_grid_prog_move = time.time()
        speech.cancelSpeech()
        # Spoken before the click because popping the JUCE menu takes a moment;
        # this is the "working on it" cue so the pause isn't mistaken for a
        # dead key.
        ui.message(
            "{0} context menu, opening".format(label)
            if label else "Context menu opening"
        )
        self.appModule._right_click_point(*point)


# ── Overlay: routing-graphic noise (jack/cable) ───────────────────────────────

class _AxeEditNoise(NVDAObjects.NVDAObject):
    """
    JackComponent / CableComponent RadioButtons -- pure routing graphics with
    no identity to act on.  Marked as layout so NVDA object navigation and the
    review cursor skip them; the app module also swallows their focus
    announcement.  Suppression is toggleable (NVDA+Shift+J).
    """

    def _get_presentationType(self):
        if getattr(self.appModule, "suppress_noise", True):
            return self.presType_layout
        return super()._get_presentationType()


# ── Overlay: Setup-panel controls with no name of their own (R7) ──────────────

class _AxeEditSetupField(NVDAObjects.NVDAObject):
    """
    A control inside the Setup panel (Config / Audio / Input Levels / Scales
    / Out N EQ / MIDI-Remote / Global -- whichever section is currently
    showing) whose own accessible name is empty: the classic unlabelled
    combo/edit shape, where the visible field label is a separate StaticText
    sitting next to the control rather than wired to it.

    Confirmed on a live capture: the "Device Name" edit box reports an empty
    name, with a StaticText reading "Device Name" sitting directly below it,
    same column. The label is recovered spatially at speak-time (see
    AppModule._setup_field_label) rather than baked in here, so it keeps
    working if the field moves (a resize, a DPI change, a different section
    laid out differently). If no qualifying label is ever found, this falls
    back to whatever NVDA already says for the bare control, so it can never
    make a control less accessible than it already was.
    """

    def _get_name(self):
        label = self.appModule._setup_field_label(self)
        return label or super()._get_name()


class _AxeEditSetupCombo(_AxeEditSetupField, _AxeEditComboBox):
    """
    A Setup-panel ComboBox with no name of its own: the same spatial-label
    fix as _AxeEditSetupField, stacked on top of the arrow-key value-announce
    every other Fractal combo box already gets (see _AxeEditComboBox). Named
    Setup combos, and every combo box in the main editor window, are
    unaffected -- they keep using plain _AxeEditComboBox.
    """


# ── App Module ────────────────────────────────────────────────────────────────

class AppModule(appModuleHandler.AppModule):

    # User-toggleable behaviour (defaults chosen for the daily-driver case).
    suppress_noise = True
    grid_arrows_enabled = True

    # Grid-cell cache (built once, reused per keystroke) + a timestamp used to
    # suppress the verbose focus announcement during our own grid moves. The
    # suppression window spans the focus churn after a Space bypass so the stale
    # gain-focus events during JUCE's rebuild never leak out.
    _grid_index = None
    _last_grid_prog_move = 0.0
    _GRID_SUPPRESS_S = 0.6

    # A Space bypass -- especially *re-enabling* a block -- makes Axe-Edit reload
    # the block's whole parameter panel, which fires focus/name/state events for
    # up to about a second and can move focus off the block. We already speak the
    # new state up front, so this window suppresses that churn for ANY control
    # (not just the grid cell) so the announcement is not cut off.
    _last_bypass_time = 0.0
    _BYPASS_SUPPRESS_S = 1.1

    # Preset-change announcement: the number and name fields update together,
    # so a short debounce coalesces both nameChange events into one message,
    # and the last message is remembered so a repeat of the same text (e.g.
    # both fields settling on their final value a moment apart) isn't spoken
    # twice.
    _preset_change_timer = None
    _PRESET_DEBOUNCE_MS = 200
    _last_preset_announcement = ""

    # Keyboard re-read fallback, ENABLED: live testing (2026-08-09) showed JUCE
    # does NOT fire nameChange on the preset fields, so the event hook never
    # spoke. Instead we re-read the preset fields a moment after the known
    # preset-change keystrokes (Ctrl+PageUp/PageDown). The keystroke is always
    # passed through to the app either way; this just adds the announcement.
    # (Does not cover the Next/Previous Preset buttons or a MIDI program change,
    # which have no keystroke to hook -- tracked as follow-up.)
    _preset_fallback_enabled = True

    # Measured from the running app when the index is built (see
    # _build_grid_index). These are only the starting fallback.
    grid_rows = _GRID_ROWS
    grid_cols = _GRID_COLS

    # The main signal row that the number-key jumps target. Axe-Edit's default
    # preset chain sits on row 2 (0-indexed); NVDA+Shift+<digit> jumps to that
    # row, column = digit.
    _MAIN_ROW = 2

    # ── Overlay class assignment ───────────────────────────────────────────

    def chooseNVDAObjectOverlayClasses(self, obj, clsList):
        name = obj.name or ""

        # Grid cells are identified by name, not role.
        if _GRID_RE.match(name):
            clsList.insert(0, _AxeEditGridCell)
            return

        # Routing-graphic noise, identified by its bare component name.
        if name.strip().lower() in _NOISE_NAMES:
            clsList.insert(0, _AxeEditNoise)
            return

        # On/off toggle buttons (Bypass, Scene Ignore, Channel A-D, Scene N).
        # Matched by name, NOT role: these are role 92, not a normal button (9),
        # so a role check missed them. The "<label>: On/Off" shape is unique to
        # them -- sliders end in a number, combos in a value, grid cells above.
        if _TOGGLE_NAME_RE.match(name):
            clsList.insert(0, _AxeEditToggleButton)
            return

        # Preset number/name fields, identified by name pattern like the
        # controls above -- both are plain EditControls otherwise.
        if _PRESET_FIELD_RE.match(name):
            clsList.insert(0, _AxeEditPresetField)
            return

        # Parameter-panel page tabs (Tone, Preamp, Speaker, ...). They are plain
        # static text, so match by role + membership in the discovered page
        # column (populated by get_page_tabs, called from the page-nav commands).
        # The left-edge check disambiguates them from any other label that
        # happens to share a page name. Dormant until the column has been
        # discovered once (a page command runs).
        if (
            obj.role == controlTypes.Role.STATICTEXT
            and name.strip() in self._page_name_set
            and self._is_at_page_left(obj)
        ):
            clsList.insert(0, _AxeEditPageTab)
            return

        role = obj.role
        if role == controlTypes.Role.COMBOBOX:
            clsList.insert(0, _AxeEditComboBox)
            return
        elif role == controlTypes.Role.SLIDER:
            clsList.insert(0, _AxeEditSlider)
            return

        # NOTE: R3 (Cab IR/Library selector) and R7 (Setup-window control
        # labelling) are TEMPORARILY DISABLED here. Both matched their target by
        # walking the UIA tree from inside overlay assignment
        # (_is_cab_library_value reads obj.previous; _is_setup_control walks the
        # whole foreground window). Because navigating the tree re-creates
        # objects, which re-enters chooseNVDAObjectOverlayClasses, this cascaded
        # on the static-text-heavy Cab parameter panel and hung NVDA. They will
        # be re-added with a re-entrancy-safe detection that does no tree walk in
        # this method (e.g. lazy label lookup in _get_name on the focused object
        # only). Their overlay classes and helpers remain defined but unassigned.

    # ── Setup-panel control labelling (R7) ──────────────────────────────────
    #
    # The Setup panel is not a separate top-level window -- JUCE swaps it in
    # as one large pane below the effects grid, and it reports the very same
    # windowClassName as everything else, so window class can't identify it.
    # What DOES identify it: it is the one container whose children include a
    # StaticText named "Config" (the left-hand section list's first entry,
    # present -- unchanged -- no matter which section is showing). That
    # container is located fresh on each call rather than cached: the only
    # callers are already rare (a genuinely nameless interactive control), so
    # a full tree walk on those rare occasions is cheap.

    _SETUP_NAV_ANCHOR = "config"

    def _find_setup_panel(self, obj, depth=0):
        """The Setup panel container, or None if Setup is not open."""
        if depth > 30:
            return None
        try:
            if (
                obj.role == controlTypes.Role.STATICTEXT
                and (obj.name or "").strip().lower() == self._SETUP_NAV_ANCHOR
            ):
                parent = obj.parent
                if parent is not None:
                    return parent
        except Exception:
            pass
        child = obj.firstChild
        while child:
            found = self._find_setup_panel(child, depth + 1)
            if found is not None:
                return found
            child = child.next
        return None

    def _is_setup_control(self, obj):
        """True if obj's on-screen rectangle falls inside the Setup panel."""
        try:
            loc = obj.location
        except Exception:
            loc = None
        if not loc:
            return False
        root = api.getForegroundObject()
        if root is None:
            return False
        panel = self._find_setup_panel(root)
        if panel is None:
            return False
        prect = panel.location
        if not prect:
            return False
        return (
            loc.left >= prect.left - 2
            and loc.top >= prect.top - 2
            and (loc.left + loc.width) <= (prect.left + prect.width) + 2
            and (loc.top + loc.height) <= (prect.top + prect.height) + 2
        )

    def _setup_field_label(self, obj):
        """The best-guess field label for an unnamed Setup control: the
        nearest StaticText that visually labels it, found by walking the
        Setup panel's other children and comparing on-screen rectangles.

        A field's label sits BELOW its control, sharing (most of) its
        horizontal span. Candidates are ranked by: sharing any horizontal
        span with the control first, then by being below it (not above/beside)
        second, then by vertical gap, then by how centred it is -- so a
        below/same-column label wins whenever one exists, but a section laid
        out differently still gets its nearest candidate rather than nothing.
        """
        if not self._is_setup_control(obj):
            return ""
        try:
            loc = obj.location
        except Exception:
            loc = None
        if not loc:
            return ""
        root = api.getForegroundObject()
        panel = self._find_setup_panel(root) if root is not None else None
        if panel is None:
            return ""
        candidates = []
        self._collect_setup_labels(panel, candidates, depth=0)
        if not candidates:
            return ""
        cx = loc.left + loc.width / 2.0

        def score(node):
            nloc = node.location
            left = max(loc.left, nloc.left)
            right = min(loc.left + loc.width, nloc.left + nloc.width)
            overlap = max(0, right - left)
            ncx = nloc.left + nloc.width / 2.0
            vgap = nloc.top - (loc.top + loc.height)  # > 0 -> label is below
            return (
                0 if overlap > 0 else 1,
                0 if vgap >= -2 else 1,
                abs(vgap),
                abs(ncx - cx),
            )

        best = min(candidates, key=score)
        return (best.name or "").strip().replace("\n", " ")

    def _collect_setup_labels(self, obj, out, depth):
        if depth > 30:
            return
        try:
            if obj.role == controlTypes.Role.STATICTEXT and (obj.name or "").strip():
                out.append(obj)
        except Exception:
            pass
        child = obj.firstChild
        while child:
            self._collect_setup_labels(child, out, depth + 1)
            child = child.next

    # ── Focus events ──────────────────────────────────────────────────────

    def event_gainFocus(self, obj, nextHandler):
        name = obj.name or ""

        # Swallow the jack/cable routing-graphic focus announcements.
        if self.suppress_noise and name.strip().lower() in _NOISE_NAMES:
            return

        # Right after a Space bypass the block's parameter panel reloads and can
        # steal focus; we already spoke the result, so swallow that churn (any
        # control) for the bypass window. restore_grid_focus pulls focus back.
        if self._in_bypass_window():
            return

        # During a parameter-page switch we click the tab (which transiently
        # lands focus on other controls, e.g. the channel buttons) and then
        # focus the page's first parameter ourselves, announcing it. Swallow the
        # transient focus churn in that short window so only our announcement is
        # heard.
        if (time.time() - self._page_switch_time) < self._PAGE_SWITCH_SUPPRESS_S:
            return

        # During our own grid navigation we announce concisely ourselves, so
        # suppress the verbose -- and possibly stale -- focus event that would
        # otherwise double-speak or read the old state.
        if _GRID_RE.match(name) and (time.time() - self._last_grid_prog_move) < self._GRID_SUPPRESS_S:
            return

        # The model/block picker (opened by Enter on a model combo) is a huge,
        # unnamed role-UNKNOWN overlay whose choices are drawn graphics with no
        # accessible identity -- landing on it is dead silence (it would be
        # swallowed by the structural-skip below). Rescue the user: say what it
        # is and how to get out and change the model accessibly instead.
        if self._is_opaque_picker(obj):
            speech.cancelSpeech()
            ui.message(
                "Model list is open but its choices are not accessible. Press "
                "Escape to close it, then use the arrow keys on the model to "
                "change it."
            )
            return

        # Skip unlabelled structural elements that carry no information.
        if obj.role in (
            controlTypes.Role.SEPARATOR,
            controlTypes.Role.BORDER,
            controlTypes.Role.UNKNOWN,
        ) and not obj.name:
            return

        nextHandler()

    def _is_opaque_picker(self, obj):
        """True for the full-window model/block picker overlay.

        It is a role-UNKNOWN element with no name that covers most of the window
        body; its contents are unnamed graphics (no UIA identity), so it cannot
        be presented -- we can only warn and point the user back to the arrows.
        Kept proportional to the window so it also fits other editors / DPIs.
        """
        try:
            if obj.role != controlTypes.Role.UNKNOWN or (obj.name or "").strip():
                return False
            loc = obj.location
            if not loc or not loc.width or not loc.height:
                return False
            fg = api.getForegroundObject()
            floc = fg.location if fg is not None else None
            if not floc or not floc.width or not floc.height:
                return False
            return (
                loc.width >= 0.5 * floc.width
                and loc.height >= 0.4 * floc.height
            )
        except Exception:
            return False

    def _in_bypass_window(self):
        """True during the post-Space-bypass rebuild window (covers any control,
        since re-enabling reloads the panel and can move focus off the block)."""
        return (time.time() - self._last_bypass_time) < self._BYPASS_SUPPRESS_S

    def _in_grid_suppress_window(self, obj):
        """True while we are still speaking for a grid cell ourselves (a Space
        bypass or an arrow move), so JUCE's own churn on that cell stays quiet."""
        try:
            name = obj.name or ""
        except Exception:
            return False
        return bool(
            _GRID_RE.match(name)
            and (time.time() - self._last_grid_prog_move) < self._GRID_SUPPRESS_S
        )

    def event_nameChange(self, obj, nextHandler):
        # After a Space bypass the cell's name flips Active<->Bypassed a little
        # later, and re-enabling churns the reloaded panel; NVDA would announce
        # those and cut off the state we already spoke. Swallow inside a window.
        if self._in_bypass_window() or self._in_grid_suppress_window(obj):
            return
        nextHandler()

    def event_stateChange(self, obj, nextHandler):
        # Same idea for the state churn during JUCE's rebuild.
        if self._in_bypass_window() or self._in_grid_suppress_window(obj):
            return
        nextHandler()

    # ── Preset change announcement ──────────────────────────────────────────

    def _onPresetFieldChanged(self, obj):
        """The preset-number or preset-name field's text just changed.

        Both fields update together whenever the preset changes, so debounce
        instead of announcing on the first event -- that coalesces the pair
        into a single "Preset 10, Deluxe Verb" message rather than two.
        """
        if self._preset_change_timer and self._preset_change_timer.IsRunning():
            self._preset_change_timer.Stop()
        self._preset_change_timer = wx.CallLater(
            self._PRESET_DEBOUNCE_MS, self._announcePresetChange,
        )

    def _announcePresetChange(self):
        self._preset_change_timer = None
        root = api.getForegroundObject()
        if root is None:
            return
        fields = {}
        self._collect_preset_fields(root, fields, depth=0)
        number = fields.get("number", "")
        name = fields.get("name", "")
        if not number and not name:
            return
        parts = []
        if number:
            # Leading zeros ("0010") read oddly digit-by-digit; a plain count
            # reads naturally and still identifies the same preset.
            parts.append("Preset {0}".format(number.lstrip("0") or "0"))
        if name:
            parts.append(name)
        text = ", ".join(parts)
        if not text or text == self._last_preset_announcement:
            return
        self._last_preset_announcement = text
        speech.cancelSpeech()
        ui.message(text)

    def _collect_preset_fields(self, obj, out, depth):
        """Find the current text of the preset-number and preset-name fields,
        read fresh from the tree -- a change is exactly what we're reacting
        to, so nothing here is cached."""
        if depth > 30 or len(out) >= 2:
            return
        m = _PRESET_FIELD_RE.match(obj.name or "")
        if m:
            out[m.group("field").lower()] = m.group("value").strip()
            if len(out) >= 2:
                return
        child = obj.firstChild
        while child:
            self._collect_preset_fields(child, out, depth + 1)
            if len(out) >= 2:
                return
            child = child.next

    # Guarded fallback (default OFF -- see _preset_fallback_enabled above).
    # Ctrl+PageUp/PageDown already work normally in Axe-Edit for preset
    # navigation; we only ever pass them through, optionally adding a delayed
    # re-read behind the flag if a live session shows nameChange is not
    # enough on its own.
    @script(gesture="kb:control+pageUp")
    def script_presetPrevFallback(self, gesture):
        gesture.send()
        if self._preset_fallback_enabled:
            wx.CallLater(250, self._announcePresetChange)

    @script(gesture="kb:control+pageDown")
    def script_presetNextFallback(self, gesture):
        gesture.send()
        if self._preset_fallback_enabled:
            wx.CallLater(250, self._announcePresetChange)

    # ── Grid cell cache (fast lookup for navigation) ───────────────────────

    def grid_cell(self, row, col):
        """Return the RadioButton for grid cell (row, col), using a cache.

        The cache is built with a single tree walk and reused for every
        keystroke; a stale entry is detected and triggers one rebuild.
        """
        obj = self._grid_index.get((row, col)) if self._grid_index else None
        if obj is not None:
            try:
                if _GRID_RE.match(obj.name or ""):
                    return obj
            except Exception:
                pass  # dead COM object -> fall through to rebuild
        self._build_grid_index()
        return self._grid_index.get((row, col))

    def invalidate_grid_index(self):
        self._grid_index = None

    def ensure_grid_index(self):
        """Build the cell index if we don't have one, so the measured grid
        dimensions are available before any bounds check."""
        if not self._grid_index:
            self._build_grid_index()

    # Retry cadence for restoring focus after a Space bypass. We poll instead
    # of waiting one long fixed delay, so on a quick machine focus comes back in
    # a few tens of milliseconds; on a slow one we keep trying up to the cap
    # Gentle focus-restore poll: a few tries, spaced out, exiting as soon as
    # focus is back on the cell. We do NOT hammer setFocus every few ms -- that
    # was fighting JUCE's own rebuild and making the toggle feel slower. The
    # spoken feedback is already out (predicted), so this can afford to be calm.
    _REFOCUS_RETRY_MS = 70
    _REFOCUS_MAX_ATTEMPTS = 8

    def restore_grid_focus(self, row, col, attempt=0):
        """Silently put focus back on grid cell (row, col) after a Space toggle.

        Speaking is handled separately (the predicted state is already out, and
        ``verify_bypass_state`` confirms it), so this only shepherds focus:

        * Focus already on the target cell -> done.
        * Focus on a different grid cell -> the user arrowed away; leave them.
        * Focus lost -> re-find the (possibly rebuilt) cell, put focus back, and
          check again on the next tick.
        """
        focus = api.getFocusObject()
        m = _GRID_RE.match((focus.name if focus is not None else "") or "")
        if m:
            # On the target cell, or the user moved to another cell: either way
            # stop -- never keep grabbing focus back from where the user went.
            return

        # Focus is lost. Re-find the cell (self-healing if the node was rebuilt)
        # and put focus back on it, without speaking.
        cell = self.grid_cell(row, col)
        if cell is not None:
            self._last_grid_prog_move = time.time()
            try:
                cell.setFocus()
            except Exception:
                self.invalidate_grid_index()

        if attempt + 1 < self._REFOCUS_MAX_ATTEMPTS:
            wx.CallLater(
                self._REFOCUS_RETRY_MS,
                self.restore_grid_focus, row, col, attempt + 1,
            )

    # ── On/off button focus restore (after Enter) ──────────────────────────

    # Switching a channel triggers a large JUCE rebuild (the whole block's
    # parameter panel reloads), which clears keyboard focus and can take a
    # while. So the first attempt waits for that to begin, and we keep trying --
    # verifying focus actually landed -- across a generous window rather than
    # giving up early and leaving Tab with no anchor.
    _BUTTON_REFOCUS_FIRST_MS = 250
    _BUTTON_REFOCUS_RETRY_MS = 130
    _BUTTON_REFOCUS_MAX_ATTEMPTS = 16

    @staticmethod
    def _toggle_label_of(obj):
        """Label of a toggle button, whether or not our overlay has relabelled
        it. The overlay renames "Channel C: Off" to "Channel C", so we ask the
        overlay directly when present and fall back to the raw-name pattern."""
        if obj is None:
            return None
        if isinstance(obj, _AxeEditToggleButton):
            return obj._button_label()
        m = _TOGGLE_NAME_RE.match(obj.name or "")
        return m.group("label").strip() if m else None

    def restore_button_focus(self, label, box, attempt=0):
        """Re-anchor keyboard focus on a toggle button after Enter activated it.

        Activation clears keyboard focus (confirmed: the stuck state had no
        focused control at all, so Tab had nothing to move from). We re-find the
        button by its stable label (e.g. "Channel C", unchanged by the On/Off
        flip) nearest its old screen position, focus it, and -- crucially --
        verify on the next tick that focus actually landed, retrying across the
        rebuild until it sticks or the window is exhausted.
        """
        if attempt == 0:
            wx.CallLater(
                self._BUTTON_REFOCUS_FIRST_MS,
                self.restore_button_focus, label, box, 1,
            )
            return

        if self._toggle_label_of(api.getFocusObject()) == label:
            return  # focus verified back on the button -- done

        target = self._find_toggle_button(label, box)
        if target is not None:
            try:
                target.setFocus()
            except Exception:
                pass

        if attempt < self._BUTTON_REFOCUS_MAX_ATTEMPTS:
            wx.CallLater(
                self._BUTTON_REFOCUS_RETRY_MS,
                self.restore_button_focus, label, box, attempt + 1,
            )

    def _find_toggle_button(self, label, box):
        root = api.getForegroundObject()
        if root is None:
            return None
        matches = []
        self._collect_toggle_buttons(root, label, matches, depth=0)
        if not matches:
            return None
        if box is None:
            return matches[0]
        cx = box.left + box.width // 2
        cy = box.top + box.height // 2

        def dist(o):
            loc = o.location
            if not loc:
                return 10 ** 18
            ox = loc.left + loc.width // 2
            oy = loc.top + loc.height // 2
            return (ox - cx) ** 2 + (oy - cy) ** 2

        return min(matches, key=dist)

    def _collect_toggle_buttons(self, obj, label, out, depth):
        if depth > 30:
            return
        # Match via _toggle_label_of so this works whether the tree-walk object
        # has our overlay (name already "Channel C") or the raw "Channel C: Off".
        if self._toggle_label_of(obj) == label:
            out.append(obj)
        child = obj.firstChild
        while child:
            self._collect_toggle_buttons(child, label, out, depth + 1)
            child = child.next

    # ── Focus recovery to an adjacent combo (after a channel switch) ────────

    # The first attempt runs immediately (synchronously, right after the toggle),
    # so there is no initial wait. We acquire the combo by SCREEN POINT via
    # objectFromPoint, not a cached object: the point stays valid even when the
    # combo behind it is rebuilt, so we get a fresh, live object every time (a
    # stale cached object wedged keyboard focus) with no tree walk (fast). We
    # stop the instant focus is on a combo and never grab again, so we do not
    # fight the user's next Tab.
    _COMBO_RECOVER_RETRY_MS = 60
    _COMBO_RECOVER_MAX_ATTEMPTS = 16

    # Cached screen point of the recovery combo (coordinates are stable across
    # rebuilds even though the object at them is not).
    _combo_point = None

    def recover_focus_to_combo(self, box, attempt=0):
        """Land keyboard focus on the combo below ``box``, acquiring it live by
        screen point each attempt, until focus is verified on a combo box."""
        focus = api.getFocusObject()
        try:
            if focus is not None and focus.role == controlTypes.Role.COMBOBOX:
                return  # focus is on a combo -- done; do not grab again
        except Exception:
            pass

        combo = self._acquire_combo(box)
        if combo is not None:
            try:
                combo.setFocus()
            except Exception:
                pass

        if attempt < self._COMBO_RECOVER_MAX_ATTEMPTS:
            wx.CallLater(
                self._COMBO_RECOVER_RETRY_MS,
                self.recover_focus_to_combo, box, attempt + 1,
            )

    def _acquire_combo(self, box):
        """Return the live recovery combo, preferring a fast point hit-test over
        a tree walk. The point is cached (coordinates don't go stale); if the
        hit-test no longer lands on a combo we re-find and re-cache the point."""
        pt = self._combo_point
        if pt is not None:
            obj = self._combo_at_point(*pt)
            if obj is not None:
                return obj
        combo = self._find_nearest_combo(box)
        if combo is not None:
            loc = combo.location
            if loc:
                self._combo_point = (
                    loc.left + loc.width // 2, loc.top + loc.height // 2,
                )
        return combo

    @staticmethod
    def _combo_at_point(x, y):
        """The combo NVDAObject at screen point (x, y), or None. Uses UIA's
        hit-test (no tree walk) and always returns a live object."""
        try:
            obj = NVDAObjects.NVDAObject.objectFromPoint(x, y)
        except Exception:
            return None
        try:
            if obj is not None and obj.role == controlTypes.Role.COMBOBOX:
                return obj
        except Exception:
            pass
        return None

    def _find_nearest_combo(self, box):
        root = api.getForegroundObject()
        if root is None:
            return None
        combos = []
        self._collect_combos(root, combos, depth=0)
        if not combos:
            return None
        if box is None:
            return combos[0]
        cx = box.left + box.width // 2
        cy = box.top + box.height // 2

        def dist(o):
            loc = o.location
            if not loc:
                return 10 ** 18
            ox = loc.left + loc.width // 2
            oy = loc.top + loc.height // 2
            return (ox - cx) ** 2 + (oy - cy) ** 2

        return min(combos, key=dist)

    def _collect_combos(self, obj, out, depth):
        if depth > 30:
            return
        try:
            if obj.role == controlTypes.Role.COMBOBOX:
                out.append(obj)
        except Exception:
            pass
        child = obj.firstChild
        while child:
            self._collect_combos(child, out, depth + 1)
            child = child.next

    @staticmethod
    def _cell_state_text(cell):
        """"Grid row 2 column 5: Amp 1A, Bypassed" -> "Amp 1A, Bypassed"."""
        name = cell.name or ""
        return _GRID_RE.sub("", name).strip(" :") or name

    def jump_to_cell(self, row, col):
        """Focus a specific grid cell from anywhere and announce it.

        Returns True if the cell was found and focused.
        """
        target = self.grid_cell(row, col)
        if target is None:
            speech.cancelSpeech()
            ui.message("No cell at row {0} column {1}".format(row, col))
            return False
        self._last_grid_prog_move = time.time()
        try:
            target.setFocus()
        except Exception:
            self.invalidate_grid_index()
            target = self.grid_cell(row, col)
            if target is None:
                return False
            self._last_grid_prog_move = time.time()
            target.setFocus()
        speech.cancelSpeech()
        ui.message(target.name or "")
        return True

    def _build_grid_index(self):
        index = {}
        root = api.getForegroundObject()
        if root:
            self._collect_grid_cells(root, index, depth=0)
        self._grid_index = index
        # Measure the grid rather than assuming the Axe-Fx III shape, so the
        # module also fits editors with a differently-sized grid.
        if index:
            self.grid_rows = max(r for r, _ in index) + 1
            self.grid_cols = max(c for _, c in index) + 1

    def _collect_grid_cells(self, obj, index, depth):
        if depth > 30:
            return
        m = _GRID_RE.match(obj.name or "")
        if m:
            index[(int(m.group(1)), int(m.group(2)))] = obj
        child = obj.firstChild
        while child:
            self._collect_grid_cells(child, index, depth + 1)
            child = child.next

    # ── Toggle commands ───────────────────────────────────────────────────

    @script(
        description="Axe-Edit: Toggle jack/cable routing-graphic noise suppression",
        gesture="kb:NVDA+shift+j",
    )
    def script_toggleNoise(self, gesture):
        self.suppress_noise = not self.suppress_noise
        ui.message(
            "Routing graphics {0}".format(
                "hidden" if self.suppress_noise else "shown"
            )
        )

    @script(
        description="Axe-Edit: Toggle 2D arrow-key grid navigation",
        gesture="kb:NVDA+shift+g",
    )
    def script_toggleGridArrows(self, gesture):
        self.grid_arrows_enabled = not self.grid_arrows_enabled
        ui.message(
            "Grid arrow navigation {0}".format(
                "on" if self.grid_arrows_enabled else "off"
            )
        )

    # ── Parameter-panel page navigation (Tone, Preamp, Speaker, ...) ────────
    #
    # The pages are a vertical column of role-STATICTEXT labels that share a
    # left edge and width and stack contiguously. They are NOT a tab control:
    # no tab role, no SELECTED state, value just echoes the name -- so which
    # page is current is not exposed to the tree (only a colour highlight), and
    # JUCE fires no event when it changes. So we drive it ourselves: discover
    # the column, keep our own cursor into it, click the target tab (absolute
    # synth click, the only thing these custom widgets honour) and speak it.

    _page_index = 0
    _page_names = ()               # last discovered page names (detects block change)
    _page_name_set = frozenset()   # cheap membership test for the overlay
    _page_left = None              # left x of the column (disambiguates the overlay)
    _PAGE_MIN_RUN = 3              # a real page column is at least this many labels
    # JUCE DE-EXPOSES the page-tab column from the accessibility tree after we
    # click a tab (confirmed live: first press finds 10 tabs at left=336, every
    # press after finds none). So we cache each tab's name + click centre from
    # the last successful discovery and click by cached coordinates on later
    # presses, only re-walking the tree when the selected block changes.
    _page_coords = ()              # cached ((name, cx, cy), ...) from last discovery
    _page_cache_block = None       # selected-block label the cache belongs to
    # Clicking a page tab transiently lands focus on other controls (e.g. the
    # channel buttons) before we focus the page's first param ourselves. Swallow
    # that focus churn for a short window so only our announcement is heard.
    _page_switch_time = 0.0
    _PAGE_SWITCH_SUPPRESS_S = 0.6

    def _collect_statictexts(self, obj, out, depth):
        if depth > 30:
            return
        try:
            if obj.role == controlTypes.Role.STATICTEXT:
                name = (obj.name or "").strip()
                loc = obj.location
                if name and loc and loc.width and loc.height:
                    out.append(obj)
        except Exception:
            pass
        child = obj.firstChild
        while child:
            self._collect_statictexts(child, out, depth + 1)
            child = child.next

    def get_page_tabs(self):
        """Discover the parameter panel's page-tab column.

        Returns the page-tab NVDAObjects top-to-bottom, or [] if none. The pages
        are the longest run of same-role static-text labels that share a
        ``(left, width)`` and stack in a contiguous vertical line -- unique to
        the page column in this UI (param captions are role-7 too but scattered
        across the knob area, never forming a uniform column). Resets the page
        cursor when the set of names changes (a different block's panel loaded)
        and refreshes the overlay's membership/left-edge caches.
        """
        root = api.getForegroundObject()
        if root is None:
            return []
        texts = []
        self._collect_statictexts(root, texts, depth=0)
        buckets = {}
        for o in texts:
            loc = o.location
            buckets.setdefault((loc.left, loc.width), []).append(o)
        best = []
        for group in buckets.values():
            if len(group) < self._PAGE_MIN_RUN:
                continue
            group.sort(key=lambda o: o.location.top)
            run = [group[0]]
            longest = run
            for prev, cur in zip(group, group[1:]):
                gap = cur.location.top - (prev.location.top + prev.location.height)
                # Contiguous = next label starts about where the previous ended
                # (tabs here slightly overlap: step 64, height 66 -> gap ~= -2).
                if -(prev.location.height // 2) <= gap <= prev.location.height:
                    run.append(cur)
                else:
                    run = [cur]
                if len(run) > len(longest):
                    longest = run
            if len(longest) > len(best):
                best = longest
        if len(best) < self._PAGE_MIN_RUN:
            return []
        names = tuple((o.name or "").strip() for o in best)
        if names != self._page_names:
            self._page_names = names
            self._page_index = 0
        self._page_name_set = frozenset(names)
        self._page_left = best[0].location.left
        return best

    def _is_at_page_left(self, obj):
        """True if obj sits at the discovered page column's left edge."""
        if self._page_left is None:
            return False
        try:
            loc = obj.location
            return bool(loc) and abs(loc.left - self._page_left) <= 4
        except Exception:
            return False

    def _page_tab_coords(self):
        """Return the page tabs as ((name, cx, cy), ...) click-centre tuples.

        Prefers a fresh tree walk (get_page_tabs), which refreshes the cache;
        but JUCE de-exposes the column after we click a tab, so when the walk
        comes back empty we fall back to the cached coordinates -- as long as we
        are still on the same block (else the cache is stale and we clear it).
        """
        block = self._selected_block_label()
        tabs = self.get_page_tabs()
        if tabs:
            coords = []
            for o in tabs:
                loc = o.location
                if loc:
                    coords.append((
                        (o.name or "").strip(),
                        loc.left + loc.width // 2,
                        loc.top + loc.height // 2,
                    ))
            if len(coords) >= self._PAGE_MIN_RUN:
                self._page_coords = tuple(coords)
                self._page_cache_block = block
                return self._page_coords
        # Tree walk found nothing usable. Reuse the cache only if we are still on
        # the block it was built for (the column was just de-exposed by our own
        # click); otherwise the cache is stale.
        if self._page_coords and block == self._page_cache_block:
            return self._page_coords
        self._page_coords = ()
        self._page_cache_block = None
        return ()

    def _select_page(self, delta):
        """Move the page cursor by delta, click that tab so the app switches to
        it, and speak its name. Clicking is what makes the announcement truthful
        -- we say exactly the page we activated, never a state we cannot read."""
        coords = self._page_tab_coords()
        if not coords:
            speech.cancelSpeech()
            ui.message("No parameter pages here")
            return
        new_index = max(0, min(self._page_index + delta, len(coords) - 1))
        self._page_index = new_index
        name, cx, cy = coords[new_index]
        speech.cancelSpeech()
        self._page_switch_time = time.time()  # suppress the click's focus churn
        self._click_point(cx, cy)
        # Land on the new page's first parameter (no separate NVDA+Shift+F
        # needed). The page has to re-render after the click first, so defer the
        # focus; the announcement then carries both the page and where we landed.
        wx.CallLater(
            self._PAGE_FOCUS_DELAY_MS,
            self._focus_first_param, name or "Page {0}".format(new_index + 1),
        )

    _PAGE_FOCUS_DELAY_MS = 250

    def _focus_first_param(self, prefix=""):
        """Focus the first parameter of the current block/page and announce it.

        Same selection as NVDA+Shift+F (tree-order first on the Cab block,
        geometric top-left elsewhere). If a prefix is given (the page name), the
        announcement is "<page>, <param>" so a page switch says both at once.
        """
        root = api.getForegroundObject()
        candidates = []
        if root is not None:
            self._collect_params(root, candidates, depth=0)
        if not candidates:
            if prefix:
                speech.cancelSpeech()
                ui.message(prefix)
            return
        if self._on_cab_block():
            param = candidates[0]
        else:
            param = min(candidates, key=self._param_sort_key)
        try:
            param.setFocus()
        except Exception:
            pass
        speech.cancelSpeech()
        pname = _clean_value_name(param.name) or param.name or "Parameter"
        ui.message("{0}, {1}".format(prefix, pname) if prefix else pname)

    @script(
        description="Axe-Edit: Next parameter page (Tone, Preamp, Speaker, ...)",
        gesture="kb:NVDA+shift+pageDown",
    )
    def script_nextPage(self, gesture):
        self._select_page(1)

    @script(
        description="Axe-Edit: Previous parameter page",
        gesture="kb:NVDA+shift+pageUp",
    )
    def script_prevPage(self, gesture):
        self._select_page(-1)

    # ── Cabling (create connections between blocks) ────────────────────────
    #
    # Axe-Edit's routing cables carry no accessible identity, so they can't be
    # read from the tree -- but connections can still be MADE. Confirmed on
    # hardware: the grid uses a click-to-connect mode. Clicking a block's output
    # jack (right edge of the cell) primes the grid and lights up the valid
    # destinations; clicking a target block's input jack (left edge) then lays
    # the cable. No mouse drag is involved. The primed state is time-sensitive,
    # so we gather both endpoints by keyboard first (touching nothing), then fire
    # the two clicks back-to-back only once the user confirms the target.
    #
    # Jack positions come from each cell's real on-screen rectangle. Measured
    # from live coordinates: the jacks sit in the GUTTERS just OUTSIDE each cell
    # edge, at mid-height -- the input jack ~11% of the cell width to the left of
    # the left edge, the output jack ~11% to the right of the right edge (NOT
    # inside the cell). Using the cell's real width keeps this correct across
    # window sizes and display scaling. Series, parallel and diagonal routing
    # all use this same two-click path.

    _cable_source = None          # (row, col, label) of an armed source, or None
    _CABLE_OUTPUT_X_RATIO = 1.11  # output jack: just past the right edge, in the gutter
    _CABLE_INPUT_X_RATIO = -0.11  # input jack: just before the left edge, in the gutter
    _CABLE_PORT_Y_RATIO = 0.5     # jacks sit at the cell's vertical midline
    _CABLE_STEP_DELAY_MS = 150    # gap between the two clicks (the primed window)

    @script(
        description="Axe-Edit: Start a cable from this block, or connect to it "
                    "(press on the source block, then on the target block)",
        gesture="kb:NVDA+shift+c",
    )
    def script_cable(self, gesture):
        focus = api.getFocusObject()
        name = (focus.name if focus is not None else "") or ""
        m = _GRID_RE.match(name)
        if not m:
            speech.cancelSpeech()
            ui.message("Cabling works on the grid. Move to a block first.")
            return
        row, col = int(m.group(1)), int(m.group(2))
        label = _cable_block_label(name) or "block"

        # First press: arm the source (its output jack).
        if self._cable_source is None:
            if label.lower() == "empty":
                ui.message("That cell is empty. Move to a block to start a cable.")
                return
            self._cable_source = (row, col, label)
            speech.cancelSpeech()
            ui.message(
                "Cable from {0}. Move to the target block and press the cable "
                "key again.".format(label)
            )
            return

        # Second press: complete to the target (its input jack), or cancel.
        src_row, src_col, src_label = self._cable_source
        if (row, col) == (src_row, src_col):
            self._cable_source = None
            speech.cancelSpeech()
            ui.message("Cable cancelled.")
            return
        if label.lower() == "empty":
            ui.message(
                "Target cell is empty. Move to a block, or press the cable key "
                "on the source block again to cancel."
            )
            return

        self._cable_source = None
        speech.cancelSpeech()
        if self._make_cable(src_row, src_col, row, col):
            ui.message("Connected {0} to {1}.".format(src_label, label))
            # The synthesized clicks drop keyboard focus; put it back on the
            # target block quietly so the user stays oriented. The "Connected"
            # message is already out, and the grid-suppress window (set in
            # _make_cable) keeps this restore from speaking over it.
            self._last_grid_prog_move = time.time()
            wx.CallLater(120, self.restore_grid_focus, row, col, 0)
        else:
            ui.message(
                "Could not cable to {0}: block position unavailable.".format(label)
            )

    def cancel_pending_cable(self):
        """Cancel an armed cable if one is pending. Returns True if it was."""
        if self._cable_source is not None:
            self._cable_source = None
            speech.cancelSpeech()
            ui.message("Cable cancelled.")
            return True
        return False

    def _cable_point(self, cell, x_ratio):
        """The (x, y) of a jack on ``cell``, from its real on-screen rect."""
        loc = cell.location if cell is not None else None
        if not loc:
            return None
        return (
            loc.left + round(loc.width * x_ratio),
            loc.top + round(loc.height * self._CABLE_PORT_Y_RATIO),
        )

    def _make_cable(self, src_row, src_col, tgt_row, tgt_col):
        """Lay a cable from the source block's output to the target's input by
        clicking the two jacks back-to-back.

        Returns True if the clicks were issued. It is not a guarantee the cable
        took -- Axe-Edit's cables can't be read back -- so the caller speaks the
        intended connection as the confirmation.
        """
        src = self.grid_cell(src_row, src_col)
        tgt = self.grid_cell(tgt_row, tgt_col)
        out_pt = self._cable_point(src, self._CABLE_OUTPUT_X_RATIO)
        in_pt = self._cable_point(tgt, self._CABLE_INPUT_X_RATIO)
        if out_pt is None or in_pt is None:
            return False
        log.info(
            "axedit cable: src(%d,%d)->tgt(%d,%d) out=%s in=%s "
            "src_rect=%s tgt_rect=%s"
            % (
                src_row, src_col, tgt_row, tgt_col, out_pt, in_pt,
                self._rect_tuple(src), self._rect_tuple(tgt),
            )
        )
        # The synthesized clicks churn focus/name/state on the grid; open the
        # existing suppression windows so that churn can't cut off the spoken
        # confirmation or leak stale events.
        now = time.time()
        self._last_grid_prog_move = now
        self._last_bypass_time = now
        # Both clicks TIGHT and uninterrupted: the grid's primed routing state
        # drops if too long passes between them, and a deferred (wx.CallLater)
        # second click waits behind whatever NVDA is doing -- e.g. speaking the
        # jack under the mouse -- which stretched the gap past that window. We
        # cancel speech and click both jacks synchronously so nothing slips in.
        speech.cancelSpeech()
        self._click_point(*out_pt)
        time.sleep(self._CABLE_STEP_DELAY_MS / 1000.0)
        self._click_point(*in_pt)
        return True

    @staticmethod
    def _rect_tuple(cell):
        loc = cell.location if cell is not None else None
        return (loc.left, loc.top, loc.width, loc.height) if loc else None

    # Mouse-event flags for the absolute-coordinate click below.
    _MOUSEEVENTF_MOVE = 0x0001
    _MOUSEEVENTF_LEFTDOWN = 0x0002
    _MOUSEEVENTF_LEFTUP = 0x0004
    _MOUSEEVENTF_RIGHTDOWN = 0x0008
    _MOUSEEVENTF_RIGHTUP = 0x0010
    _MOUSEEVENTF_ABSOLUTE = 0x8000

    @classmethod
    def _click_point(cls, x, y):
        """A single synthesized left click at screen point (x, y).

        The coordinates are baked into each mouse event as ABSOLUTE values
        (normalised 0..65535 over the primary screen). NVDA's default helper
        sends a position-less down/up and relies on the cursor already being
        parked there; JUCE's grid appears to read the coordinates off the event,
        so a position-less click aimed perfectly can still do nothing -- the
        absolute-coordinate form is what actually registers here. Small gaps let
        the move settle and the press register.
        """
        x, y = int(round(x)), int(round(y))
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0) or 1  # SM_CXSCREEN
        sh = user32.GetSystemMetrics(1) or 1  # SM_CYSCREEN
        ax = (65536 * x) // sw + 1
        ay = (65536 * y) // sh + 1
        user32.SetCursorPos(x, y)
        time.sleep(0.05)
        user32.mouse_event(cls._MOUSEEVENTF_MOVE | cls._MOUSEEVENTF_ABSOLUTE, ax, ay, 0, 0)
        time.sleep(0.02)
        user32.mouse_event(cls._MOUSEEVENTF_LEFTDOWN | cls._MOUSEEVENTF_ABSOLUTE, ax, ay, 0, 0)
        time.sleep(0.03)
        user32.mouse_event(cls._MOUSEEVENTF_LEFTUP | cls._MOUSEEVENTF_ABSOLUTE, ax, ay, 0, 0)

    @classmethod
    def _right_click_point(cls, x, y):
        """A single synthesized RIGHT click at screen point (x, y).

        Mirrors ``_click_point`` exactly -- same ABSOLUTE-coordinate technique,
        same small settle/press gaps -- but fires RIGHTDOWN/RIGHTUP instead of
        LEFTDOWN/LEFTUP, to pop a block's context menu at the focused grid
        cell (the Applications key) instead of clicking a jack.
        """
        x, y = int(round(x)), int(round(y))
        user32 = ctypes.windll.user32
        sw = user32.GetSystemMetrics(0) or 1  # SM_CXSCREEN
        sh = user32.GetSystemMetrics(1) or 1  # SM_CYSCREEN
        ax = (65536 * x) // sw + 1
        ay = (65536 * y) // sh + 1
        user32.SetCursorPos(x, y)
        time.sleep(0.05)
        user32.mouse_event(cls._MOUSEEVENTF_MOVE | cls._MOUSEEVENTF_ABSOLUTE, ax, ay, 0, 0)
        time.sleep(0.02)
        user32.mouse_event(cls._MOUSEEVENTF_RIGHTDOWN | cls._MOUSEEVENTF_ABSOLUTE, ax, ay, 0, 0)
        time.sleep(0.03)
        user32.mouse_event(cls._MOUSEEVENTF_RIGHTUP | cls._MOUSEEVENTF_ABSOLUTE, ax, ay, 0, 0)

    # ── Top menu bar (Alt+letter opens each menu) ──────────────────────────

    # The menu bar is five JUCE menu-bar items (NVDA role MENUITEM) named
    # "Preset", "Block", "Tools", "Settings", "Help". They open only on a
    # mouse click / invoke, so plain Alt+letter does nothing by default. We bind
    # the natural Alt+<initial> to find the item by name and invoke it.

    def _open_menu(self, label, gesture=None):
        root = api.getForegroundObject()
        item = self._find_menu_item(root, label, depth=0) if root else None
        # A menu bar item opens on click; its own action may not, so allow the
        # mouse-click fallback here (unlike the focus-losing on/off buttons).
        if item is not None and _invoke_control(item, allow_mouse=True):
            speech.cancelSpeech()
            ui.message("{0} menu".format(label))
            return
        # Couldn't find/open it -- let the app have the keystroke.
        if gesture is not None:
            gesture.send()

    def _find_menu_item(self, obj, label, depth):
        if depth > 30:
            return None
        try:
            if obj.role == controlTypes.Role.MENUITEM and (
                (obj.name or "").strip().lower() == label.lower()
            ):
                return obj
        except Exception:
            pass
        child = obj.firstChild
        while child:
            found = self._find_menu_item(child, label, depth + 1)
            if found is not None:
                return found
            child = child.next
        return None

    @script(description="Axe-Edit: Open the Preset menu", gesture="kb:alt+p")
    def script_menuPreset(self, gesture):
        self._open_menu("Preset", gesture)

    @script(description="Axe-Edit: Open the Block menu", gesture="kb:alt+b")
    def script_menuBlock(self, gesture):
        self._open_menu("Block", gesture)

    @script(description="Axe-Edit: Open the Tools menu", gesture="kb:alt+t")
    def script_menuTools(self, gesture):
        self._open_menu("Tools", gesture)

    @script(description="Axe-Edit: Open the Settings menu", gesture="kb:alt+s")
    def script_menuSettings(self, gesture):
        self._open_menu("Settings", gesture)

    @script(description="Axe-Edit: Open the Help menu", gesture="kb:alt+h")
    def script_menuHelp(self, gesture):
        self._open_menu("Help", gesture)

    # ── Preset import / export shortcuts ────────────────────────────────
    #
    # The Preset menu already has Import Preset / Export Preset items that
    # load and save a preset file from disk -- they only respond to a mouse
    # click, with no keyboard shortcut. Ctrl+I / Ctrl+E open the Preset menu
    # (reusing the same menu-bar lookup the Alt+P shortcut above uses) and
    # then try to invoke whichever child item's name CONTAINS "Import"/"Export".
    # NOTE (2026-08-09): INCOMPLETE -- the Ctrl+I / Ctrl+E gestures below are
    # UNBOUND for now. When the Preset menu opens it is a SEPARATE POPUP that is
    # not under getForegroundObject(), so _invoke_menu_child can't find the item
    # (the menu opens but the action never fires). Pending a keystroke-driven
    # rebuild; the code is kept for reference.

    _MENU_CHILD_SETTLE_MS = 150

    def _invoke_menu_command(self, menu_label, item_keyword, gesture=None):
        root = api.getForegroundObject()
        menu = self._find_menu_item(root, menu_label, depth=0) if root else None
        if menu is None or not _invoke_control(menu, allow_mouse=True):
            if gesture is not None:
                gesture.send()
            return
        wx.CallLater(
            self._MENU_CHILD_SETTLE_MS,
            self._invoke_menu_child, item_keyword,
        )

    def _invoke_menu_child(self, item_keyword):
        root = api.getForegroundObject()
        item = (
            self._find_menu_item_containing(root, item_keyword, depth=0)
            if root else None
        )
        if item is not None:
            _invoke_control(item, allow_mouse=True)

    def _find_menu_item_containing(self, obj, keyword, depth):
        """Like _find_menu_item, but matches a menu item whose name CONTAINS
        keyword (case-insensitive) rather than requiring an exact label --
        used for submenu items whose precise wording we don't want to
        hard-code."""
        if depth > 30:
            return None
        try:
            if obj.role == controlTypes.Role.MENUITEM and (
                keyword.lower() in (obj.name or "").strip().lower()
            ):
                return obj
        except Exception:
            pass
        child = obj.firstChild
        while child:
            found = self._find_menu_item_containing(child, keyword, depth + 1)
            if found is not None:
                return found
            child = child.next
        return None

    # Unbound (no gesture=) pending the rebuild described above.
    @script(
        description="Axe-Edit: Import a preset file (Preset menu) [unbound, WIP]",
    )
    def script_importPreset(self, gesture):
        self._invoke_menu_command("Preset", "Import", gesture)

    @script(
        description="Axe-Edit: Export a preset file (Preset menu) [unbound, WIP]",
    )
    def script_exportPreset(self, gesture):
        self._invoke_menu_command("Preset", "Export", gesture)

    # ── Section navigation ────────────────────────────────────────────────

    @script(
        description="Axe-Edit: Move focus to Amp block parameters",
        gesture="kb:NVDA+shift+a",
    )
    def script_goToAmpBlock(self, gesture):
        self._focus_section(["amp block", "amp", "amplifier"], label="Amp block")

    @script(
        description="Axe-Edit: Move focus to Effects grid",
        gesture="kb:NVDA+shift+e",
    )
    def script_goToEffects(self, gesture):
        # Land on the first real grid cell rather than a container.
        cell = self.grid_cell(0, 0)
        if cell:
            self._last_grid_prog_move = time.time()
            cell.setFocus()
            speech.cancelSpeech()
            ui.message(cell.name or "Effects grid")
        else:
            self._focus_section(["grid", "effects"], label="Effects")

    @script(
        description="Axe-Edit: Move focus to Preset selector",
        gesture="kb:NVDA+shift+p",
    )
    def script_goToPreset(self, gesture):
        self._focus_section(["preset name", "preset"], label="Preset selector")

    @script(
        description="Axe-Edit: Move focus to Scene selector",
        gesture="kb:NVDA+shift+s",
    )
    def script_goToScene(self, gesture):
        self._focus_section(["scene number", "scene"], label="Scene selector")

    @script(
        description="Axe-Edit: Announce full info about the focused control",
        gesture="kb:NVDA+shift+i",
    )
    def script_announceInfo(self, gesture):
        obj = api.getFocusObject()
        if not obj:
            ui.message("No focused control")
            return

        parts = []
        if obj.name:
            parts.append(obj.name)

        try:
            parts.append(obj.role.displayString)
        except AttributeError:
            parts.append(str(obj.role))

        if obj.value:
            parts.append(obj.value)

        states = obj.states
        if controlTypes.State.CHECKED in states:
            parts.append("on")
        elif controlTypes.State.CHECKABLE in states:
            parts.append("off")
        if controlTypes.State.READONLY in states:
            parts.append("read only")
        if controlTypes.State.UNAVAILABLE in states:
            parts.append("unavailable")

        ui.message(", ".join(parts) if parts else "Unknown control")

    @script(
        description="Axe-Edit: Activate focused control (works on mouse-only items)",
        gesture="kb:NVDA+shift+space",
    )
    def script_activateControl(self, gesture):
        obj = api.getFocusObject()
        if not obj:
            return
        if not _invoke_control(obj):
            ui.message("Cannot determine control location")

    @script(
        description="Axe-Edit: Jump to a column on the main signal row "
                    "(NVDA+Ctrl+0 through 9 = row 2, columns 0-9)",
        gestures=["kb:NVDA+control+{0}".format(d) for d in range(10)],
    )
    def script_jumpMainRowColumn(self, gesture):
        digit = self._gesture_digit(gesture)
        if digit is None:
            return
        self.jump_to_cell(self._MAIN_ROW, digit)

    @staticmethod
    def _gesture_digit(gesture):
        """Extract 0-9 from a number-row gesture, robust to naming."""
        key = getattr(gesture, "mainKeyName", "") or ""
        # mainKeyName is typically the bare character, e.g. "5".
        if len(key) == 1 and key.isdigit():
            return int(key)
        # Fallback: last character of the display name (e.g. "NVDA+control+5").
        disp = getattr(gesture, "displayName", "") or ""
        if disp and disp[-1].isdigit():
            return int(disp[-1])
        return None

    @script(
        description="Axe-Edit: Jump to the first parameter of the current block",
        gesture="kb:NVDA+shift+f",
    )
    def script_goToFirstParam(self, gesture):
        """Focus the first editable parameter (slider or param combo) in the
        parameters panel of the currently-selected block."""
        root = api.getForegroundObject()
        if not root:
            ui.message("Axe-Edit is not in the foreground")
            return
        candidates = []
        self._collect_params(root, candidates, depth=0)
        if not candidates:
            ui.message("No parameters found")
            return
        # The "first" parameter is normally the visually top-most, then
        # left-most one (matches where a sighted user's cursor lands: the first
        # knob). The Cab block is the exception: its panel stacks two or more
        # identical cab columns side by side, all sharing the same row tops, plus
        # a block-output column (Level/Balance) whose slider sits a few pixels
        # ABOVE the first cab row. Geometry then lands on the output column or
        # the wrong cab rather than the panel's genuine first control. For the
        # Cab block we instead take the first parameter in tree (tab) order --
        # the order _collect_params already appends them in -- which is the true
        # first focusable control no matter how the columns are laid out.
        if self._on_cab_block():
            param = candidates[0]
        else:
            param = min(candidates, key=self._param_sort_key)
        param.setFocus()
        speech.cancelSpeech()
        ui.message(_clean_value_name(param.name) or param.name or "Parameter")

    _PARAM_ROLES = frozenset({
        controlTypes.Role.SLIDER,
        controlTypes.Role.COMBOBOX,
    })

    @staticmethod
    def _param_sort_key(obj):
        loc = obj.location
        if loc:
            return (loc.top, loc.left)
        return (10 ** 9, 10 ** 9)

    def _collect_params(self, obj, out, depth):
        if depth > 30:
            return
        if obj.role in self._PARAM_ROLES:
            name = obj.name or ""
            # A genuine parameter carries a "Label: value" style name; skip
            # empty/utility combos and routing controls.
            if ":" in name and name.strip().lower() not in _NOISE_NAMES:
                out.append(obj)
        child = obj.firstChild
        while child:
            self._collect_params(child, out, depth + 1)
            child = child.next

    # Cab-block detection for the first-parameter jump (script_goToFirstParam).
    # A block's parameter panel belongs to whichever grid cell is currently
    # SELECTED (the cell Axe-Edit loaded the params from). Grid cells report that
    # selection as a truthful value of "On" -- our grid overlay hides it from the
    # spoken states, but leaves the underlying value intact -- so we read the
    # selected cell's block label from the grid index the module already keeps.
    def _selected_block_label(self):
        self.ensure_grid_index()
        for cell in (self._grid_index or {}).values():
            try:
                if (cell.value or "").strip().lower() == "on":
                    return _cable_block_label(cell.name or "")
            except Exception:
                continue
        return ""

    def _on_cab_block(self):
        """True when the selected block (whose params are on screen) is a Cab.

        The Cab panel is the one layout the top-most/left-most heuristic can't
        read: it holds several identical cab columns plus a block-output column.
        Every other block keeps the geometric heuristic unchanged."""
        return self._selected_block_label().strip().lower().startswith("cab")

    # ── Chain summary (read from the grid, instant) ────────────────────────

    @script(
        description="Axe-Edit: Speak the current preset's effect chain "
                    "(estimated order)",
        gesture="kb:NVDA+shift+o",
    )
    def script_speakChain(self, gesture):
        """Speak the placed blocks in estimated signal order.

        Built entirely from the grid cells already in the accessibility tree, so
        it is instant. Cells are read column by column (left to right), and top
        to bottom within a column, which follows the signal flow -- but column
        order alone cannot see diagonal or parallel cabling, so the order is
        spoken as an ESTIMATE. Empty cells and shunts are skipped.
        """
        self.ensure_grid_index()
        if not self._grid_index:
            speech.cancelSpeech()
            ui.message("No effect grid found")
            return
        entries = []
        for col in range(self.grid_cols):
            for row in range(self.grid_rows):
                cell = self.grid_cell(row, col)
                if cell is None:
                    continue
                name = cell.name or ""
                if not _is_placed_block(_cable_block_label(name)):
                    continue
                summary = _block_summary(name)
                if summary:
                    entries.append(summary)
        speech.cancelSpeech()
        if not entries:
            ui.message("No blocks placed")
            return
        ui.message(
            "Estimated chain, left to right: {0}. Order is approximate; "
            "cabling is not read.".format(", ".join(entries))
        )

    @script(
        description="Axe-Edit: Summarise the selected block's parameters",
        gesture="kb:NVDA+shift+b",
    )
    def script_speakFocusedBlock(self, gesture):
        """Summarise the parameters currently shown for the selected block.

        Speaks each visible parameter and its value, in screen order, so you can
        hear a block's settings at a glance instead of arrowing one at a time.
        It reads whichever parameter PAGE is showing, so pair it with the page
        commands (NVDA+Shift+PageDown/PageUp) to summarise a specific page. Falls
        back to the focused cell's block + bypass state if no parameters are up.
        """
        root = api.getForegroundObject()
        params = []
        if root is not None:
            self._collect_params(root, params, depth=0)
        speech.cancelSpeech()
        if not params:
            obj = api.getFocusObject()
            summary = _block_summary((obj.name if obj is not None else "") or "")
            ui.message(summary or "No parameters to summarise")
            return
        params.sort(key=self._param_sort_key)
        parts = []
        for p in params:
            txt = _clean_value_name(p.name or "")
            if txt:
                parts.append(txt)
        block = self._selected_block_label()
        if parts and block:
            ui.message("{0}: {1}".format(block, ", ".join(parts)))
        elif parts:
            ui.message(", ".join(parts))
        else:
            ui.message(block or "No parameters to summarise")

    # ── Diagnostics ───────────────────────────────────────────────────────

    # Plenty for any Fractal editor (Axe-Edit III reports ~409) while still
    # bounding a runaway tree.
    _DUMP_MAX = 8000

    @script(
        description="Axe-Edit: Save a diagnostic dump of this window to the Desktop",
        gesture="kb:NVDA+shift+d",
    )
    def script_dumpTree(self, gesture):
        """Write this window's whole accessibility tree to a JSON file.

        This is how support for another Fractal editor gets confirmed without
        the developer owning the hardware: open the editor, press the key once,
        and send back the file that lands on the Desktop.
        """
        root = api.getForegroundObject()
        if root is None:
            ui.message("No window in the foreground")
            return

        ui.message("Collecting controls, one moment")
        records = []
        try:
            self._dump_object(root, records, depth=0)
        except Exception as e:
            ui.message("Dump failed: {0}".format(e))
            return

        self.ensure_grid_index()
        payload = {
            "addonVersion": _ADDON_VERSION,
            "appName": self.appName,
            "windowTitle": getattr(root, "name", "") or "",
            "gridCellsFound": len(self._grid_index or {}),
            "gridRows": self.grid_rows,
            "gridCols": self.grid_cols,
            "controlCount": len(records),
            "truncated": len(records) >= self._DUMP_MAX,
            "controls": records,
        }

        target_dir = os.path.join(os.path.expanduser("~"), "Desktop")
        if not os.path.isdir(target_dir):
            target_dir = os.path.expanduser("~")
        filename = "fractal-edit-dump-{0}.json".format(
            re.sub(r"[^A-Za-z0-9._-]+", "-", self.appName or "unknown")
        )
        path = os.path.join(target_dir, filename)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=1, ensure_ascii=False)
        except Exception as e:
            ui.message("Could not save the dump: {0}".format(e))
            return

        speech.cancelSpeech()
        ui.message(
            "Saved {0} controls, {1} grid cells. File is on your Desktop, "
            "named {2}".format(len(records), payload["gridCellsFound"], filename)
        )

    def _dump_object(self, obj, out, depth):
        """Append obj and its descendants to out, defensively.

        Anything that raises on a single property is recorded as null rather
        than aborting the whole dump -- a partial dump is still useful.
        """
        if depth > 30 or len(out) >= self._DUMP_MAX:
            return

        record = {"depth": depth}
        for key in ("name", "value", "description", "windowClassName"):
            try:
                record[key] = getattr(obj, key, None)
            except Exception:
                record[key] = None
        try:
            record["role"] = str(obj.role)
        except Exception:
            record["role"] = None
        try:
            record["states"] = sorted(str(s) for s in obj.states)
        except Exception:
            record["states"] = []
        try:
            loc = obj.location
            record["location"] = (
                [loc.left, loc.top, loc.width, loc.height] if loc else None
            )
        except Exception:
            record["location"] = None
        out.append(record)

        try:
            child = obj.firstChild
        except Exception:
            return
        while child is not None and len(out) < self._DUMP_MAX:
            self._dump_object(child, out, depth + 1)
            try:
                child = child.next
            except Exception:
                break

    # ── Helpers ───────────────────────────────────────────────────────────

    def _focus_section(self, keywords, label=""):
        """
        Walk the accessibility tree of the foreground window and focus the
        first interactive control whose name contains one of the keywords.
        Skips pure containers so we land on something focusable.
        """
        root = api.getForegroundObject()
        if not root:
            ui.message("Axe-Edit is not in the foreground")
            return

        found = self._search(root, keywords, depth=0)
        if found:
            found.setFocus()
            if label:
                ui.message(label)
        else:
            ui.message("Section not found: {0}".format(label or keywords[0]))

    _CONTAINER_ROLES = frozenset({
        controlTypes.Role.WINDOW,
        controlTypes.Role.DIALOG,
        controlTypes.Role.PANE,
        controlTypes.Role.GROUPING,
        controlTypes.Role.APPLICATION,
    })

    def _search(self, obj, keywords, depth):
        if depth > 25:
            return None

        name = (obj.name or "").lower()
        if any(kw in name for kw in keywords):
            if obj.role not in self._CONTAINER_ROLES:
                return obj

        child = obj.firstChild
        while child:
            result = self._search(child, keywords, depth + 1)
            if result:
                return result
            child = child.next

        return None
