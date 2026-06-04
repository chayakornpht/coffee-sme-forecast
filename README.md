# Coffee SME — Demand Forecasting

โปรเจกต์ Data Science เพื่อลด waste และเพิ่ม revenue ให้ร้านกาแฟ SME
ผ่าน demand forecasting รายสาขา/รายสินค้า/รายวัน

---

## Business Problem

ร้านกาแฟ SME ที่มีหลายสาขา (สมมติ "ร้านลุงตี๋" 5 สาขา) เผชิญปัญหา

- เบเกอรี่และของสด **หมดอายุก่อนขายหมด** → revenue หายไปทุกวัน
- เจ้าของสั่งสต็อกจาก "ความรู้สึก" ไม่ใช่ข้อมูล → over-order หรือ under-stock สลับกันไป
- ไม่รู้ว่าวันไหนควรเตรียมของเท่าไหร่ในแต่ละสาขา

**เป้าหมาย** สร้าง forecast model ที่พยากรณ์ยอดขายล่วงหน้า 7 วัน
ระดับสาขา × สินค้า × วัน เพื่อให้สั่งของได้แม่นขึ้น ลด waste ของหมดอายุ

---

## โครงสร้างโปรเจกต์

```
coffee-sme-forecast/
├── mock_data/              ข้อมูล mock + schema + generator
│   ├── generate_mock.py    สคริปต์สร้าง CSV (รันแล้วได้ data ชุดเดียวกัน เพราะ seed คงที่)
│   ├── schema.sql          PostgreSQL DDL
│   └── README.md           อธิบาย data ครบทุก column
├── ingestion/              สคริปต์โหลด CSV เข้า Postgres
│   ├── ingest.py           idempotent loader ใช้ COPY FROM STDIN
│   └── README.md
└── README.md               ไฟล์นี้
```

ข้อมูล CSV ไม่ commit ใน repo — ใครจะใช้รัน `generate_mock.py` เพื่อสร้างข้อมูลชุดเดียวกัน

---


## Tech Stack

- **Python 3.11** — pandas, numpy สำหรับ data manipulation
- **PostgreSQL 18** — data storage และ analytical queries
- **psycopg2** — Python ↔ Postgres connector (ใช้ COPY FROM STDIN)
- Coming next: Jupyter, scikit-learn, LightGBM, matplotlib

---

## Data ที่ใช้

Mock data 2 ปี (Jan 2024 – Dec 2025) ครอบคลุม 5 สาขาประเภทต่างกัน (office, mall,
community, university, transit) 29 SKU 7 หมวด รวม ~508,000 transactions
พร้อม pattern ที่ฝังไว้ในข้อมูล — peak เช้า, weekend/weekday differences,
weather impact, holidays, seasonal trend, bakery waste

รายละเอียดเต็มดูที่ [`mock_data/README.md`](mock_data/README.md)

---

## Running the dashboard

```bash
streamlit run notebooks/04_dashboard.py
```

Prerequisite: run notebook 03 first to generate `models/` artifacts.
The dashboard opens at `http://localhost:8501`.
## Roadmap

- [x] Mock data generation
- [x] PostgreSQL schema + ingestion pipeline
- [x] EDA — สำรวจข้อมูลและหา insight
- [x] Baseline forecast (moving average)
- [x] ML forecast (LightGBM with feature engineering)
- [x] Waste analysis และ business impact estimation
- [x] **[Full proposal →](proposal.md)**
