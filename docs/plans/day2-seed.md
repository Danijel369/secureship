# Plan: scripts/seed_data.py + backend/tests/test_seed.py

## Context

Week 1 day 2 established the DB schema and app skeleton. This seed populates
`customer`, `shipment`, and `package` with the 3 demo people from
`scripts/fixtures/demo-identities.json` plus 24 generated customers and 47
generated shipments (27 customers / 50 shipments total), so the chat has
realistic parcel data to query. Re-run safety (ON CONFLICT DO UPDATE) means
`init_db.py` + `seed_data.py` can always be run from scratch without corruption.

## Files changed

| File | Action |
|------|--------|
| `scripts/seed_data.py` | create |
| `backend/tests/test_seed.py` | create |

Schema, fixture, pyproject.toml, uv.lock untouched.

## seed_data.py design

**Path setup** — identical pattern to `init_db.py`:
```python
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))
from app.db import get_connection
```

**Constants:**
- `BASE_DATE = date(2026, 10, 1)` — never `datetime.now()`
- `LAST_UPDATE = datetime(2026, 10, 1, 8, 0, 0, tzinfo=timezone.utc)` — fixed for all seed rows
- `FIXTURE_PATH` — `scripts/fixtures/demo-identities.json`

**Fixed lists (stdlib only, no Faker):**
- `FIRST_NAMES` / `LAST_NAMES` — 24 items each, gender-neutral
- `EXCLUDED_NAMES = {("Avery","Chen"), ("Jordan","Patel"), ("Sam","Okonkwo")}`
- `STREET_NAMES`, `CITY_STATE_ZIP` (24 US city/state/ZIP tuples)
- `PACKAGE_DESCRIPTIONS`, `EXCEPTION_REASONS`, `NON_EXCEPTION_STATUSES/WEIGHTS`

**`generate_customers(rng)`:**
1. Build all (first, last) combos from FIRST_NAMES × LAST_NAMES, exclude EXCLUDED_NAMES.
2. `rng.shuffle(combos)` → take first 24.
3. Phone: `+1555123{4+i:04d}` (no collisions with fixture +15551230001–3).
4. Address: `f"{rng.randint(1,999)} {rng.choice(STREET_NAMES)}, {city}, {state} {zip}"`
   where `(city, state, zip) = rng.choice(CITY_STATE_ZIP)`.

**`generate_shipments(customers, rng)`:**
1. **Exact-47 allocation** — constrained `rng.randint` loop so sum = 47, each in [1,3].
2. **Tracking numbers** — `MX{10004+i}`, skip 10099 (`n >= 10099 → n += 1`).
3. **Statuses** — `exception_indices = set(rng.sample(range(47), 4))`;
   `non_exc = sorted non-exception indices`. Force `non_exc[0]` → `label_created`,
   `non_exc[1]` → `out_for_delivery` (guarantees ≥ 1 of each). Remaining non-exception
   shipments use `rng.choices(NON_EXCEPTION_STATUSES, weights=[40,40,10,10])`.
   Exception shipments: `exception_reason = rng.choice(EXCEPTION_REASONS)`.
4. **destination** — customer's own city/state (parsed from address). **origin** — 
   `rng.choice(CITY_STATE_ZIP filtered to exclude destination)` (never equals destination).
5. **Dates** — `estimated_delivery = BASE_DATE + timedelta(rng.randint(2,30))`,
   `last_update = LAST_UPDATE`.

**`generate_packages(shipments, rng)`:**
- Per shipment: `rng.randint(1, 3)` packages.
- Shipment indices 0, 1, 2 (MX10004–MX10006): first package gets
  `declared_value = rng.uniform(500.0, 1500.0)` → guarantees ≥ 3 high-value shipments.
- All other packages: `declared_value = rng.uniform(5.0, 200.0)`.
- `weight_kg = round(rng.uniform(0.1, 20.0), 2)`, `description = rng.choice(PACKAGE_DESCRIPTIONS)`.

**`main()` — single transaction:**
1. Load fixture JSON. `rng = random.Random(42)`.
2. Call generate_* in order (customers → shipments → packages).
3. `all_customers = fixture["customers"] + customers_gen`.
4. `with get_connection() as conn:` (psycopg3 commits on clean exit):
   - INSERT customers with `ON CONFLICT (phone_number) DO UPDATE SET ...` → build `customer_id_map`.
   - INSERT fixture shipments (resolve `customer_ref` via map; raise ValueError if not found).
   - INSERT generated shipments; build `shipment_id_map` from both batches.
   - For every seed shipment: `DELETE FROM package WHERE shipment_id = %s`, then INSERT packages.
5. Second connection: query and print counts (no personal data).

**Output:**
```
customers: 27
shipments: delivered=N, exception=N, in_transit=N, label_created=N, out_for_delivery=N
packages: N
shipments_with_declared_value_gte_500: N
```

## test_seed.py design

**Location:** `backend/tests/test_seed.py`

Path setup adds `scripts/` to `sys.path` before `from seed_data import main as seed_main`.

| Test | What it checks |
|------|----------------|
| `test_seed_twice_identical_counts` | Run seed twice; assert counts dict equal; assert 27 customers, 50 shipments |
| `test_fixture_customers_match` | Query by phone_number; assert all 4 fields match fixture |
| `test_fixture_shipments_match` | Query MX10001–MX10003; assert all shipment fields + customer full name |
| `test_fixture_packages_match` | Query packages via tracking_number; assert description, weight_kg, declared_value |
| `test_mx10002_is_exception` | Direct assert status='exception', exception_reason='address_mismatch' |

Each test calls `seed_main()` at the start (idempotent; safe).

## Verification

```
cd backend && uv run python ../scripts/seed_data.py   # run once
cd backend && uv run python ../scripts/seed_data.py   # run again, same output
cd backend && uv run pytest tests/test_seed.py -v
cd backend && uv run pytest -v                        # all tests green
```
