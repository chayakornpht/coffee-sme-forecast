# Data Ingestion

โหลด mock CSV เข้า PostgreSQL ในแบบที่รันซ้ำได้ ทุกครั้งที่รันสคริปต์นี้
database จะกลับมาอยู่ในสภาพเดียวกัน

---

## ทำไมเขียนเป็นสคริปต์แทน import ผ่าน GUI

ระหว่าง EDA และเทรน forecast model จะต้องลบ-โหลดข้อมูลใหม่หลายรอบ ทั้งตอน
ปรับ schema, ตอนเปลี่ยน mock generator, หรือลองเปลี่ยน feature engineering
แล้วอยากเริ่มจากศูนย์ การคลิก GUI ทุกรอบช้าและพลาดได้ง่าย (ลำดับโหลดผิด,
ลืม enable header, ลืมตารางใดตารางหนึ่ง)

สคริปต์ที่รันคำสั่งเดียวจบ ทำให้ analysis loop เร็วและไม่มี state เพี้ยน
และคนที่มาตรวจหรือต่อยอดงานนี้ reproduce ผลลัพธ์เดิมได้จากเครื่องของตัวเอง

---

## วิธีใช้

**1. ติดตั้ง dependency**

```bash
pip install -r requirements.txt
```

**2. เตรียม PostgreSQL** (ต้องมีอยู่แล้ว — local install หรือ Docker)

```bash
createdb coffee_sme
```

**3. ตั้งค่า environment variable** (หรือ copy `.env.example` เป็น `.env`)

```bash
export DB_URL='postgresql://postgres:yourpassword@localhost:5432/coffee_sme'
export DATA_DIR='../mock_data'   # path ไปที่โฟลเดอร์ CSV
```

**4. รัน**

```bash
python ingest.py
```

---

## Output ที่คาดหวัง

```
10:23:01 | INFO  | data dir: /path/to/mock_data
10:23:01 | INFO  | Pre-flight: validating CSV headers ...
10:23:01 | INFO  |   all CSVs ok.
10:23:01 | INFO  | Applying schema (drop & create) ...
10:23:01 | INFO  | Loading data ...
10:23:01 | INFO  |   products                 0.01s
10:23:01 | INFO  |   stores                   0.00s
10:23:01 | INFO  |   calendar                 0.02s
10:23:01 | INFO  |   weather                  0.02s
10:23:01 | INFO  |   purchasing_orders        0.31s
10:23:04 | INFO  |   sales_transactions       2.87s
10:23:04 | INFO  | Row counts:
10:23:04 | INFO  |   products                       29
10:23:04 | INFO  |   stores                          5
10:23:04 | INFO  |   calendar                      731
10:23:04 | INFO  |   weather                       731
10:23:04 | INFO  |   purchasing_orders          15,224
10:23:04 | INFO  |   sales_transactions        508,407
10:23:04 | INFO  | Done.
```

---

## Reset

อยากเริ่มใหม่ตั้งแต่ต้น แค่รันสคริปต์อีกครั้ง — มันจะ drop tables เก่าทิ้งและสร้างใหม่ทั้งหมด
ไม่ต้อง drop database หรือทำขั้นตอนอะไรเพิ่ม

---

## What this script does (และไม่ทำ)

**ทำ**

- ตรวจ CSV header ตรงกับ schema ก่อนแตะ database (fail-fast)
- DROP + CREATE ตารางใหม่ทุกครั้ง (idempotent)
- โหลดผ่าน `COPY FROM STDIN` ซึ่งเร็วกว่า INSERT ทีละแถวมาก สำหรับตาราง sales 500k แถว
  ใช้เวลาแค่ ~3 วินาที
- โหลดตามลำดับ foreign key dependency
- รายงานจำนวนแถวที่โหลดได้ ให้ตรวจสอบได้ง่าย

**ไม่ทำ**

- ไม่ทำ incremental load หรือ CDC (data ทั้งหมดเป็น static mock)
- ไม่ทำ schema migration (drop & recreate ตรงๆ ตามที่งานต้องการ)
- ไม่ทำ retry / failure recovery แบบ production (ใช้ในเครื่อง dev ของเรา ไม่ใช่ production)
