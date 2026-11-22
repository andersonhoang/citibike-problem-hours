"""
test_env.py
Task: "Python environment: pinned versions, installs on all three laptops" (Marcuz).
Run on each team member's laptop after `pip install -r requirements.txt`:
    python test_env.py
"""
import importlib
import sys
from pathlib import Path

REQUIRED = [
    "polars",
    "pandas",
    "numpy",
    "scipy",
    "sklearn",
    "matplotlib",
    "seaborn",
    "pyarrow",
    "requests",
    "pptx",
    "docx",
    "ipykernel",
]


def main():
    print(f"Python: {sys.version.split()[0]}")
    assert sys.version_info >= (3, 10), "Need Python 3.10 or newer"

    missing = []
    for name in REQUIRED:
        try:
            mod = importlib.import_module(name)
            ver = getattr(mod, "__version__", "installed")
            print(f"  OK  {name:12s} {ver}")
        except ImportError:
            missing.append(name)
            print(f"  FAIL {name}")
    assert not missing, f"Missing packages: {missing}"

    # Known-answer check: verify the aggregated table exists and has 403,200 rows.
    csv_path = Path(__file__).resolve().parent / "data_processed" / "station_hour.csv"
    assert csv_path.exists(), f"Missing {csv_path}"
    import polars as pl
    n_rows = pl.scan_csv(csv_path, schema_overrides={"station_id": pl.Utf8}).select(pl.len()).collect().item()
    assert n_rows == 403_200, f"Expected 403,200 rows, got {n_rows:,}"
    print(f"\nEnvironment check PASSED ({len(REQUIRED)} packages OK; station_hour.csv = {n_rows:,} rows).")


if __name__ == "__main__":
    main()
