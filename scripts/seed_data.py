#!/usr/bin/env python3
"""Seed SecureShip database with demo customers, shipments, and packages."""
from pathlib import Path
import sys
import json
import random
from datetime import date, datetime, timedelta, timezone

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db import get_connection  # noqa: E402

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "demo-identities.json"
BASE_DATE = date(2026, 10, 1)
LAST_UPDATE = datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc)

FIRST_NAMES = [
    "Alex", "Blake", "Casey", "Dana", "Drew", "Ellis", "Finley", "Gray",
    "Harper", "Hayden", "Jamie", "Jules", "Kennedy", "Lane", "Logan", "Morgan",
    "Parker", "Quinn", "Reese", "River", "Robin", "Sage", "Skyler", "Taylor",
]
LAST_NAMES = [
    "Anderson", "Brooks", "Carter", "Davis", "Edwards", "Foster", "Garcia", "Hall",
    "Harris", "Jackson", "Kim", "Lewis", "Martin", "Miller", "Moore", "Nelson",
    "Perez", "Roberts", "Robinson", "Scott", "Smith", "Thompson", "Turner", "Walker",
]
EXCLUDED_NAMES = {("Avery", "Chen"), ("Jordan", "Patel"), ("Sam", "Okonkwo")}

STREET_NAMES = [
    "Elm Street", "Oak Avenue", "Main Street", "Pine Road", "Cedar Lane",
    "Maple Drive", "Birch Way", "Willow Court", "Ash Boulevard", "Walnut Place",
]
CITY_STATE_ZIP = [
    ("Denver", "CO", "80202"), ("Phoenix", "AZ", "85001"), ("Nashville", "TN", "37201"),
    ("Seattle", "WA", "98101"), ("Boston", "MA", "02101"), ("Miami", "FL", "33101"),
    ("Dallas", "TX", "75201"), ("Detroit", "MI", "48201"), ("Minneapolis", "MN", "55401"),
    ("Atlanta", "GA", "30301"), ("Baltimore", "MD", "21201"), ("Milwaukee", "WI", "53201"),
    ("Albuquerque", "NM", "87101"), ("Tucson", "AZ", "85701"), ("Sacramento", "CA", "94203"),
    ("Mesa", "AZ", "85201"), ("Omaha", "NE", "68101"), ("Raleigh", "NC", "27601"),
    ("Colorado Springs", "CO", "80901"), ("Long Beach", "CA", "90802"),
    ("Virginia Beach", "VA", "23451"), ("Kansas City", "MO", "64101"),
    ("Indianapolis", "IN", "46201"), ("Louisville", "KY", "40201"),
]
PACKAGE_DESCRIPTIONS = [
    "Clothing", "Electronics", "Books", "Kitchenware", "Sporting goods",
    "Toys", "Jewelry", "Tools", "Shoes", "Home decor",
]
EXCEPTION_REASONS = ["address_mismatch", "weather_delay", "damaged_package"]
NON_EXCEPTION_STATUSES = ["in_transit", "delivered", "label_created", "out_for_delivery"]
NON_EXCEPTION_WEIGHTS = [40, 40, 10, 10]


def _tracking_number(idx: int) -> str:
    n = 10004 + idx
    if n >= 10099:
        n += 1
    return f"MX{n}"


def generate_customers(rng: random.Random) -> list[dict]:
    combos = [
        (f, l)
        for f in FIRST_NAMES
        for l in LAST_NAMES
        if (f, l) not in EXCLUDED_NAMES
    ]
    rng.shuffle(combos)
    customers = []
    for i, (first, last) in enumerate(combos[:24]):
        phone = f"+1555123{4 + i:04d}"
        street_num = rng.randint(1, 999)
        street = rng.choice(STREET_NAMES)
        city, state, zipcode = rng.choice(CITY_STATE_ZIP)
        address = f"{street_num} {street}, {city}, {state} {zipcode}"
        customers.append({
            "first_name": first,
            "last_name": last,
            "phone_number": phone,
            "address": address,
        })
    return customers


