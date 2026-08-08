# install_dev.ps1
# Copies the app modules to NVDA's scratchpad for development testing.
# No packaging or add-on installation required.
# After running this, press NVDA+Ctrl+F3 in NVDA to reload plugins.

$scratchpad = Join-Path $env:APPDATA "nvda\scratchpad\appModules"
$appModules = Join-Path $PSScriptRoot "axedit-accessibility\appModules"

# The behaviour lives in fractalEditCore.py; each editor's shim imports it, so
# the core MUST be copied alongside the shims or the import fails.
$sources = @(
    "fractalEditCore.py",
    "axe-edit iii.py",
    "fm9-edit.py",
    "fm3-edit.py"
)

if (-not (Test-Path $scratchpad)) {
    New-Item -ItemType Directory -Path $scratchpad -Force | Out-Null
    Write-Host "Created: $scratchpad"
}

foreach ($name in $sources) {
    $source = Join-Path $appModules $name
    if (Test-Path $source) {
        Copy-Item -Path $source -Destination $scratchpad -Force
        Write-Host "Installed: $scratchpad\$name"
    }
    else {
        Write-Host "Skipped (not found): $name"
    }
}

Write-Host ""
Write-Host "Press NVDA+Ctrl+F3 in NVDA to reload plugins, then switch to Axe-Edit III."
