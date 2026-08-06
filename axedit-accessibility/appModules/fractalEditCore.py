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

Navigation / commands
----------------------
  Arrows (on a grid cell)  -- move between grid cells, 2D (toggle: NVDA+Shift+G)
  Home / End (on a grid cell) -- jump to the first / last column of the row
  Enter (on a grid cell)   -- select that block so its parameters load
  Space (on a grid cell)   -- bypass / enable the block, keeping focus
  Enter (on an on/off button) -- toggle it (Space is reserved for block bypass)
  NVDA+Ctrl+0..9   -- jump straight to row 2, that column (e.g. +5 = the amp)
  NVDA+Shift+A   -- jump to the Amp block
  NVDA+Shift+E   -- jump to the Effects grid (row 0, column 0)
  NVDA+Shift+F   -- jump to the first parameter of the current block
  NVDA+Shift+P   -- jump to the Preset selector
  NVDA+Shift+S   -- jump to the Scene selector
  Alt+P/B/T/S/H  -- open the Preset / Block / Tools / Settings / Help menu
  NVDA+Shift+I   -- announce full info about the focused control
  NVDA+Shift+J   -- toggle jack/cable noise suppression (default: on)
  NVDA+Shift+G   -- toggle 2D arrow-key grid navigation (default: on)
  NVDA+Shift+Space -- activate the focused control (for mouse-only items)
  NVDA+Shift+D   -- save a diagnostic dump of the window to the Desktop
"""

_ADDON_VERSION = "0.8.0"

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


# The routing-graphic RadioButtons that carry no useful identity.
_NOISE_NAMES = frozenset({"jackcomponent", "cablecomponent"})

# Slider names trail a modifier hint we don't want on every keystroke.
_MODIFIER_TRAILER_RE = re.compile(r",\s*Modifier (Disabled|Enabled)\s*$", re.IGNORECASE)


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

        role = obj.role
        if role == controlTypes.Role.COMBOBOX:
            clsList.insert(0, _AxeEditComboBox)
        elif role == controlTypes.Role.SLIDER:
            clsList.insert(0, _AxeEditSlider)

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
        # The "first" parameter is the visually top-most, then left-most one
        # (matches where a sighted user's cursor lands: the first knob).
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
