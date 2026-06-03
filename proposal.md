# Proposal: Demand Forecasting สำหรับร้านกาแฟ SME

> ลด waste 15% สำหรับร้านกาแฟ 5 สาขา ประหยัด ~฿84,000/ปี ด้วย ML-based demand forecasting

---

## 1. ปัญหาที่ลูกค้าเผชิญ

ร้านกาแฟ SME (สมมติ "ร้านลุงตี๋" 5 สาขาในกรุงเทพ) เผชิญปัญหาเดิมๆ ทุกวัน

- เบเกอรี่หมดอายุก่อนขายหมด → ทิ้งทุกเย็น
- บางวันของขาดสต็อก → ลูกค้าผิดหวัง
- เจ้าของสั่งของจาก "ความรู้สึก" ไม่ใช่ข้อมูล

**คำถามหลัก** — พรุ่งนี้ แต่ละสาขาควรเตรียมสินค้าแต่ละชนิดกี่ชิ้น เพื่อให้ขายหมดและไม่ขาด

---

## 2. ขอบเขตข้อมูล

| Source | Volume | Coverage |
|---|---|---|
| Sales transactions | 508,407 rows | 2024-2025 (24 เดือน) |
| Purchasing orders | 15,224 rows | 2 ปีเต็ม |
| Products / Stores | 29 SKU / 5 สาขา | All |
| Weather / Calendar | 731 / 731 days | รายวัน |

ข้อมูลทั้งหมด ingest เข้า PostgreSQL ด้วย pipeline ที่ reproducible — รันซ้ำได้ทุกเมื่อ

---

## 3. Key Insights จาก EDA

### 3.1 Bakery กิน waste 67% ของทั้งหมด

| Category | Waste cost (2 ปี) | สัดส่วน |
|---|---|---|
| **Bakery** | **฿1.11M** | **67%** |
| Coffee_hot | ฿196k | 12% |
| Sandwich | ฿133k | 8% |
| อื่นๆ | ฿221k | 13% |

**เบเกอรี่ทิ้ง 1 ใน 5 ชิ้น** (waste rate 20.9%) — เป็นเป้าหมายชัดของ Phase 1

### 3.2 แต่ละสาขามี "บุคลิก" ที่ต่างกันมาก

| Store | ประเภท | Pattern |
|---|---|---|
| ST01 | Office building | Weekday สูง, เสาร์อาทิตย์ตก 50% |
| ST02 | Mall | **กลับด้าน** — เสาร์อาทิตย์ peak |
| ST03 | Community | เรียบทุกวัน |
| ST04 | University | คล้าย office, ตามปฏิทินภาคเรียน |
| ST05 | Transit hub | Rush hour เช้า 7-8 โมง volume สูงสุด |

→ One-size-fits-all forecast ไม่ทำงาน ต้องเรียน pattern ต่อสาขา

### 3.3 External factor มีผลชัดเจน

- **ฝน** → ยอดรวม -15%, **พายุ** -35%
- **อุณหภูมิ ≥32°C** → iced share พุ่งจาก 25% → 49% (เกือบสองเท่า)
- **วันหยุด** → ทุกสาขาตก 40-50% **ยกเว้น mall** ที่เกือบปกติ

---

## 4. Solution: Demand Forecasting

### Approach
- **Algorithm**: LightGBM (industry standard สำหรับ tabular forecasting)
- **Granularity**: ระดับ store × product × day
- **Horizon**: ทำนาย 7 วันล่วงหน้า

### Features ที่ใช้

| Group | Examples |
|---|---|
| Temporal | day-of-week, month, week-of-year |
| Lag | yesterday, last week, 14d ago, 28d ago |
| Rolling | mean/std 7-day, 28-day |
| External | weather, temperature, holiday, payday |
| Categorical | store, product, store_type, category |

### Performance vs Baseline

