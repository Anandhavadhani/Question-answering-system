<#
Simple PowerShell helper to run the FastAPI app with PYTHONPATH set so
`uvicorn app.main:app` works regardless of current working directory.
#>
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# Ensure PYTHONPATH contains the backend folder so `import app` resolves
$Env:PYTHONPATH = $scriptDir

Write-Host "Starting backend from: $scriptDir" -ForegroundColor Green
python -m uvicorn app.main:app --reload --port 8000 --log-level debug
