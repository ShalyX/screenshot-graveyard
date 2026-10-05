$ErrorActionPreference = "Stop"
if (-not $env:HF_TOKEN) {
  Write-Host "Set HF_TOKEN before starting:" -ForegroundColor Yellow
  Write-Host '$env:HF_TOKEN="hf_..."'
  exit 1
}
python -m pip install --disable-pip-version-check -r requirements.txt
python server.py
