#!/usr/bin/env python3
"""Validate an NVDA add-on manifest the exact way NVDA does at install time.

NVDA's "missing a file or invalid file format" dialog is generic wording for
*any* failure building the AddonBundle -- most often a manifest that fails
validation, not a corrupt zip. This reproduces NVDA's install-time check so a
broken manifest is caught on this machine instead of on a user's device.

Usage:
    python validate_manifest.py [path]

    path may be a .nvda-addon package (manifest is read from inside the zip),
    a manifest.ini file, or a folder containing one. With no argument, the
    newest *.nvda-addon next to this script is checked.

Exit code 0 = NVDA will accept the manifest; 1 = it will be rejected.

Requires: pip install configobj
"""
import io
import os
import sys
import glob
import zipfile

try:
    from configobj import ConfigObj
    from validate import Validator, ValidateError
except ImportError:
    sys.stderr.write(
        "configobj is not installed. Run:  python -m pip install configobj\n"
    )
    sys.exit(2)

# NVDA's manifest configspec: the four required fields have no default;
# everything else is optional. Mirrors addonHandler.AddonManifest.
_SPEC = """
name = string()
summary = string()
version = string()
author = string()
description = string(default=None)
url = string(default=None)
docFileName = string(default=None)
minimumNVDAVersion = apiVersion(default="0.0.0")
lastTestedNVDAVersion = apiVersion(default="0.0.0")
updateChannel = string(default=None)
""".splitlines()

_REQUIRED = ("name", "summary", "version", "author")


def _api_version(value):
    """Mirror NVDA's year[.major[.minor]] version parsing."""
    parts = str(value).split(".")
    if not (1 <= len(parts) <= 3) or not all(p.isdigit() for p in parts):
        raise ValidateError("bad version string: %r" % (value,))
    return value


def _read_manifest_bytes(path):
    """Return (manifest_bytes, source_label) for a package / manifest / folder."""
    if os.path.isdir(path):
        path = os.path.join(path, "manifest.ini")
    if path.lower().endswith(".nvda-addon") or zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            return z.read("manifest.ini"), "%s (manifest.ini inside zip)" % os.path.basename(path)
    with open(path, "rb") as f:
        return f.read(), path


def validate(path):
    raw, label = _read_manifest_bytes(path)
    cfg = ConfigObj(io.BytesIO(raw), configspec=_SPEC, encoding="utf-8")
    result = cfg.validate(Validator({"apiVersion": _api_version}), preserve_errors=True)

    print("Validating: %s" % label)

    # configobj returns True when everything passed; otherwise a dict of results.
    if result is True:
        for k in _REQUIRED:
            print("  %-10s = %r" % (k, cfg.get(k)))
        print("\nVALID -- NVDA will accept this package.")
        return True

    print("\nManifest FAILED validation (NVDA would reject it):")
    for key, ok in result.items():
        if ok is not True:
            reason = "missing (required, no value read)" if ok is False else ok
            print("  %-22s FAIL -> %s" % (key, reason))
    # A False on a required field almost always means the fields are not at the
    # root level (e.g. wrapped in an [add-on] section) or a comma-containing
    # value was parsed as a list. See reference_nvda_addon_manifest_format.
    print("\nCommon causes: an [add-on] section wrapper (fields must be at root),")
    print("or an unquoted comma-containing value (quote it, e.g. description).")
    return False


def main(argv):
    if len(argv) > 1:
        target = argv[1]
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        pkgs = sorted(glob.glob(os.path.join(here, "*.nvda-addon")), key=os.path.getmtime)
        if not pkgs:
            sys.stderr.write("No *.nvda-addon found next to this script; pass a path.\n")
            return 2
        target = pkgs[-1]
    return 0 if validate(target) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
