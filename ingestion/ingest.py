"""
Data ingestion for Coffee SME forecasting project.

โหลด mock CSV เข้า PostgreSQL แบบรันซ้ำได้ ทุกครั้งที่รันสคริปต์นี้
database จะกลับมาอยู่ในสภาพเดิม สะดวกตอนทำ EDA / ปรับ feature
แล้วต้อง reset ข้อมูลเพื่อเริ่มใหม่

Usage:
    export DB_URL='postgresql://user:pass@localhost:5432/coffee_sme'
    export DATA_DIR='./mock_data'
    python ingest.py
"""
import csv
import logging
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import psycopg2

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_URL      = os.environ.get("DB_URL", "postgresql://postgres:postgres@localhost:5432/coffee_sme")
DATA_DIR    = Path(os.environ.get("DATA_DIR", "./mock_data"))
SCHEMA_FILE = DATA_DIR / "schema.sql"

# Load order respects foreign-key dependencies:
# reference tables first, fact tables (sales, PO) last.
LOAD_ORDER = [
    "products",
    "stores",
    "calendar",
    "weather",
    "purchasing_orders",
    "sales_transactions",
]

# Expected column lists — used for pre-flight validation against CSV headers.
# Catching a column mismatch before we touch the DB makes debugging much easier.
EXPECTED_COLUMNS = {
    "products":           ["product_id", "product_name", "product_taxonomies", "price", "cost_per_unit"],
    "stores":             ["store_id", "store_type"],
    "calendar":           ["date", "is_weekend", "is_holiday", "holiday_name", "is_payday"],
    "weather":            ["date", "temp_celsius", "condition"],
    "purchasing_orders":  ["po_id", "store_id", "product_id", "qty_ordered",
                           "arrival_date", "expire_date", "cost_per_unit"],
    "sales_transactions": ["transaction_id", "datetime", "product_id", "qty", "store_id"],
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@contextmanager
def timed(label):
    """Log how long a block of work took."""
    t0 = time.perf_counter()
    yield
    log.info(f"  {label:<22} {time.perf_counter() - t0:>6.2f}s")


def read_csv_header(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return next(csv.reader(f))


def validate_csv(table: str, csv_path: Path) -> None:
    """Confirm CSV exists and its header matches the table schema."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing CSV: {csv_path}")
    header = read_csv_header(csv_path)
    expected = EXPECTED_COLUMNS[table]
    if header != expected:
        raise ValueError(
            f"Column mismatch for '{table}':\n"
            f"  expected: {expected}\n"
            f"  got:      {header}"
        )


def apply_schema(conn) -> None:
    """Drop and recreate all tables. Running this twice yields the same state."""
    log.info("Applying schema (drop & create) ...")
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def copy_csv(conn, table: str, csv_path: Path) -> None:
    """Bulk-load a CSV into the named table using PostgreSQL's COPY.

    COPY is ~100x faster than row-by-row INSERT on the sales table (~500k rows).
    `NULL ''` makes empty CSV fields (e.g. calendar.holiday_name on non-holidays)
    become SQL NULL rather than the empty string.
    """
    with conn.cursor() as cur, open(csv_path, "r", encoding="utf-8") as f:
        cur.copy_expert(
            f"COPY {table} FROM STDIN WITH (FORMAT csv, HEADER true, NULL '')",
            f,
        )


def verify_counts(conn) -> None:
    """Report row counts after load so reviewers can sanity-check."""
    log.info("Row counts:")
    with conn.cursor() as cur:
        for table in LOAD_ORDER:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            n = cur.fetchone()[0]
            log.info(f"  {table:<22} {n:>9,}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    log.info(f"data dir: {DATA_DIR.resolve()}")

    # Pre-flight: validate every CSV BEFORE we touch the database.
    # If we drop tables and then discover a typo halfway through, we lose state
    # for no reason. Fail fast, fail cheap.
    log.info("Pre-flight: validating CSV headers ...")
    for table in LOAD_ORDER:
        validate_csv(table, DATA_DIR / f"{table}.csv")
    log.info("  all CSVs ok.")

    # Single connection, single transaction-per-table.
    # `with psycopg2.connect()` auto-rolls-back on exception.
    with psycopg2.connect(DB_URL) as conn:
        apply_schema(conn)

        log.info("Loading data ...")
        for table in LOAD_ORDER:
            csv_path = DATA_DIR / f"{table}.csv"
            with timed(table):
                copy_csv(conn, table, csv_path)
        conn.commit()

        verify_counts(conn)

    log.info("Done.")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        log.error(f"File error: {e}")
        sys.exit(1)
    except psycopg2.Error as e:
        log.error(f"Database error: {e}")
        sys.exit(2)
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        sys.exit(3)
