# Releasing a new version of the add-on

Two things must happen on every release, and the build now **enforces both** —
`build_addon.ps1` refuses to produce a package otherwise:

1. **Users are told what's new.** The build fails unless `changelog.md` has a
   `## <version>` section matching `manifest.ini`.
2. **No personal data ships.** After building, `scrub_pii.py` scans the package
   *and* the public docs (README.md, LICENSE, changelog.md) for the real name,
   personal email, local user paths, machine names, and stray dump/media files.
   Any hit deletes the build.

## Steps

1. **Write the changelog first.** Add a `## <new version>` section at the top of
   [axedit-accessibility/changelog.md](axedit-accessibility/changelog.md),
   describing each new feature in plain, user-facing language (see existing
   entries for the voice). This is the source of truth the other surfaces copy.
2. **Bump the version** in
   [axedit-accessibility/manifest.ini](axedit-accessibility/manifest.ini).
3. **Update the public README's "Features" list and keyboard tables**
   ([README.md](README.md)) so a new user reading it sees the new capability —
   the changelog says *what changed*, the Features list says *what it does now*.
4. **Build:** `./build_addon.ps1`. It runs, in order:
   - changelog gate (must have this version's section),
   - zip + manifest validation,
   - **PII scrub** (fails and deletes the build on any finding).
   A clean run ends with `scrub_pii: OK`.
5. **Publish the GitHub release.** Create the release/tag for the version and
   **paste this version's changelog section into the release notes** — that is
   how users on the Releases page see the new features called out specifically.

## If the PII scrub flags something

- **A real leak** (name, email, `C:\Users\...` path, machine name, a `.json`
  dump left in `appModules/`): remove it from the file, rebuild.
- **A legitimate value** the scanner shouldn't block (e.g. a real support email
  you *want* published): add it to the allowlist near the top of
  [scrub_pii.py](scrub_pii.py) (`EMAIL_ALLOW`), or adjust `DENY`. The denylist
  itself is private to the repo and never ships.
- To add a new never-publish token (e.g. a surname), add a line to the `DENY`
  list in `scrub_pii.py`.
