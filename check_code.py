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

# Step 2: settings. Every .py file in this folder is checked, except this one.
FOLDER = Path(__file__).resolve().parent
THIS_FILE = Path(__file__).name
FILES = sorted(p for p in FOLDER.glob("*.py") if p.name != THIS_FILE)
FAILED = []                                 # names of checks that failed

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
    for f in FILES:
        try:
            compile(f.read_text(encoding="utf-8"), f.name, "exec")
        except SyntaxError as err:
            problems.append(f"{f.name} line {err.lineno}: {err.msg}")
    report("Every .py file compiles", problems)


def check_windows_paths():
    """Windows paths must be raw strings, for example r"C:\\Users\\...". Without the r, \\U breaks the code."""
    problems = []
    for f in FILES:
        for number, line in enumerate(f.read_text(encoding="utf-8").splitlines(), start=1):
            if WINDOWS_PATH.search(line):
                problems.append(f"{f.name} line {number}: Windows path without r prefix")
    report("Windows paths are raw strings", problems)


def check_blank_ids():
    """A file that groups by station ID must also remove blank IDs (the 16 Nov 2026 mistake)."""
    problems = []
    for f in FILES:
        text = f.read_text(encoding="utf-8")
        if "group_by(" in text and "station_id" in text and not BLANK_FILTER.search(text):
            problems.append(f"{f.name} groups by station_id but never removes blank IDs")
    report("Files that group by station ID also remove blank IDs", problems)


def check_collect_before_get_column():
    """On a lazy table, collect() must come before get_column(). Looks at the 8 lines above each call."""
    problems = []
    for f in FILES:
        lines = f.read_text(encoding="utf-8").splitlines()
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
            if (path.lower().endswith((".zip", ".csv")) and not path.startswith("data_processed/")) or path.startswith("data_raw/"):
                problems.append(f"raw-data file is tracked by git: {path}")
            if path.startswith("data_processed/") and path != "data_processed/station_hour.csv":
                problems.append(f"unexpected file tracked in data_processed/: {path}")
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
