# Coffee Shop SME — Mock Data Package

ข้อมูล mock สำหรับโปรเจกต์ Demand Forecasting ของร้านกาแฟ SME (สมมติชื่อ "ร้านลุงตี๋")
ออกแบบ pattern ให้สมจริงพอจะใช้ฝึก forecasting model ได้

---

## โครงสร้างโดยรวม

- **5 สาขา** แต่ละสาขาเป็นคนละ "บุคลิก" (office, mall, community, university, transit)
- **29 SKU** ใน 7 หมวด (กาแฟร้อน/เย็น, ชา, เครื่องดื่มอื่น, เบเกอรี่, แซนด์วิช, ของกินเล่น)
- **2 ปีเต็ม** (2024-01-01 ถึง 2025-12-31)
- **~508,000 transactions** ขนาดเพียงพอที่ model จะเรียน pattern ได้

---

## ไฟล์ในแพ็กเกจ

| ไฟล์ | จำนวนแถว | คำอธิบาย |
|---|---|---|
| `products.csv` | 29 | SKU ทั้งหมด + ราคาขาย + ต้นทุน |
| `stores.csv` | 5 | สาขาและประเภท |
| `calendar.csv` | 731 | วันที่ทั้งหมด + flag วันหยุด/payday |
| `weather.csv` | 731 | อุณหภูมิและสภาพอากาศรายวัน |
| `sales_transactions.csv` | 508,407 | transaction ระดับใบเสร็จ |
| `purchasing_orders.csv` | 15,224 | คำสั่งซื้อรายสัปดาห์เข้าสาขา |
| `schema.sql` | — | CREATE TABLE statements |
| `load.sql` | — | คำสั่ง `\copy` โหลดข้อมูล |

---

## วิธีใช้

```bash
# 1) สร้างฐานข้อมูล
createdb coffee_sme

# 2) สร้าง schema
psql coffee_sme -f schema.sql

# 3) เข้า psql แล้วโหลด CSV (ต้องอยู่ใน directory เดียวกับไฟล์ CSV)
cd /path/to/mock_data
psql coffee_sme
coffee_sme=# \i load.sql
```

ถ้าใช้ Docker หรือ remote DB ที่ \copy ใช้ไม่สะดวก ให้แก้เป็น `COPY ... FROM '/absolute/path/'` ใน load.sql แทน

---

## Patterns ที่ฝังในข้อมูล

ออกแบบให้ model สามารถ "เรียนรู้" pattern เหล่านี้ได้

**ช่วงเวลาในวัน** — peak เช้า 8-9 โมงสำหรับทุกสาขา, มี second peak ช่วงพักเที่ยง

**วันในสัปดาห์**
- ST01 (office) ยอดตกฮวบเสาร์-อาทิตย์ (~85% ตก)
- ST02 (mall) ยอดพุ่งเสาร์-อาทิตย์
- ST04 (university) ตกเสาร์-อาทิตย์
- ST05 (transit) ตกแต่ไม่เยอะ

**สภาพอากาศ**
- ร้อน (≥32°C) → กาแฟเย็นขายดี
- ฝนตก → ยอดรวมลด ~15%, แต่กาแฟร้อนสัดส่วนเพิ่ม
- พายุ → ยอดลด ~35%

**วันหยุด** — ส่วนใหญ่ยอดตก ยกเว้น ST02 (mall) ที่ใกล้เคียงปกติ

**ฤดูกาล**
- ธันวาคม +15% (ปลายปี)
- เมษายน -15% (สงกรานต์ คนกลับต่างจังหวัด)

**Trend** — เติบโตประมาณ 15% ตลอด 2 ปี

**Waste pattern (สำคัญสำหรับโปรเจกต์)** — เบเกอรี่/แซนด์วิช purchasing order สั่งเกินยอดขายจริง 15-40% (อายุสั้น 2-5 วัน) → ทำให้คำนวณ waste rate ได้จาก `qty_ordered` vs ยอดขาย

---

## Query ตัวอย่างเริ่มต้น

```sql
-- ยอดขายรายวัน (สำหรับ forecast)
SELECT
    datetime::date AS sale_date,
    store_id,
    product_id,
    SUM(qty) AS qty_sold
FROM sales_transactions
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

-- Waste rate ราย product/store (สิ่งที่จะ optimize)
WITH weekly_sales AS (
    SELECT
        DATE_TRUNC('week', datetime)::date AS week_start,
        store_id, product_id,
        SUM(qty) AS sold
    FROM sales_transactions
    GROUP BY 1, 2, 3
)
SELECT
    po.store_id,
    p.product_taxonomies,
    p.product_name,
    SUM(po.qty_ordered)              AS total_ordered,
    COALESCE(SUM(ws.sold), 0)        AS total_sold,
    SUM(po.qty_ordered) - COALESCE(SUM(ws.sold), 0) AS estimated_waste,
    ROUND(100.0 * (SUM(po.qty_ordered) - COALESCE(SUM(ws.sold), 0))
          / NULLIF(SUM(po.qty_ordered), 0), 1)       AS waste_pct
FROM purchasing_orders po
JOIN products p ON p.product_id = po.product_id
LEFT JOIN weekly_sales ws
       ON ws.week_start = po.arrival_date
      AND ws.store_id   = po.store_id
      AND ws.product_id = po.product_id
GROUP BY 1, 2, 3
ORDER BY waste_pct DESC NULLS LAST
LIMIT 20;

-- รวม feature สำหรับ forecast model
SELECT
    s.datetime::date AS d,
    s.store_id,
    s.product_id,
    SUM(s.qty) AS qty_sold,
    c.is_weekend, c.is_holiday, c.is_payday,
    w.temp_celsius, w.condition
FROM sales_transactions s
JOIN calendar c ON c.date = s.datetime::date
JOIN weather  w ON w.date = s.datetime::date
GROUP BY 1, 2, 3, c.is_weekend, c.is_holiday, c.is_payday, w.temp_celsius, w.condition;
```

---

## หมายเหตุ

- ไม่มี customer_id ในรอบนี้ (focus ที่ demand forecasting อย่างเดียว)
- ไม่มี promotion_id ในรอบนี้ (จะเพิ่มใน Phase 2 ของโปรเจกต์)
- ทุก seed คงที่ที่ 42 — รัน generator ใหม่จะได้ข้อมูลชุดเดียวกัน
