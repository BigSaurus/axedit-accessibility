# Axe-Edit III Accessibility - NVDA app module
# Copyright (C) 2026 Big Saurus
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2, as published by the
# Free Software Foundation. This program is distributed WITHOUT ANY WARRANTY.
# See the LICENSE file (GNU GPL v2) distributed with this add-on for details.

"""
appModules/axe-edit iii.py

NVDA app module for Axe-Edit III (Fractal Audio).

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

Navigation / commands
----------------------
  Arrows (on a grid cell)  -- move between grid cells, 2D (toggle: NVDA+Shift+G)
  Home / End (on a grid cell) -- jump to the first / last column of the row
  Enter (on a grid cell)   -- select that block so its parameters load
  NVDA+Ctrl+0..9   -- jump straight to row 2, that column (e.g. +5 = the amp)
  NVDA+Shift+A   -- jump to the Amp block
  NVDA+Shift+E   -- jump to the Effects grid (row 0, column 0)
  NVDA+Shift+F   -- jump to the first parameter of the current block
  NVDA+Shift+P   -- jump to the Preset selector
  NVDA+Shift+S   -- jump to the Scene selector
  NVDA+Shift+I   -- announce full info about the focused control
  NVDA+Shift+J   -- toggle jack/cable noise suppression (default: on)
  NVDA+Shift+G   -- toggle 2D arrow-key grid navigation (default: on)
  NVDA+Shift+Space -- activate the focused control (for mouse-only items)
"""

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
_GRID_ROWS = 6      # rows 0..5
_GRID_COLS = 14     # cols 0..13

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


def _invoke_control(obj):
    """Activate a control: standard action first, synthesised click as fallback.

    Returns True if some activation was attempted.
    """
    if obj is None:
        return False
    try:
        obj.doAction(0)
        return True
    except Exception:
        pass
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
        if not (0 <= nr < _GRID_ROWS and 0 <= nc < _GRID_COLS):
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
        if self._grid_nav_enabled() and rc is not None \
                and self._goto(rc[0], _GRID_COLS - 1):
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
    # suppress the verbose focus announcement during our own grid moves.
    _grid_index = None
    _last_grid_prog_move = 0.0

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

        # During our own grid navigation we announce concisely ourselves, so
        # suppress the verbose focus event that would otherwise double-speak.
        if _GRID_RE.match(name) and (time.time() - self._last_grid_prog_move) < 0.4:
            return

        # Skip unlabelled structural elements that carry no information.
        if obj.role in (
            controlTypes.Role.SEPARATOR,
            controlTypes.Role.BORDER,
            controlTypes.Role.UNKNOWN,
        ) and not obj.name:
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
