# build_addon.ps1
# Packages the add-on as a .nvda-addon file for distribution or installation.
# Run from the tools/nvda-addon/ directory.
#
# Produces a spec-compliant zip: entry paths use FORWARD slashes (NVDA's
# installer uses Python zipfile, which expects '/'), and dev-only files
# (__pycache__, *.pyc, the docs/ developer notes) are excluded.

$addonDir   = Join-Path $PSScriptRoot "axedit-accessibility"
$outputDir  = $PSScriptRoot

# Read the version straight from the manifest so this never drifts.
$manifest = Join-Path $addonDir "manifest.ini"
$version  = (Select-String -Path $manifest -Pattern '^\s*version\s*=\s*(.+)$').Matches[0].Groups[1].Value.Trim()
$outputFile = Join-Path $outputDir "axedit-accessibility-$version.nvda-addon"

if (-not (Test-Path $addonDir)) {
    Write-Error "Add-on directory not found: $addonDir"
    exit 1
}

if (Test-Path $outputFile) {
    Remove-Item $outputFile -Force
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

# Files to leave out of the shipped package.
$excludeDirs = @('__pycache__', 'docs')          # docs/ = developer notes; doc/ = user help (kept)
$excludeExt  = @('.pyc')

$zip = [System.IO.Compression.ZipFile]::Open($outputFile, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    $base = (Resolve-Path $addonDir).Path
    Get-ChildItem -Path $addonDir -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($base.Length + 1)
        $parts = $rel -split '[\\/]'
        if ($parts | Where-Object { $excludeDirs -contains $_ }) { return }
        if ($excludeExt -contains $_.Extension.ToLower()) { return }
        $entryName = ($parts -join '/')   # ZIP spec: forward slashes
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $zip, $_.FullName, $entryName,
            [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
}
finally {
    $zip.Dispose()
}

Write-Host "Built: $outputFile (version $version)"

# Validate the packaged manifest exactly the way NVDA does at install time, so a
# broken manifest is caught here rather than on a user's device. A manifest error
# surfaces to users as the misleading "missing a file or invalid file format".
$validator = Join-Path $PSScriptRoot "validate_manifest.py"
$python = (Get-Command python -ErrorAction SilentlyContinue)
if ($python -and (Test-Path $validator)) {
    Write-Host ""
    & $python.Source $validator $outputFile
    if ($LASTEXITCODE -eq 2) {
        Write-Warning "Manifest not validated (configobj missing). Run: python -m pip install configobj"
    }
    elseif ($LASTEXITCODE -ne 0) {
        Remove-Item $outputFile -Force
        Write-Error "Manifest validation FAILED - NVDA would reject this package. Removed the bad build. Fix manifest.ini and rebuild."
        exit 1
    }
}
else {
    Write-Warning "Skipped manifest validation (python not found). Install Python + 'pip install configobj' to enable it."
}

Write-Host ""
Write-Host "To install: open the .nvda-addon file while NVDA is running,"
Write-Host "or drag and drop it onto the NVDA system tray icon."
