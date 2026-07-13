# install_dev.ps1
# Copies the app module to NVDA's scratchpad for development testing.
# No packaging or add-on installation required.
# After running this, press NVDA+Ctrl+F3 in NVDA to reload plugins.

$scratchpad = Join-Path $env:APPDATA "nvda\scratchpad\appModules"
$source     = Join-Path $PSScriptRoot "axedit-accessibility\appModules\axe-edit iii.py"

if (-not (Test-Path $scratchpad)) {
    New-Item -ItemType Directory -Path $scratchpad -Force | Out-Null
    Write-Host "Created: $scratchpad"
}

Copy-Item -Path $source -Destination $scratchpad -Force
Write-Host "Installed to: $scratchpad\axe-edit iii.py"
Write-Host ""
Write-Host "Press NVDA+Ctrl+F3 in NVDA to reload plugins, then switch to Axe-Edit III."
