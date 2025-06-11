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
    session.run("uv", "pip", "install", ".[test]")
    session.run("uv", "run", "pytest", *session.posargs)


@nox.session(name="format", python=PYTHON_VERSION)
def format(session):
    """Lint the code and apply fixes in-place whenever possible."""
    session.run("uv", "pip", "install", ".[format]")
    session.run("ruff", "format", ".")
    session.run("ruff", "check", "--fix", ".")
    # session.run("uvx", "ty", "check")


@nox.session(name="generate-migration", python=PYTHON_VERSION)
def generate_migration(session: nox.Session) -> None:
    """Generate a new Alembic migration script."""
    session.run("uv", "pip", "install", ".[dev]")
    if not session.posargs:
        session.error('Migration message is required. Usage: nox -s generate-migration -- "Your migration message"')
    migration_message = session.posargs[0]
    session.run("uv", "run", "alembic", "revision", "--autogenerate", "-m", migration_message)
