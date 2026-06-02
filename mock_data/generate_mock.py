"""
Mock data generator: Coffee shop SME (ร้านกาแฟลุงตี๋)
- 5 stores, 29 products, 24 months of data (2024-01-01 to 2025-12-31)
- Embeds realistic patterns: morning peak, weekend/weekday differences,
  weather impact, holidays, seasonality, store-type behavior, bakery waste
- Output: 6 CSV files ready for PostgreSQL \\copy import
"""
import os
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd

np.random.seed(42)

OUT = "/home/claude/mock_data"
os.makedirs(OUT, exist_ok=True)

# =========================================================================
# 1) Reference data
# =========================================================================
START = date(2024, 1, 1)
END   = date(2025, 12, 31)
N_DAYS = (END - START).days + 1
all_dates = [START + timedelta(days=i) for i in range(N_DAYS)]

# Stores (5 locations, each a different "character")
stores = [
    ("ST01", "office_building"),  # busy weekdays, dead weekends
    ("ST02", "mall"),              # busy weekends, holidays
    ("ST03", "community"),         # steady residential
    ("ST04", "university"),        # academic rhythm
    ("ST05", "transit_hub"),       # morning rush dominant
]
store_df = pd.DataFrame(stores, columns=["store_id", "store_type"])

# Products (29 SKUs across categories)
products = [
    # Hot Coffee
    ("PROD001", "espresso",            "coffee_hot",   65,  18),
    ("PROD002", "americano",           "coffee_hot",   70,  18),
    ("PROD003", "latte",               "coffee_hot",   80,  22),
    ("PROD004", "cappuccino",          "coffee_hot",   80,  22),
    ("PROD005", "mocha",               "coffee_hot",   90,  28),
    ("PROD006", "caramel_macchiato",   "coffee_hot",   95,  30),
    # Iced Coffee
    ("PROD007", "iced_americano",      "coffee_iced",  75,  19),
    ("PROD008", "iced_latte",          "coffee_iced",  85,  24),
    ("PROD009", "iced_mocha",          "coffee_iced",  95,  30),
    ("PROD010", "iced_caramel",        "coffee_iced", 100,  32),
    # Tea
    ("PROD011", "thai_tea",            "tea",          65,  18),
    ("PROD012", "green_tea_latte",     "tea",          85,  26),
    ("PROD013", "lemon_tea",           "tea",          70,  20),
    # Other drinks
    ("PROD014", "hot_chocolate",       "other_drink",  90,  30),
    ("PROD015", "matcha_latte",        "other_drink", 100,  35),
    ("PROD016", "fruit_smoothie",      "other_drink", 120,  45),
    # Bakery (short expiry — drives waste data)
    ("PROD017", "croissant",           "bakery",       55,  22),
    ("PROD018", "pain_au_chocolat",    "bakery",       65,  28),
    ("PROD019", "danish",              "bakery",       60,  25),
    ("PROD020", "blueberry_muffin",    "bakery",       55,  20),
    ("PROD021", "brownie",             "bakery",       60,  22),
    ("PROD022", "cheesecake_slice",    "bakery",       95,  38),
    ("PROD023", "cookie",              "bakery",       35,  12),
    # Sandwiches
    ("PROD024", "ham_cheese_sandwich", "sandwich",     95,  40),
    ("PROD025", "tuna_sandwich",       "sandwich",    105,  45),
    ("PROD026", "egg_salad_sandwich",  "sandwich",     95,  40),
    # Snacks (long shelf life)
    ("PROD027", "granola_bar",         "snack",        45,  18),
    ("PROD028", "yogurt_cup",          "snack",        55,  22),
    ("PROD029", "fruit_cup",           "snack",        65,  28),
]
product_df = pd.DataFrame(
    products,
    columns=["product_id", "product_name", "product_taxonomies", "price", "cost_per_unit"],
)

