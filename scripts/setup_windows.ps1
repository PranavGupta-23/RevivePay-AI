Write-Host "== ARSA Windows Setup ==" -ForegroundColor Cyan

$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Python was not found on PATH. Install Python 3.11 from https://www.python.org/downloads/ and re-run this script." -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion"

if (-not (Test-Path "RevivePay_AI")) {
    Write-Host "Creating virtual environment (RevivePay_AI) ..."
    python -m venv RevivePay_AI
} else {
    Write-Host "Virtual environment RevivePay_AI already exists."
}

Write-Host "Activating virtual environment ..."
.\RevivePay_AI\Scripts\Activate.ps1

Write-Host "Installing dependencies from requirements.txt ..."
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example (edit it if you have an ANTHROPIC_API_KEY)."
}

Write-Host "Generating synthetic training data ..."
python ml/generate_synthetic_data.py

Write-Host "Training the recovery-probability model ..."
python ml/train_model.py

Write-Host ""
Write-Host "== Setup complete! ==" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. In one terminal: .\scripts\run_backend.ps1"
Write-Host "  2. In another terminal: .\scripts\run_dashboard.ps1"
Write-Host "  3. Open http://localhost:8501 in your browser"
