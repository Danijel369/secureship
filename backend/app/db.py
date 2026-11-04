"""Database connection helper using psycopg 3."""
import psycopg
from app.config import DATABASE_URL


def get_connection():
    """Return a new psycopg connection. Caller must close it."""
    return psycopg.connect(DATABASE_URL)
