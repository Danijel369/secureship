CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS customer (
    id serial PRIMARY KEY,
    first_name text NOT NULL,
    last_name text NOT NULL,
    phone_number text NOT NULL UNIQUE,
    address text NOT NULL
);

CREATE TABLE IF NOT EXISTS shipment (
    id serial PRIMARY KEY,
    customer_id int NOT NULL REFERENCES customer(id),
    tracking_number text NOT NULL UNIQUE,
    status text NOT NULL CHECK (status IN ('label_created','in_transit','out_for_delivery','delivered','exception')),
    exception_reason text NULL,
    carrier text,
    origin text,
    destination text,
    estimated_delivery date,
    last_update timestamptz
);

CREATE INDEX IF NOT EXISTS idx_shipment_customer_id ON shipment(customer_id);

CREATE TABLE IF NOT EXISTS package (
    id serial PRIMARY KEY,
    shipment_id int NOT NULL REFERENCES shipment(id),
    description text,
    weight_kg numeric(8,2),
    declared_value numeric(10,2)
);

CREATE TABLE IF NOT EXISTS chat_session (
    id text PRIMARY KEY,
    customer_id int NULL REFERENCES customer(id),
    state text NOT NULL DEFAULT 'anonymous',
    transcript jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
