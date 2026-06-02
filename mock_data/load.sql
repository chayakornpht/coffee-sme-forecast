-- ============================================================================
-- Load CSV data into the schema
-- Run AFTER schema.sql
-- ============================================================================
-- Usage:
--   1) Place all CSV files in the same directory as this script
--   2) Connect to your database with psql
--   3) cd to that directory, then run: \i load.sql
--
-- Note: \copy is a psql client-side command. If you prefer the server-side
--       COPY command, you'll need to use absolute paths and have superuser
--       permissions on the DB server's filesystem.

-- Reference tables first (foreign keys depend on them)
\copy products            FROM 'products.csv'            WITH (FORMAT csv, HEADER true);
\copy stores              FROM 'stores.csv'              WITH (FORMAT csv, HEADER true);
\copy calendar            FROM 'calendar.csv'            WITH (FORMAT csv, HEADER true, NULL '');
\copy weather             FROM 'weather.csv'             WITH (FORMAT csv, HEADER true);

-- Fact tables (largest one last)
\copy purchasing_orders   FROM 'purchasing_orders.csv'   WITH (FORMAT csv, HEADER true);
\copy sales_transactions  FROM 'sales_transactions.csv'  WITH (FORMAT csv, HEADER true);

-- Verify row counts
SELECT 'products'            AS table_name, COUNT(*) FROM products
UNION ALL SELECT 'stores',              COUNT(*) FROM stores
UNION ALL SELECT 'calendar',            COUNT(*) FROM calendar
UNION ALL SELECT 'weather',             COUNT(*) FROM weather
UNION ALL SELECT 'purchasing_orders',   COUNT(*) FROM purchasing_orders
UNION ALL SELECT 'sales_transactions',  COUNT(*) FROM sales_transactions;