def generate_shipments(customers: list[dict], rng: random.Random) -> list[dict]:
    # Constrained allocation: exactly 47 shipments, each customer gets 1–3
    remaining = 47
    counts: list[int] = []
    for i in range(24):
        left = 24 - i
        lo = max(1, remaining - 3 * (left - 1))
        hi = min(3, remaining - (left - 1))
        n = rng.randint(lo, hi)
        counts.append(n)
        remaining -= n

    stubs: list[dict] = []
    for cust_idx, count in enumerate(counts):
        for _ in range(count):
            stubs.append({"cust_idx": cust_idx})

    for i, s in enumerate(stubs):
        s["tracking_number"] = _tracking_number(i)

    # Exactly 4 exception shipments; guarantee ≥1 label_created and ≥1 out_for_delivery
    exception_indices = set(rng.sample(range(47), 4))
    non_exc = [i for i in range(47) if i not in exception_indices]

    for i, s in enumerate(stubs):
        if i in exception_indices:
            s["status"] = "exception"
            s["exception_reason"] = rng.choice(EXCEPTION_REASONS)
        elif i == non_exc[0]:
            s["status"] = "label_created"
            s["exception_reason"] = None
        elif i == non_exc[1]:
            s["status"] = "out_for_delivery"
            s["exception_reason"] = None
        else:
            s["status"] = rng.choices(NON_EXCEPTION_STATUSES, weights=NON_EXCEPTION_WEIGHTS)[0]
            s["exception_reason"] = None

    for s in stubs:
        cust = customers[s["cust_idx"]]
        # destination = customer's own city/state (parsed from "N Street, City, ST ZIP")
        parts = cust["address"].split(", ")
        dest_city = parts[1]
        dest_state = parts[2].split(" ")[0]
        s["destination"] = f"{dest_city}, {dest_state}"
        # origin = different city
        origin_pool = [
            (c, st, z)
            for c, st, z in CITY_STATE_ZIP
            if f"{c}, {st}" != s["destination"]
        ]
        oc, os_, _ = rng.choice(origin_pool)
        s["origin"] = f"{oc}, {os_}"

    for s in stubs:
        offset = rng.randint(2, 30)
        s["estimated_delivery"] = BASE_DATE + timedelta(days=offset)
        s["last_update"] = LAST_UPDATE
        s["carrier"] = "MockExpress"

    return stubs


def generate_packages(shipments: list[dict], rng: random.Random) -> list[dict]:
    packages: list[dict] = []
    for i, s in enumerate(shipments):
        count = rng.randint(1, 3)
        for j in range(count):
            weight = round(rng.uniform(0.1, 20.0), 2)
            # First package of first 3 shipments is high-value (≥500) for policy tests
            if i < 3 and j == 0:
                value = round(rng.uniform(500.0, 1500.0), 2)
            else:
                value = round(rng.uniform(5.0, 200.0), 2)
            desc = rng.choice(PACKAGE_DESCRIPTIONS)
            packages.append({
                "tracking_number": s["tracking_number"],
                "description": desc,
                "weight_kg": weight,
                "declared_value": value,
            })
    return packages