# =========================================================================
# 2) Calendar (Thai holidays + paydays)
# =========================================================================
thai_holidays = {
    "2024-01-01": "New Year",        "2024-02-10": "Chinese New Year",
    "2024-04-13": "Songkran",        "2024-04-14": "Songkran",
    "2024-04-15": "Songkran",        "2024-05-01": "Labour Day",
    "2024-05-22": "Visakha Bucha",   "2024-07-22": "Asalha Bucha",
    "2024-08-12": "Mother Day",      "2024-10-13": "King Bhumibol Memorial",
    "2024-10-23": "Chulalongkorn",   "2024-12-05": "Father Day",
    "2024-12-10": "Constitution",    "2024-12-31": "New Year Eve",
    "2025-01-01": "New Year",        "2025-01-29": "Chinese New Year",
    "2025-04-13": "Songkran",        "2025-04-14": "Songkran",
    "2025-04-15": "Songkran",        "2025-05-01": "Labour Day",
    "2025-05-12": "Visakha Bucha",   "2025-06-09": "Coronation",
    "2025-07-10": "Asalha Bucha",    "2025-08-12": "Mother Day",
    "2025-10-13": "King Bhumibol Memorial", "2025-10-23": "Chulalongkorn",
    "2025-12-05": "Father Day",      "2025-12-10": "Constitution",
    "2025-12-31": "New Year Eve",
}

def last_day_of_month(d):
    nxt = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return nxt - timedelta(days=1)

cal_rows = []
for d in all_dates:
    iso = d.isoformat()
    holiday_name = thai_holidays.get(iso, "")
    cal_rows.append({
        "date":         iso,
        "is_weekend":   d.weekday() >= 5,
        "is_holiday":   bool(holiday_name),
        "holiday_name": holiday_name if holiday_name else None,
        "is_payday":    d.day == 15 or d == last_day_of_month(d),
    })
calendar_df = pd.DataFrame(cal_rows)

# =========================================================================
# 3) Weather (Bangkok-ish seasonal patterns)
# =========================================================================
month_temp = {1:28, 2:30, 3:33, 4:35, 5:34, 6:32, 7:31, 8:31, 9:31, 10:31, 11:29, 12:27}
month_rain = {1:0.05,2:0.05,3:0.10,4:0.15,5:0.40,6:0.50,7:0.55,8:0.55,9:0.60,10:0.45,11:0.15,12:0.05}

weather_rows = []
for d in all_dates:
    temp = month_temp[d.month] + np.random.normal(0, 2)
    if np.random.random() < month_rain[d.month]:
        cond = "rainy" if np.random.random() < 0.85 else "stormy"
    else:
        cond = "sunny" if temp > 32 else "cloudy"
    weather_rows.append({
        "date":         d.isoformat(),
        "temp_celsius": round(float(temp), 1),
        "condition":    cond,
    })
weather_df = pd.DataFrame(weather_rows)

# Quick lookup: date -> (temp, condition)
weather_lookup = {r["date"]: (r["temp_celsius"], r["condition"]) for r in weather_rows}
holiday_lookup = {iso: True for iso in thai_holidays}

# =========================================================================
# 4) Sales transactions (the heavy table)
# =========================================================================
print("Generating sales transactions ...")

# Volume baseline per store type
store_base = {"ST01": 180, "ST02": 130, "ST03": 100, "ST04": 140, "ST05": 200}

# Hour-of-day distribution per store type (24 weights, sum normalized later)
hour_patterns = {
    "ST01": np.array([0,0,0,0,0,0,1, 6,12,10, 5, 8,10, 6, 3, 2, 2, 2, 1, 1, 1, 0, 0, 0], dtype=float),  # office
    "ST02": np.array([0,0,0,0,0,0,0, 1, 3, 5, 7, 8,10,10, 9, 8, 7, 6, 5, 4, 2, 1, 0, 0], dtype=float),  # mall
    "ST03": np.array([0,0,0,0,0,0,0, 3, 8,12,10, 6, 5, 8, 9, 7, 5, 4, 3, 2, 1, 1, 0, 0], dtype=float),  # community
    "ST04": np.array([0,0,0,0,0,0,0, 2, 7,10, 8, 6, 5, 8, 9, 8, 6, 5, 3, 2, 1, 0, 0, 0], dtype=float),  # university
    "ST05": np.array([0,0,0,0,0,1, 5,15,12, 5, 3, 3, 3, 3, 3, 5, 8,10, 8, 4, 2, 1, 0, 0], dtype=float),  # transit
}
hour_probs = {s: w / w.sum() for s, w in hour_patterns.items()}

