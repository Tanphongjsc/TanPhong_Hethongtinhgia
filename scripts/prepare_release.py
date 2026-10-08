"""Prepare a configured release locally; never deploy, migrate or seed data."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    os.environ.setdefault("APP_ENV", "production")
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.production"
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm:
        sys.exit("Build cần Node/npm; runtime sau build không cần Node.")
    commands = [
        [npm, "ci"], [npm, "run", "build"],
        [sys.executable, "manage.py", "collectstatic", "--noinput", "--settings=config.production"],
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level=ERROR", "--settings=config.production"],
        [sys.executable, "-m", "config.serve", "--check"],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
    print("Release preparation PASS. Chưa deploy/restart; không migration hoặc seed.")


if __name__ == "__main__":
    main()
