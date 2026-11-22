"""
check_code.py
42.510 Citi Bike project: automatic checks on the Python code and on what git would publish.

Each check is a rule from CODING_RULES.md or a mistake we already made.
Run from the SUTD folder:  python check_code.py
Exit code 0 = all passed; 1 = at least one check failed.
"""

# Step 1: import the tools.
import re                                   # pattern matching on lines of code
import subprocess                           # runs git
import sys                                  # sets the exit code
from pathlib import Path                    # file paths

# Step 2: settings. Every .py file in the repo is checked for syntax and Windows paths, except this one.
# The two polars rules (blank IDs, collect before get_column) apply only to the scripts in the root folder,
# because those are the ones that read the raw trips.
FOLDER = Path(__file__).resolve().parent
THIS_FILE = Path(__file__).name
SKIP_DIRS = {".venv", "venv", "__pycache__", "data_raw", ".git", "node_modules"}
ALL_FILES = sorted(
    p for p in FOLDER.rglob("*.py")
    if p.name != THIS_FILE and not (set(p.relative_to(FOLDER).parts) & SKIP_DIRS)
)
FILES = [p for p in ALL_FILES if p.parent == FOLDER]     # root scripts only
FAILED = []                                 # names of checks that failed

# What git may track. Aggregated outputs are allowed; raw trips and zips never.
ALLOWED_EXTENSIONS = {
    "data_processed/": {".csv", ".json", ".parquet"},
    "results/": {".csv", ".json", ".parquet", ".txt"},
}
MAX_TRACKED_MB = 50                         # raw monthly CSV parts are about 186 MB; GitHub refuses over 100 MB

# Patterns used by the checks.
WINDOWS_PATH = re.compile(r'(?<![rR])"[A-Za-z]:\\')                  # a Windows path with no r prefix
BLANK_FILTER = re.compile(r'has_real_id\(|is_blank\(|blank\(|strip_chars\(\) (!=|==) ""')


def report(name, problems):
    """Print PASS, or FAIL with the first problems found."""
    if problems:
        FAILED.append(name)
        print(f"FAIL: {name}")
        for problem in problems[:10]:
            print(f"      {problem}")
    else:
        print(f"PASS: {name}")


def check_syntax():
    """Every file must compile (no syntax errors)."""
    problems = []
    for f in ALL_FILES:
        name = f.relative_to(FOLDER).as_posix()
        try:
            compile(f.read_text(encoding="utf-8-sig"), name, "exec")
        except SyntaxError as err:
            problems.append(f"{name} line {err.lineno}: {err.msg}")
    report("Every .py file compiles", problems)


def check_windows_paths():
    """Windows paths must be raw strings, for example r"C:\\Users\\...". Without the r, \\U breaks the code."""
    problems = []
    for f in ALL_FILES:
        name = f.relative_to(FOLDER).as_posix()
        for number, line in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), start=1):
            if WINDOWS_PATH.search(line):
                problems.append(f"{name} line {number}: Windows path without r prefix")
    report("Windows paths are raw strings", problems)


def check_blank_ids():
    """A file that groups by station ID must also remove blank IDs (the 16 Nov 2026 mistake)."""
    problems = []
    for f in FILES:
        text = f.read_text(encoding="utf-8-sig")
        if "group_by(" in text and "station_id" in text and not BLANK_FILTER.search(text):
            problems.append(f"{f.name} groups by station_id but never removes blank IDs")
    report("Files that group by station ID also remove blank IDs", problems)


def check_collect_before_get_column():
    """On a lazy table, collect() must come before get_column(). Looks at the 8 lines above each call."""
    problems = []
    for f in FILES:
        lines = f.read_text(encoding="utf-8-sig").splitlines()
        for number, line in enumerate(lines, start=1):
            if ".get_column(" in line:
                before = lines[max(0, number - 9):number - 1]
                if any("scan_csv(" in x for x in before) and not any(".collect()" in x for x in before):
                    problems.append(f"{f.name} line {number}: get_column on a lazy table without collect()")
    report("get_column is only used after collect()", problems)


def git(*args):
    """Run a git command in this folder and return its result."""
    return subprocess.run(["git", *args], cwd=FOLDER, capture_output=True, text=True)


def check_repo_safety():
    """Raw data must never be tracked by git. Personal files must be git-ignored."""
    problems = []
    listed = git("ls-files")
    if listed.returncode != 0:
        problems.append("git ls-files failed: " + listed.stderr.strip())
    else:
        for path in listed.stdout.splitlines():
            lower = path.lower()
            suffix = Path(lower).suffix
            full = FOLDER / path
            # Raw data: zips anywhere, anything in data_raw/, or a CSV outside the two output folders.
            if lower.endswith(".zip") or path.startswith("data_raw/"):
                problems.append(f"raw-data file is tracked by git: {path}")
            elif suffix == ".csv" and not path.startswith(tuple(ALLOWED_EXTENSIONS)):
                problems.append(f"CSV tracked outside data_processed/ and results/: {path}")
            # Output folders: only aggregated file types.
            for folder, allowed in ALLOWED_EXTENSIONS.items():
                if path.startswith(folder) and suffix not in allowed:
                    problems.append(f"file type {suffix or '(none)'} not allowed in {folder}: {path}")
            # Content guard: a tracked CSV whose header looks like raw Citi Bike trips.
            if suffix == ".csv" and full.exists():
                with open(full, encoding="utf-8-sig", errors="replace") as handle:
                    if "ride_id" in handle.readline():
                        problems.append(f"CSV looks like raw trip data (header has ride_id): {path}")
            # Size guard.
            if full.exists() and full.stat().st_size > MAX_TRACKED_MB * 1024 * 1024:
                problems.append(f"file over {MAX_TRACKED_MB} MB is tracked: {path}")
    for name in ["StatActionLog.txt", "HANDOFF.md"]:
        if git("check-ignore", "-q", name).returncode != 0:
            problems.append(f"{name} is not git-ignored")
    report("Raw data and personal files stay out of git", problems)


def main():
    check_syntax()
    check_windows_paths()
    check_blank_ids()
    check_collect_before_get_column()
    check_repo_safety()
    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed: {', '.join(FAILED)}")
        sys.exit(1)
    print("All code checks passed.")


if __name__ == "__main__":
    main()
