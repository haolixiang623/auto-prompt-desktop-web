param(
    [string]$RuntimeDir = "src-tauri/resources/python-runtime",
    [string[]]$Packages = @("openai", "openpyxl", "pymupdf"),
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Resolve-PythonCommand {
    param([string]$PreferredPythonExe)

    $candidates = New-Object System.Collections.Generic.List[object]
    if ($PreferredPythonExe) {
        $candidates.Add([pscustomobject]@{ Exe = $PreferredPythonExe; Args = @() })
    }

    $candidates.Add([pscustomobject]@{ Exe = "python"; Args = @() })
    $candidates.Add([pscustomobject]@{ Exe = "py"; Args = @("-3.11") })
    $candidates.Add([pscustomobject]@{ Exe = "py"; Args = @("-3.12") })

    $localAppData = [Environment]::GetFolderPath("LocalApplicationData")
    $candidates.Add([pscustomobject]@{ Exe = (Join-Path $localAppData "Programs\Python\Python311\python.exe"); Args = @() })
    $candidates.Add([pscustomobject]@{ Exe = (Join-Path $localAppData "Programs\Python\Python312\python.exe"); Args = @() })

    foreach ($candidate in $candidates) {
        $exists = $false
        if (Test-Path $candidate.Exe) {
            $exists = $true
        } elseif (Get-Command $candidate.Exe -ErrorAction SilentlyContinue) {
            $exists = $true
        }

        if (-not $exists) {
            continue
        }

        try {
            $probe = & $candidate.Exe @($candidate.Args + @("-c", "import sys; print(sys.executable)")) 2>$null
            if ($LASTEXITCODE -eq 0 -and $probe) {
                return @{ Exe = $candidate.Exe; Args = $candidate.Args }
            }
        } catch {
            continue
        }
    }

    throw "No usable Python interpreter was found. Install Python 3.11+ or pass -PythonExe explicitly."
}

function Invoke-Python {
    param(
        [hashtable]$PythonCommand,
        [string[]]$PythonArgs
    )

    & $PythonCommand.Exe @($PythonCommand.Args + $PythonArgs)
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $($PythonCommand.Exe) $($PythonArgs -join ' ')"
    }
}

$pythonCmd = Resolve-PythonCommand -PreferredPythonExe $PythonExe
$json = Invoke-Python -PythonCommand $pythonCmd -PythonArgs @(
    "-c",
    "import json, sys; print(json.dumps({'executable': sys.executable, 'base_prefix': sys.base_prefix, 'version': sys.version}))"
)
$pythonInfo = $json | ConvertFrom-Json
if (-not $pythonInfo -or -not $pythonInfo.base_prefix) {
    throw "Unable to resolve Python base prefix."
}

$basePrefix = $pythonInfo.base_prefix
$runtimePath = Resolve-Path -LiteralPath . | ForEach-Object { Join-Path $_ $RuntimeDir }

Write-Host "Using Python executable: $($pythonInfo.executable)"
Write-Host "Using Python base prefix: $basePrefix"
Write-Host "Preparing runtime at: $runtimePath"

if (Test-Path $runtimePath) {
    Remove-Item -Recurse -Force $runtimePath
}
New-Item -ItemType Directory -Force -Path $runtimePath | Out-Null

$itemsToCopy = @(
    "python.exe",
    "pythonw.exe",
    "python3.dll",
    "python311.dll",
    "python312.dll",
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "Lib",
    "DLLs",
    "libs",
    "include",
    "LICENSE.txt"
)

foreach ($item in $itemsToCopy) {
    $source = Join-Path $basePrefix $item
    if (Test-Path $source) {
        Copy-Item -Path $source -Destination $runtimePath -Recurse -Force
    }
}

$runtimePyvenv = Join-Path $runtimePath "pyvenv.cfg"
if (Test-Path $runtimePyvenv) {
    Remove-Item -Force $runtimePyvenv
}

$runtimePython = Join-Path $runtimePath "python.exe"
if (-not (Test-Path $runtimePython)) {
    throw "Portable runtime build failed: python.exe was not copied."
}

$runtimeCommand = @{ Exe = $runtimePython; Args = @() }
Invoke-Python -PythonCommand $runtimeCommand -PythonArgs @("-m", "ensurepip", "--upgrade")
Invoke-Python -PythonCommand $runtimeCommand -PythonArgs @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Python -PythonCommand $runtimeCommand -PythonArgs (@("-m", "pip", "install") + $Packages)

$packageVersions = @{}
foreach ($package in $Packages) {
    $version = Invoke-Python -PythonCommand $runtimeCommand -PythonArgs @(
        "-c",
        "import importlib.metadata; print(importlib.metadata.version('$package'))"
    )
    $packageVersions[$package] = ($version | Out-String).Trim()
}

$manifest = [ordered]@{
    python_version = ($pythonInfo.version | Out-String).Trim()
    packages = $packageVersions
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 (Join-Path $runtimePath "runtime-manifest.json")

Write-Host "Offline Python runtime is ready."