def main() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text())
    rng = random.Random(42)

    customers_gen = generate_customers(rng)
    shipments_gen = generate_shipments(customers_gen, rng)
    packages_gen = generate_packages(shipments_gen, rng)

    all_customers = fixture["customers"] + customers_gen  # 3 + 24

    # Index packages by tracking number
    packages_by_tn: dict[str, list[dict]] = {}
    for p in fixture["packages"]:
        packages_by_tn.setdefault(p["tracking_number"], []).append(p)
    for p in packages_gen:
        packages_by_tn.setdefault(p["tracking_number"], []).append(p)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # customers
            customer_id_map: dict[str, int] = {}
            for c in all_customers:
                cur.execute(
                    """
                    INSERT INTO customer (first_name, last_name, phone_number, address)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (phone_number) DO UPDATE SET
                        first_name = EXCLUDED.first_name,
                        last_name  = EXCLUDED.last_name,
                        address    = EXCLUDED.address
                    RETURNING id
                    """,
                    (c["first_name"], c["last_name"], c["phone_number"], c["address"]),
                )
                cid = cur.fetchone()[0]
                customer_id_map[f"{c['first_name']} {c['last_name']}"] = cid

            # fixture shipments
            shipment_id_map: dict[str, int] = {}
            for s in fixture["shipments"]:
                ref = s["customer_ref"]
                if ref not in customer_id_map:
                    raise ValueError(f"customer_ref not found in seed: {ref!r}")
                cid = customer_id_map[ref]
                est = date.fromisoformat(s["estimated_delivery"])
                exc = s.get("exception_reason")
                cur.execute(
                    """
                    INSERT INTO shipment
                        (customer_id, tracking_number, status, exception_reason,
                         carrier, origin, destination, estimated_delivery, last_update)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tracking_number) DO UPDATE SET
                        customer_id        = EXCLUDED.customer_id,
                        status             = EXCLUDED.status,
                        exception_reason   = EXCLUDED.exception_reason,
                        carrier            = EXCLUDED.carrier,
                        origin             = EXCLUDED.origin,
                        destination        = EXCLUDED.destination,
                        estimated_delivery = EXCLUDED.estimated_delivery,
                        last_update        = EXCLUDED.last_update
                    RETURNING id
                    """,
                    (cid, s["tracking_number"], s["status"], exc,
                     s["carrier"], s["origin"], s["destination"], est, LAST_UPDATE),
                )
                shipment_id_map[s["tracking_number"]] = cur.fetchone()[0]

            # generated shipments
            for s in shipments_gen:
                cust = customers_gen[s["cust_idx"]]
                ref = f"{cust['first_name']} {cust['last_name']}"
                cid = customer_id_map[ref]
                cur.execute(
                    """
                    INSERT INTO shipment
                        (customer_id, tracking_number, status, exception_reason,
                         carrier, origin, destination, estimated_delivery, last_update)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tracking_number) DO UPDATE SET
                        customer_id        = EXCLUDED.customer_id,
                        status             = EXCLUDED.status,
                        exception_reason   = EXCLUDED.exception_reason,
                        carrier            = EXCLUDED.carrier,
                        origin             = EXCLUDED.origin,
                        destination        = EXCLUDED.destination,
                        estimated_delivery = EXCLUDED.estimated_delivery,
                        last_update        = EXCLUDED.last_update
                    RETURNING id
                    """,
                    (cid, s["tracking_number"], s["status"], s["exception_reason"],
                     s["carrier"], s["origin"], s["destination"],
                     s["estimated_delivery"], s["last_update"]),
                )
                shipment_id_map[s["tracking_number"]] = cur.fetchone()[0]

            # packages: delete existing then insert
            for tn, pkgs in packages_by_tn.items():
                sid = shipment_id_map[tn]
                cur.execute("DELETE FROM package WHERE shipment_id = %s", (sid,))
                for p in pkgs:
                    cur.execute(
                        """
                        INSERT INTO package (shipment_id, description, weight_kg, declared_value)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (sid, p["description"], p["weight_kg"], p["declared_value"]),
                    )

    # print counts only — no personal data
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM customer")
            n_customers = cur.fetchone()[0]

            cur.execute(
                "SELECT status, COUNT(*) FROM shipment GROUP BY status ORDER BY status"
            )
            status_counts = dict(cur.fetchall())

            cur.execute("SELECT COUNT(*) FROM package")
            n_packages = cur.fetchone()[0]

            cur.execute(
                """
                SELECT COUNT(DISTINCT sh.id) FROM shipment sh
                JOIN package pk ON pk.shipment_id = sh.id
                WHERE pk.declared_value >= 500
                """
            )
            n_high_value = cur.fetchone()[0]

    print(f"customers: {n_customers}")
    parts = ", ".join(f"{s}={c}" for s, c in sorted(status_counts.items()))
    print(f"shipments: {parts}")
    print(f"packages: {n_packages}")
    print(f"shipments_with_declared_value_gte_500: {n_high_value}")


if __name__ == "__main__":
    main()
