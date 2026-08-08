#!/usr/bin/env python3
"""
scrub_pii.py -- pre-release PII / private-data scrub for the NVDA add-on.

Run by build_addon.ps1 after the package is built. Scans TWO surfaces that
reach the public:

  1. The shipped .nvda-addon (a zip) -- every text entry's contents, plus a
     check that no unexpected file types slipped in (a stray diagnostic dump
     would carry the user's own preset names).
  2. The public repo docs that go up to GitHub alongside releases:
     README.md, LICENSE, and the shipped changelog.md.

Exit codes (build_addon.ps1 treats non-zero as FAIL and deletes the build):
  0  clean
  1  one or more PII / leak findings
  2  could not run (bad arguments, missing package)

Public-alias rule: everything public says "Big Saurus" only -- never the real
name, the personal email, local user paths, or machine names.
"""

import os
import re
import sys
import zipfile

# --- What must never appear on anything public -------------------------------
# GENERIC, non-personal patterns only -- this file is itself public. It must
# NOT contain the real name, personal email, or machine name; those would leak
# the very data it guards. Personal literals live in a gitignored side file
# (see PII_TOKENS_FILE below) that never ships.
#
# Each entry: (compiled regex, human label). Matching is case-insensitive.
DENY = [
    (re.compile(r"[A-Za-z]:\\Users\\[^\\\"'\s]+", re.I), "absolute Windows user path (C:\\Users\\...)"),
    (re.compile(r"/Users/[^/\"'\s]+", re.I),          "absolute macOS/Unix user path (/Users/...)"),
    # Any e-mail address at all, unless explicitly allowed below. The add-on has
    # no reason to embed a contact address; flag them so none leaks by accident.
    # (This alone catches the personal gmail without naming it here.)
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),     "e-mail address"),
]

# E-mail addresses that are legitimately allowed to appear (none today).
EMAIL_ALLOW = set()

# Personal never-publish tokens (real name, machine names, a surname, ...) are
# read from this gitignored file so they stay out of this public scanner. One
# entry per line: "regex<TAB>label", or just a literal string (matched
# case-insensitively, whole-word where it makes sense). Blank lines and lines
# starting with '#' are ignored. If the file is absent, a warning is printed and
# only the generic patterns above run.
PII_TOKENS_FILE = "pii_tokens.local"


def load_local_tokens(script_dir):
    path = os.path.join(script_dir, PII_TOKENS_FILE)
    if not os.path.isfile(path):
        print(f"scrub_pii: NOTE - {PII_TOKENS_FILE} not found; scanning with generic "
              "patterns only (real name / machine names won't be checked).", file=sys.stderr)
        return
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if "\t" in line:
                pat, label = line.split("\t", 1)
            else:
                # Bare literal -> whole-word, case-insensitive.
                pat, label = r"\b" + re.escape(line.strip()) + r"\b", f"private token ({line.strip()})"
            DENY.append((re.compile(pat, re.I), label.strip()))

# Dump / media / archive file types that must never be inside the package. This
# is how a diagnostic dump (.json, full of the user's own preset names), a
# recorded .wav, a screenshot, or a stray archive would sneak in. Legitimate
# text docs (.md, .html, .txt) are allowed through and instead get PII-scanned.
SUSPICIOUS_PACKAGE_EXT = {
    ".json", ".log", ".csv", ".syx", ".bin", ".dat",
    ".wav", ".mp3", ".flac",
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff",
    ".zip", ".7z", ".rar", ".nvda-addon",
}

# Extensions we bother scanning the *text* of.
TEXT_EXT = {".py", ".ini", ".html", ".htm", ".md", ".txt", ".json"}


def _finding(findings, where, label, snippet):
    findings.append((where, label, snippet.strip()[:120]))


def _scan_text(text, where, findings):
    for line_no, line in enumerate(text.splitlines(), 1):
        for rx, label in DENY:
            for m in rx.finditer(line):
                if label == "e-mail address" and m.group(0).lower() in EMAIL_ALLOW:
                    continue
                _finding(findings, f"{where}:{line_no}", label, line)


def scan_package(addon_path, findings):
    if not zipfile.is_zipfile(addon_path):
        print(f"scrub_pii: not a zip: {addon_path}", file=sys.stderr)
        return 2
    with zipfile.ZipFile(addon_path) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            name = info.filename
            ext = os.path.splitext(name)[1].lower()
            if ext in SUSPICIOUS_PACKAGE_EXT:
                _finding(findings, f"[package] {name}", "dump/media/archive file in package (possible private-data leak)", name)
            if ext in TEXT_EXT:
                try:
                    text = z.read(name).decode("utf-8", errors="replace")
                except Exception as e:  # noqa: BLE001
                    print(f"scrub_pii: could not read {name}: {e}", file=sys.stderr)
                    continue
                _scan_text(text, f"[package] {name}", findings)
    return 0


def scan_public_docs(script_dir, findings):
    # Docs that ship to GitHub next to the release.
    candidates = [
        os.path.join(script_dir, "README.md"),
        os.path.join(script_dir, "LICENSE"),
        os.path.join(script_dir, "axedit-accessibility", "changelog.md"),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            _scan_text(f.read(), f"[repo] {os.path.relpath(path, script_dir)}", findings)


def main(argv):
    if len(argv) != 2:
        print("usage: scrub_pii.py <path-to.nvda-addon>", file=sys.stderr)
        return 2
    addon_path = argv[1]
    if not os.path.isfile(addon_path):
        print(f"scrub_pii: package not found: {addon_path}", file=sys.stderr)
        return 2

    script_dir = os.path.dirname(os.path.abspath(__file__))
    load_local_tokens(script_dir)
    findings = []

    rc = scan_package(addon_path, findings)
    if rc == 2:
        return 2
    scan_public_docs(script_dir, findings)

    if findings:
        print("scrub_pii: FAIL -- private data found in files that reach the public:\n")
        for where, label, snippet in findings:
            print(f"  {where}")
            print(f"    -> {label}")
            print(f"       {snippet}\n")
        print(f"{len(findings)} finding(s). Remove them (or add a legitimate one to the")
        print("allowlist in scrub_pii.py) and rebuild.")
        return 1

    print("scrub_pii: OK -- no personal data found in the package or public docs.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
