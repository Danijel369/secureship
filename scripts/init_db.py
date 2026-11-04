#!/usr/bin/env python3
"""Initialize database schema from backend/app/schema.sql"""
from pathlib import Path
import sys

# Add backend to path so we can import config and db
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db import get_connection


def main():
    schema_path = backend_path / "app" / "schema.sql"

    if not schema_path.exists():
        print(f"Error: schema file not found at {schema_path}", file=sys.stderr)
        sys.exit(1)

    schema_sql = schema_path.read_text()

    print("Applying schema...")
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
        print("Schema applied successfully.")
    except Exception as e:
        print(f"Error applying schema: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
