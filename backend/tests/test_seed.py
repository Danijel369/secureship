"""Tests for scripts/seed_data.py idempotency and correctness."""
import sys
from datetime import date
from pathlib import Path

# seed_data.py lives in scripts/, not on the pytest path
_scripts = str(Path(__file__).resolve().parents[2] / "scripts")
if _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from seed_data import main as seed_main  # noqa: E402
from app.db import get_connection  # noqa: E402


def _counts() -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM customer")
            customers = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM shipment")
            shipments = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM package")
            packages = cur.fetchone()[0]
            cur.execute(
                """
                SELECT COUNT(DISTINCT sh.id) FROM shipment sh
                JOIN package pk ON pk.shipment_id = sh.id
                WHERE pk.declared_value >= 500
                """
            )
            high_value = cur.fetchone()[0]
    return {
        "customers": customers,
        "shipments": shipments,
        "packages": packages,
        "high_value": high_value,
    }


def test_seed_twice_identical_counts():
    seed_main()
    counts1 = _counts()
    seed_main()
    counts2 = _counts()
    assert counts1 == counts2
    assert counts1["customers"] == 27
    assert counts1["shipments"] == 50


def test_fixture_customers_match():
    seed_main()
    expected = [
        ("Avery", "Chen", "+15551230001", "12 Harbor Lane, Portland, OR 97201"),
        ("Jordan", "Patel", "+15551230002", "88 King Street, Austin, TX 78701"),
        ("Sam", "Okonkwo", "+15551230003", "4 Canal Road, Chicago, IL 60601"),
    ]
    with get_connection() as conn:
        with conn.cursor() as cur:
            for first, last, phone, address in expected:
                cur.execute(
                    "SELECT first_name, last_name, phone_number, address "
                    "FROM customer WHERE phone_number = %s",
                    (phone,),
                )
                row = cur.fetchone()
                assert row is not None, f"customer {phone!r} not found"
                assert row == (first, last, phone, address)


def test_fixture_shipments_match():
    seed_main()
    expected = [
        {
            "tracking_number": "MX10001",
            "status": "in_transit",
            "exception_reason": None,
            "carrier": "MockExpress",
            "origin": "Seattle, WA",
            "destination": "Portland, OR",
            "estimated_delivery": date(2026, 10, 12),
            "customer_ref": "Avery Chen",
        },
        {
            "tracking_number": "MX10002",
            "status": "exception",
            "exception_reason": "address_mismatch",
            "carrier": "MockExpress",
            "origin": "Dallas, TX",
            "destination": "Austin, TX",
            "estimated_delivery": date(2026, 10, 9),
            "customer_ref": "Jordan Patel",
        },
        {
            "tracking_number": "MX10003",
            "status": "delivered",
            "exception_reason": None,
            "carrier": "MockExpress",
            "origin": "Chicago, IL",
            "destination": "Chicago, IL",
            "estimated_delivery": date(2026, 10, 2),
            "customer_ref": "Sam Okonkwo",
        },
    ]
    with get_connection() as conn:
        with conn.cursor() as cur:
            for exp in expected:
                cur.execute(
                    """
                    SELECT s.tracking_number, s.status, s.exception_reason,
                           s.carrier, s.origin, s.destination, s.estimated_delivery,
                           c.first_name || ' ' || c.last_name AS full_name
                    FROM shipment s
                    JOIN customer c ON c.id = s.customer_id
                    WHERE s.tracking_number = %s
                    """,
                    (exp["tracking_number"],),
                )
                row = cur.fetchone()
                assert row is not None, f"{exp['tracking_number']} not found"
                tn, status, exc_reason, carrier, origin, dest, est_del, full_name = row
                assert tn == exp["tracking_number"]
                assert status == exp["status"]
                assert exc_reason == exp["exception_reason"]
                assert carrier == exp["carrier"]
                assert origin == exp["origin"]
                assert dest == exp["destination"]
                assert est_del == exp["estimated_delivery"]
                assert full_name == exp["customer_ref"]


def test_fixture_packages_match():
    seed_main()
    expected = [
        ("MX10001", "Ceramic mug", 0.8, 24.0),
        ("MX10002", "Laptop sleeve", 0.4, 45.0),
        ("MX10003", "Hardcover book", 1.1, 32.0),
    ]
    with get_connection() as conn:
        with conn.cursor() as cur:
            for tn, desc, weight, value in expected:
                cur.execute(
                    """
                    SELECT p.description, p.weight_kg, p.declared_value
                    FROM package p
                    JOIN shipment s ON s.id = p.shipment_id
                    WHERE s.tracking_number = %s
                    """,
                    (tn,),
                )
                row = cur.fetchone()
                assert row is not None, f"package for {tn} not found"
                assert row[0] == desc
                assert float(row[1]) == weight
                assert float(row[2]) == value


def test_mx10002_is_exception():
    seed_main()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status, exception_reason FROM shipment WHERE tracking_number = 'MX10002'",
            )
            row = cur.fetchone()
    assert row is not None
    assert row[0] == "exception"
    assert row[1] == "address_mismatch"