# Helpers
prod_ids   = [p[0] for p in products]
prod_cats  = [p[2] for p in products]
prod_names = [p[1] for p in products]

def product_probs_for_day(temp, condition):
    """Return product-selection probability vector for the day's conditions."""
    w = np.ones(len(products), dtype=float)
    for i, cat in enumerate(prod_cats):
        if cat == "coffee_hot":
            w[i] = 3.0 if temp < 30 else 2.0
            if condition in ("rainy", "stormy"): w[i] *= 1.4
        elif cat == "coffee_iced":
            w[i] = 3.5 if temp >= 32 else 1.5
            if condition in ("rainy", "stormy"): w[i] *= 0.6
        elif cat == "tea":          w[i] = 1.5
        elif cat == "other_drink":  w[i] = 1.0
        elif cat == "bakery":       w[i] = 2.0
        elif cat == "sandwich":     w[i] = 0.8
        elif cat == "snack":        w[i] = 0.5
        # Premium items less common
        if "macchiato" in prod_names[i] or "cheesecake" in prod_names[i] or "smoothie" in prod_names[i]:
            w[i] *= 0.7
    return w / w.sum()

def daily_volume(store_id, d, is_weekend, is_holiday, condition):
    base = store_base[store_id]
    if store_id == "ST01" and is_weekend:  base *= 0.4
    elif store_id == "ST02" and is_weekend: base *= 1.4
    elif store_id == "ST04" and is_weekend: base *= 0.5
    elif store_id == "ST05" and is_weekend: base *= 0.7
    if is_holiday:
        base *= 0.5 if store_id != "ST02" else 0.9
    if condition == "rainy":  base *= 0.85
    if condition == "stormy": base *= 0.65
    # Seasonality
    seasonal = {1:1.00,2:1.00,3:1.05,4:0.85,5:1.00,6:1.00,7:1.00,
                8:1.00,9:1.00,10:1.00,11:1.00,12:1.15}[d.month]
    base *= seasonal
    # Mild upward trend
    base *= (1 + (d - START).days * 0.0002)
    # Noise
    base *= np.random.normal(1.0, 0.10)
    return max(int(base), 10)

# Pre-compute qty distribution (most transactions are 1 item)
qty_choices  = np.array([1, 2, 3])
qty_weights  = np.array([0.78, 0.18, 0.04])

# Generate
rng_default = np.random.default_rng(42)
sales_chunks = []
trans_id = 0

for d in all_dates:
    iso = d.isoformat()
    is_weekend = d.weekday() >= 5
    is_holiday = iso in holiday_lookup
    temp, condition = weather_lookup[iso]
    p_probs = product_probs_for_day(temp, condition)

    for store_id, _ in stores:
        n = daily_volume(store_id, d, is_weekend, is_holiday, condition)
        h_probs = hour_probs[store_id]

        hours    = rng_default.choice(24, size=n, p=h_probs)
        minutes  = rng_default.integers(0, 60, size=n)
        seconds  = rng_default.integers(0, 60, size=n)
        prod_idx = rng_default.choice(len(products), size=n, p=p_probs)
        qtys     = rng_default.choice(qty_choices, size=n, p=qty_weights)

        # Build timestamps as strings (faster than datetime objects for many rows)
        base_str = f"{d.year:04d}-{d.month:02d}-{d.day:02d}"
        ts_array = [
            f"{base_str} {int(h):02d}:{int(m):02d}:{int(s):02d}"
            for h, m, s in zip(hours, minutes, seconds)
        ]
        prod_array = [prod_ids[i] for i in prod_idx]
        txn_ids = [f"TXN{trans_id + i:08d}" for i in range(n)]
        trans_id += n

        sales_chunks.append(pd.DataFrame({
            "transaction_id": txn_ids,
            "datetime":       ts_array,
            "product_id":     prod_array,
            "qty":            qtys.astype(int),
            "store_id":       store_id,
        }))