| Metric | Baseline (MA 28-day) | LightGBM | Improvement |
|---|---|---|---|
| Overall MAE | 3.16 | 2.68 | **+15.2%** |
| **Bakery MAE** | **3.56** | **3.02** | **+15.2%** |
| Coffee_hot MAE | 4.74 | 3.80 | +19.8% |

**ทุกหมวดดีขึ้นหมด** — ML เรียน pattern จริง ไม่ใช่ overfit

---

## 5. Business Impact

| Metric | ปัจจุบัน | After ML |
|---|---|---|
| Bakery waste/เดือน | ฿46,000 | ฿39,000 |
| **Savings/เดือน** | — | **฿7,000** |
| **Savings/ปี** | — | **฿84,000** |

฿84,000/ปี เทียบเท่าเงินเดือนพนักงาน part-time 0.6 คน  
สำหรับ SME ที่ margin บาง — เป็นเงินจริงที่จับต้องได้

> **โดยที่ยังไม่ได้ tune hyperparameters เลย** มีโอกาสดันขึ้นอีก 3-5% ด้วยการปรับเล็กน้อย

---

## 6. Deliverables ที่ลูกค้าจะได้รับ

1. **Forecast model** ที่รัน batch ทุกคืน → ผลล่วงหน้า 7 วัน
2. **Operational dashboard** เปิดเช้าก่อนเปิดร้าน เห็นว่าแต่ละสาขาควรสั่งของอะไรกี่ชิ้น
3. **Monthly insight report** สรุปสาขาไหน performance ดี/แย่ พร้อม recommendation
4. **Reproducible pipeline** — ทุก experiment track ได้ผ่าน Git ตรวจสอบย้อนกลับได้

---

## 7. Roadmap

| Phase | Scope | Timeline | Estimated savings |
|---|---|---|---|
| **Phase 1** ✅ | Bakery demand forecast 5 สาขา | Done | **~฿84k/ปี** |
| Phase 2 | + Promotion uplift, customer churn | Q2-Q3 | +฿200k+/ปี |
| Phase 3 | + Dynamic pricing | Q4 | +฿100k+/ปี |

**Phase 1 → Phase 2 ใช้ infrastructure เดิม** — ไม่ต้องลงทุนใหม่

---

## 8. Tech Stack

**Python** + **PostgreSQL** + **LightGBM** + **pandas/scikit-learn**

ทำงานบนเครื่อง local ของลูกค้าได้ ไม่ต้องลงทุน cloud ตั้งแต่ต้น — เริ่มเล็กแล้วขยายตามผล

**Repository**: [github.com/chayakornpht/coffee-sme-forecast](https://github.com/chayakornpht/coffee-sme-forecast)

---

## 9. ทำไมโปรเจกต์นี้ defend ได้

- ✅ Business problem ชัด ตัวเลข impact วัดเป็นเงินได้
- ✅ Solution เริ่มจาก baseline → ML — เลือกเครื่องมือตามปัญหา ไม่ใช่เอาเครื่องมือมาก่อน
- ✅ All decisions backed by data — ไม่ใช่ assumption
- ✅ Phased delivery — ลูกค้าเห็นผลใน Phase 1 (1-2 เดือน) ก่อนตัดสินใจ Phase 2
- ✅ Code reproducible — ส่งต่อทีมต่อ หรือ audit ได้

---

## Appendix: Skill Criteria Mapping

| เกณฑ์ | สิ่งที่ตอบในโปรเจกต์ |
|---|---|
| การวางแผน | Phased roadmap 3 phases พร้อม impact estimate |
| การเลือก AI/ML solution | เริ่ม baseline → ML, อธิบายว่าทำไม LightGBM |
| MLOps concept | Idempotent pipeline, reproducible, version-controlled |
| ใช้ AI ช่วยทำงาน | ใช้ LLM ช่วยเขียน code/SQL, ตรวจ logic, ร่างเอกสาร |
