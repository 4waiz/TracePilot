#!/usr/bin/env python
"""
Development utility: drop all tables, recreate them, and re-seed demo users.

Usage:
    python db_reset.py          # interactive confirmation
    python db_reset.py --yes    # skip confirmation
"""

import sys

from backend.database import Base, engine
from backend.seed import run_seed

# Ensure all models are imported so metadata knows about them
import backend.models  # noqa: F401


def reset_database(skip_confirm: bool = False) -> None:
    if not skip_confirm:
        answer = input(
            "This will DROP ALL TABLES and recreate them. All data will be lost.\n"
            "Continue? [y/N] "
        )
        if answer.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return

    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")

    print("Recreating tables and seeding demo data...")
    run_seed()
    print("Database reset complete.")


if __name__ == "__main__":
    skip = "--yes" in sys.argv or "-y" in sys.argv
    reset_database(skip_confirm=skip)
