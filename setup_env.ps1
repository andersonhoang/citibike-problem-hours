# One-command environment setup for Windows (PowerShell)
# Usage: .\setup_env.ps1
$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) {
    python -m venv .venv
}
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python test_env.py
