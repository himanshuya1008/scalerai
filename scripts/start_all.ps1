$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$apiPath = Join-Path $repoRoot "src/api.py"
$frontendPath = Join-Path $repoRoot "frontend"
$venvPython = Join-Path $repoRoot ".venv/Scripts/python.exe"

if (-not (Test-Path $venvPython)) {
  throw ".venv Python not found at $venvPython"
}

if (-not (Test-Path $apiPath)) {
  throw "API file not found at $apiPath"
}

if (-not (Test-Path $frontendPath)) {
  throw "Frontend folder not found at $frontendPath"
}

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$repoRoot'; & '$venvPython' '$apiPath'"
)

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$frontendPath'; npm start"
)

Write-Host "Backend and frontend launch commands started in separate windows."
