"""One-command wrappers for the fetch -> compute -> build pipeline (ROADMAP Q5).

A Makefile was the obvious choice here, but `make` is not present on the
Windows box this repo is developed on, and a task runner you cannot run is
not a task runner. Python is already a hard requirement for every stage of
the pipeline, so this uses it and nothing else -- stdlib only, no new
dependency (SPEC.md §2 keeps that list at requests + jinja2).

Usage:
    python tasks.py build              # render docs/ from committed data
    python tasks.py compute            # recompute every season on file
    python tasks.py fetch [--season Y] # re-fetch from ESPN (network)
    python tasks.py test               # run the scoring-math tests
    python tasks.py css                # rebuild the Tailwind bundle
    python tasks.py all                # compute + build + test (offline)
    python tasks.py refresh            # fetch + compute + build + test
"""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run(*cmd):
    """Run a command, echoing it first. Aborts the task on failure."""
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)


def seasons_on_file():
    """Every season with a committed raw fetch, oldest first."""
    return sorted(int(p.stem.split("-")[1])
                  for p in Path("data").glob("raw-*.json"))


def task_fetch(args):
    run(sys.executable, "fetch.py", "--season", str(args.season))


def task_compute(args):
    found = seasons_on_file()
    if not found:
        sys.exit("No data/raw-*.json found. Run `python tasks.py fetch` first.")
    for season in found:
        run(sys.executable, "compute.py", "--season", str(season))


def task_build(args):
    run(sys.executable, "build.py")


def task_test(args):
    run(sys.executable, "-m", "unittest", "test_compute", "-v")


def task_css(args):
    # npm is a dev-only dependency; shell=True so the .cmd shim resolves
    # on Windows the same way it does from a normal terminal.
    print("$ npm run build:css")
    if subprocess.run("npm run build:css", shell=True).returncode != 0:
        sys.exit(1)


def task_all(args):
    task_compute(args)
    task_build(args)
    task_test(args)


def task_refresh(args):
    task_fetch(args)
    task_compute(args)
    task_build(args)
    task_test(args)


TASKS = {
    "fetch": task_fetch,
    "compute": task_compute,
    "build": task_build,
    "test": task_test,
    "css": task_css,
    "all": task_all,
    "refresh": task_refresh,
}


def main():
    parser = argparse.ArgumentParser(
        description="Task runner for the LeagueStats pipeline.")
    parser.add_argument("task", choices=sorted(TASKS), help="which task to run")
    parser.add_argument("--season", type=int, default=datetime.now().year,
                        help="season for `fetch` (default: current year)")
    args = parser.parse_args()
    TASKS[args.task](args)


if __name__ == "__main__":
    main()
