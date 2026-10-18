# Run every check the CI would: backend tests + lint, frontend lint + build.
# Usage (from the repo root):  powershell -ExecutionPolicy Bypass -File scripts\check.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Step($name, $dir, $cmd) {
    Write-Host "==> $name" -ForegroundColor Cyan
    Push-Location "$root\$dir"
    try {
        Invoke-Expression $cmd
        if ($LASTEXITCODE -ne 0) { throw "$name failed" }
    } finally { Pop-Location }
}

Step "backend: pytest"      "backend"  "uv run pytest"
Step "backend: ruff check"  "backend"  "uv run ruff check ."
Step "backend: ruff format" "backend"  "uv run ruff format --check ."
Step "frontend: lint"       "frontend" "npm run lint"
Step "frontend: build"      "frontend" "npm run build"
Write-Host "All checks passed." -ForegroundColor Green
