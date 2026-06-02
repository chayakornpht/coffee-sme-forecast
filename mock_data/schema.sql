-- ============================================================================
-- Coffee Shop SME — Mock Data Schema
-- PostgreSQL 13+
-- ============================================================================
-- Run order: this file first (creates tables), then load.sql (imports CSVs)

DROP TABLE IF EXISTS purchasing_orders   CASCADE;
DROP TABLE IF EXISTS sales_transactions  CASCADE;
DROP TABLE IF EXISTS weather             CASCADE;
DROP TABLE IF EXISTS calendar            CASCADE;
DROP TABLE IF EXISTS stores              CASCADE;
DROP TABLE IF EXISTS products            CASCADE;

-- ---------------------------------------------------------------------------
-- Reference tables
-- ---------------------------------------------------------------------------
CREATE TABLE products (
    product_id          VARCHAR(10)  PRIMARY KEY,
    product_name        VARCHAR(50)  NOT NULL,
    product_taxonomies  VARCHAR(30)  NOT NULL,
    price               NUMERIC(8,2) NOT NULL,
    cost_per_unit       NUMERIC(8,2) NOT NULL
);

CREATE TABLE stores (
    store_id    VARCHAR(10) PRIMARY KEY,
    store_type  VARCHAR(30) NOT NULL
);

CREATE TABLE calendar (
    date          DATE        PRIMARY KEY,
    is_weekend    BOOLEAN     NOT NULL,
    is_holiday    BOOLEAN     NOT NULL,
    holiday_name  VARCHAR(50),
    is_payday     BOOLEAN     NOT NULL
);

CREATE TABLE weather (
    date          DATE         PRIMARY KEY,
    temp_celsius  NUMERIC(4,1) NOT NULL,
    condition     VARCHAR(20)  NOT NULL
);

-- ---------------------------------------------------------------------------
-- Fact tables
-- ---------------------------------------------------------------------------
CREATE TABLE sales_transactions (
    transaction_id  VARCHAR(20) PRIMARY KEY,
    datetime        TIMESTAMP   NOT NULL,
    product_id      VARCHAR(10) NOT NULL REFERENCES products(product_id),
    qty             INTEGER     NOT NULL CHECK (qty > 0),
    store_id        VARCHAR(10) NOT NULL REFERENCES stores(store_id)
);

CREATE TABLE purchasing_orders (
    po_id          VARCHAR(20)  PRIMARY KEY,
    store_id       VARCHAR(10)  NOT NULL REFERENCES stores(store_id),
    product_id     VARCHAR(10)  NOT NULL REFERENCES products(product_id),
    qty_ordered    INTEGER      NOT NULL CHECK (qty_ordered > 0),
    arrival_date   DATE         NOT NULL,
    expire_date    DATE         NOT NULL,
    cost_per_unit  NUMERIC(8,2) NOT NULL,
    CHECK (expire_date >= arrival_date)
);

-- ---------------------------------------------------------------------------
-- Indexes for typical analytical queries
-- ---------------------------------------------------------------------------
-- Time-range scans on sales (forecasting, daily aggregation)
CREATE INDEX idx_sales_datetime         ON sales_transactions(datetime);
CREATE INDEX idx_sales_date             ON sales_transactions((datetime::date));

-- Group-by store/product (per-SKU forecasting, store performance)
CREATE INDEX idx_sales_store_product    ON sales_transactions(store_id, product_id);
CREATE INDEX idx_sales_product_datetime ON sales_transactions(product_id, datetime);

-- PO lookups for waste analysis
CREATE INDEX idx_po_store_product       ON purchasing_orders(store_id, product_id);
CREATE INDEX idx_po_expire              ON purchasing_orders(expire_date);