sales_df = pd.concat(sales_chunks, ignore_index=True)
sales_df = sales_df.sort_values("datetime").reset_index(drop=True)
# Re-issue sequential transaction IDs in chronological order
sales_df["transaction_id"] = [f"TXN{i:08d}" for i in range(len(sales_df))]
print(f"  rows: {len(sales_df):,}")

# =========================================================================
# 5) Purchasing orders (weekly restocks; bakery over-orders → waste)
# =========================================================================
print("Generating purchasing orders ...")

sales_df["_date"] = pd.to_datetime(sales_df["datetime"]).dt.date
# Week starts on Monday — group by ISO week
sales_df["_week"] = pd.to_datetime(sales_df["datetime"]).dt.to_period("W-SUN").dt.start_time.dt.date

weekly = (
    sales_df.groupby(["_week", "store_id", "product_id"], as_index=False)["qty"]
    .sum()
    .rename(columns={"qty": "week_qty"})
)
weekly = weekly.merge(product_df[["product_id", "product_taxonomies", "cost_per_unit"]], on="product_id")

# Overshoot rules per category
def overshoot(cat):
    return {
        "bakery":      (1.15, 1.40),
        "sandwich":    (1.05, 1.20),
        "snack":       (1.00, 1.15),
        "coffee_hot":  (1.00, 1.10),
        "coffee_iced": (1.00, 1.10),
        "tea":         (1.00, 1.10),
        "other_drink": (1.00, 1.10),
    }[cat]

def expire_days(cat):
    if cat == "bakery":   return np.random.randint(2, 5)
    if cat == "sandwich": return np.random.randint(2, 4)
    if cat == "snack":    return np.random.randint(30, 90)
    return np.random.randint(180, 365)  # coffee beans / syrups

po_rows = []
for i, r in enumerate(weekly.itertuples(index=False)):
    low, high = overshoot(r.product_taxonomies)
    qty_ordered = max(int(r.week_qty * np.random.uniform(low, high)), 1)
    arrival = r._0  # _week column
    exp_d   = expire_days(r.product_taxonomies)
    expire  = arrival + timedelta(days=exp_d)
    po_rows.append({
        "po_id":         f"PO{i:07d}",
        "store_id":      r.store_id,
        "product_id":    r.product_id,
        "qty_ordered":   qty_ordered,
        "arrival_date":  arrival.isoformat(),
        "expire_date":   expire.isoformat(),
        "cost_per_unit": r.cost_per_unit,
    })

po_df = pd.DataFrame(po_rows)
print(f"  rows: {len(po_df):,}")

# Clean up temp columns before export
sales_df = sales_df.drop(columns=["_date", "_week"])

# =========================================================================
# 6) Write CSVs
# =========================================================================
print("Writing CSV files ...")
product_df.to_csv  (f"{OUT}/products.csv",            index=False)
store_df.to_csv    (f"{OUT}/stores.csv",              index=False)
calendar_df.to_csv (f"{OUT}/calendar.csv",            index=False)
weather_df.to_csv  (f"{OUT}/weather.csv",             index=False)
sales_df.to_csv    (f"{OUT}/sales_transactions.csv",  index=False)
po_df.to_csv       (f"{OUT}/purchasing_orders.csv",   index=False)

# Summary
print("\nDone.")
for name, df in [
    ("products", product_df), ("stores", store_df),
    ("calendar", calendar_df), ("weather", weather_df),
    ("sales_transactions", sales_df), ("purchasing_orders", po_df),
]:
    print(f"  {name:<22} rows={len(df):>8,}")
