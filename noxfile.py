from __future__ import annotations

from pathlib import Path

import nox

PYTHON_VERSION = "3.12"
ROOT = Path(".")
nox.options.default_venv_backend = "uv"
nox.options.stop_on_first_error = True
nox.options.reuse_existing_virtualenvs = True


@nox.session(name="test", python=PYTHON_VERSION)
def test(session):
    """Run pytest with optional arguments forwarded from the command line."""
    session.run("uv", "sync", "--active", "--extra", "dev")
    session.run("pytest", "-s", "-vv", ".", *session.posargs)


@nox.session(name="format", python=PYTHON_VERSION)
def format(session):
    """Lint the code and apply fixes in-place whenever possible."""
    session.run("uv", "sync", "--active", "--extra", "format", "--extra", "dev")
    session.run("ruff", "format", ".")
    session.run("ruff", "check", "--fix", ".")
    session.run("pyright")
    # session.run("uvx", "ty", "check")
