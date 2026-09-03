if (-not (Test-Path "env:VIRTUAL_ENV")) {
    if (Test-Path ".venv\Scripts\Activate.ps1") {
        .\.venv\Scripts\Activate.ps1
    } else {
        Write-Host "Virtual environment not found. Run .\scripts\setup_windows.ps1 first." -ForegroundColor Red
        exit 1
    }
}

Write-Host "== 1/4: Generating synthetic data ==" -ForegroundColor Cyan
python ml/generate_synthetic_data.py

Write-Host "== 2/4: Training model ==" -ForegroundColor Cyan
python ml/train_model.py

Write-Host "== 3/4: Running tests ==" -ForegroundColor Cyan
pytest tests/ -v

Write-Host "== 4/4: Running evaluation vs. baselines ==" -ForegroundColor Cyan
python evaluation/run_evaluation.py

Write-Host ""
Write-Host "Pipeline complete. Start the backend and dashboard with:" -ForegroundColor Green
Write-Host "  .\scripts\run_backend.ps1"
Write-Host "  .\scripts\run_dashboard.ps1"
