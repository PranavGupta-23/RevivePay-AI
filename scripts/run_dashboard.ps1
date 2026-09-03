if (-not (Test-Path "env:VIRTUAL_ENV")) {
    if (Test-Path ".venv\Scripts\Activate.ps1") {
        .\.venv\Scripts\Activate.ps1
    } else {
        Write-Host "Virtual environment not found. Run .\scripts\setup_windows.ps1 first." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Starting Streamlit dashboard at http://localhost:8501 ..." -ForegroundColor Cyan
streamlit run dashboard/app.py
