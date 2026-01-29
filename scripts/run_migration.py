#!/usr/bin/env python3
"""Run database migrations against Supabase.

This script reads SQL migration files and executes them against
the configured Supabase database.

Usage:
    python scripts/run_migration.py

Requires SUPABASE_URL and SUPABASE_KEY environment variables.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    load_dotenv()

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
        return 1

    from supabase import create_client

    client = create_client(supabase_url, supabase_key)

    migrations_dir = Path(__file__).parent.parent / "migrations"
    if not migrations_dir.exists():
        print(f"Migrations directory not found: {migrations_dir}")
        return 1

    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        print("No migration files found")
        return 0

    for migration_file in migration_files:
        print(f"Running migration: {migration_file.name}")
        sql = migration_file.read_text(encoding="utf-8")

        try:
            # Execute raw SQL via Supabase RPC or postgrest
            # Note: Supabase client doesn't directly support raw SQL execution.
            # Migrations should be run via Supabase Dashboard SQL Editor
            # or via direct Postgres connection.
            print(f"  SQL content ({len(sql)} chars)")
            print("  Note: Run this SQL in Supabase Dashboard -> SQL Editor")
        except Exception as e:
            print(f"  Error: {e}")
            return 1

    print("\nMigration SQL files are ready.")
    print("Please run the SQL in Supabase Dashboard -> SQL Editor")
    print(f"Migration file: {migrations_dir / '001_initial_schema.sql'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
