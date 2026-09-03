if (-not (Test-Path "env:VIRTUAL_ENV")) {
    if (Test-Path ".venv\Scripts\Activate.ps1") {
        .\.venv\Scripts\Activate.ps1
    } else {
        Write-Host "Virtual environment not found. Run .\scripts\setup_windows.ps1 first." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Starting FastAPI backend at http://localhost:8000 (docs at /docs) ..." -ForegroundColor Cyan
uvicorn backend.main:app --reload --port 8000
