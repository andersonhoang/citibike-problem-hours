"""
analysis/00_check_env.py
Task (Marcuz, W1): "Python environment: pinned versions, installs on all three laptops".

Run on every team member's laptop after creating the virtual environment and installing requirements.txt:
    python analysis/00_check_env.py

Checks that Python and every package in the project stack import cleanly, prints their exact versions
so all three laptops can compare outputs, and runs a quick read check on data_processed/station_hour.csv.
"""
import importlib
import sys
from pathlib import Path

EXPECTED_PYTHON = "3.14.4"
PACKAGES = [
    ("polars", "polars"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("scipy", "scipy"),
    ("scikit-learn", "sklearn"),
    ("matplotlib", "matplotlib"),
    ("seaborn", "seaborn"),
    ("pyarrow", "pyarrow"),
    ("requests", "requests"),
    ("ipykernel", "ipykernel"),
    ("nbconvert", "nbconvert"),
]


def main() -> None:
    """Print Python and package versions, fail if any required package is missing."""
    py_ver = sys.version.split()[0]
    print(f"Python: {py_ver} (team target: {EXPECTED_PYTHON})")
    if py_ver != EXPECTED_PYTHON:
        print(f"WARNING: expected Python {EXPECTED_PYTHON}, got {py_ver}")

    missing = []
    for dist_name, import_name in PACKAGES:
        try:
            mod = importlib.import_module(import_name)
            ver = getattr(mod, "__version__", "installed")
            print(f"  OK   {dist_name:14s} {ver}")
        except ImportError:
            missing.append(dist_name)
            print(f"  FAIL {dist_name:14s} NOT INSTALLED")

    assert not missing, f"Missing packages: {', '.join(missing)}"

    # Quick known-answer check on the shared station-hour table (300 stations x 24 hours x 56 days).
    table_path = Path(__file__).resolve().parents[1] / "data_processed" / "station_hour.csv"
    assert table_path.exists(), f"Missing {table_path}"
    import polars as pl
    n_rows = pl.scan_csv(table_path, schema_overrides={"station_id": pl.Utf8}).select(pl.len()).collect().item()
    assert n_rows == 403_200, f"Expected 403,200 rows, got {n_rows:,}"
    print(f"\nEnvironment check PASSED: {len(PACKAGES)}/{len(PACKAGES)} packages OK; station_hour.csv = {n_rows:,} rows.")


if __name__ == "__main__":
    main()
