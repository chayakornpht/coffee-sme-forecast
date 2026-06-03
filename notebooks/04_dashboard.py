"""
Coffee SME — Operational Dashboard
Run from project root:
    streamlit run notebooks/04_dashboard.py

Prerequisite: run notebook 03 first to generate models/ and data_cache/ artifacts.
"""
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Coffee SME Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Paths (relative to this file's location)
# ---------------------------------------------------------------------------
HERE = Path(__file__).parent
MODELS_DIR = HERE.parent / "models"


# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------
@st.cache_resource
def get_engine():
    db_url = os.environ.get(
        "DB_URL",
        "postgresql://postgres:Cyk.2004@localhost:5432/coffee_sme",
    )
    return create_engine(db_url)


@st.cache_data(ttl=3600)
def load_predictions():
    """Test-set predictions with actual qty + ML/baseline forecasts."""
    path = MODELS_DIR / "test_predictions.parquet"
    if not path.exists():
        st.error(
            f"ไม่พบ {path} — กรุณารัน notebook 03 จนจบเพื่อสร้างไฟล์นี้ก่อน"
        )
        st.stop()
    return pd.read_parquet(path)


@st.cache_data(ttl=3600)
def load_products():
    return pd.read_sql("SELECT * FROM products ORDER BY product_id", get_engine())


@st.cache_data(ttl=3600)
def load_stores():
    return pd.read_sql("SELECT * FROM stores ORDER BY store_id", get_engine())


@st.cache_data(ttl=3600)
def load_waste_summary():
    """Per-(store, product) waste over the 2-year history."""
    return pd.read_sql(
        """
        WITH weekly_sales AS (
            SELECT 
                DATE_TRUNC('week', datetime)::date AS week,
                store_id, product_id,
                SUM(qty) AS sold
            FROM sales_transactions
            GROUP BY 1, 2, 3
        )
        SELECT 
            po.store_id,
            p.product_name,
            p.product_taxonomies AS category,
            SUM(po.qty_ordered) AS ordered,
            SUM(COALESCE(ws.sold, 0)) AS sold,
            SUM(po.qty_ordered - COALESCE(ws.sold, 0)) AS waste_units,
            ROUND(SUM((po.qty_ordered - COALESCE(ws.sold, 0)) * po.cost_per_unit)::numeric, 0) AS waste_baht,
            ROUND(100.0 * SUM(po.qty_ordered - COALESCE(ws.sold, 0)) 
                  / NULLIF(SUM(po.qty_ordered), 0), 1) AS waste_pct
        FROM purchasing_orders po
        JOIN products p ON p.product_id = po.product_id
        LEFT JOIN weekly_sales ws 
            ON ws.week = po.arrival_date 
           AND ws.store_id = po.store_id
           AND ws.product_id = po.product_id
        GROUP BY 1, 2, 3
        ORDER BY waste_baht DESC
    """,
        get_engine(),
    )


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
preds = load_predictions()
products = load_products()
stores = load_stores()
waste = load_waste_summary()

# ---------------------------------------------------------------------------
# Sidebar — filters
# ---------------------------------------------------------------------------
st.sidebar.title("Filters")

store_options = ["ทุกสาขา"] + sorted(stores["store_id"].tolist())
selected_store = st.sidebar.selectbox("สาขา", store_options)

category_options = ["ทุกหมวด"] + sorted(products["product_taxonomies"].unique().tolist())
selected_category = st.sidebar.selectbox("หมวด", category_options, index=category_options.index("bakery") if "bakery" in category_options else 0)

if selected_category != "ทุกหมวด":
    cat_products = products[products["product_taxonomies"] == selected_category]
else:
    cat_products = products
product_options = sorted(cat_products["product_name"].tolist())
selected_product = st.sidebar.selectbox("สินค้า", product_options)

selected_product_id = products.loc[products["product_name"] == selected_product, "product_id"].iloc[0]

st.sidebar.divider()
st.sidebar.caption("ℹ️ ข้อมูล demo จาก mock 2 ปี (Jan 2024 – Dec 2025)")
st.sidebar.caption("Test period: Dec 2025")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("☕ Coffee SME — Operational Dashboard")
st.caption(
    "Demand forecast & waste analytics · LightGBM model (+15.2% MAE improvement vs MA28 baseline)"
)

# ---------------------------------------------------------------------------
# KPI metrics row
# ---------------------------------------------------------------------------
bakery_waste_2yr = waste[waste["category"] == "bakery"]["waste_baht"].sum()
bakery_waste_per_month = bakery_waste_2yr / 24
savings_per_month = bakery_waste_per_month * 0.152
savings_per_year = savings_per_month * 12

overall_mae_ml = preds["err_ml"].mean()
overall_mae_baseline = preds["err_baseline"].mean()
improvement_pct = (overall_mae_baseline - overall_mae_ml) / overall_mae_baseline * 100

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Bakery waste / เดือน", f"฿{bakery_waste_per_month:,.0f}")
with col2:
    st.metric(
        "Savings ML / เดือน",
        f"฿{savings_per_month:,.0f}",
        delta=f"+{improvement_pct:.1f}%",
    )
with col3:
    st.metric("Savings / ปี (est.)", f"฿{savings_per_year:,.0f}")
with col4:
    st.metric(
        "MAE vs baseline",
        f"{overall_mae_ml:.2f}",
        delta=f"−{improvement_pct:.1f}%",
        delta_color="inverse",
    )

st.divider()

# ---------------------------------------------------------------------------
# Forecast chart
# ---------------------------------------------------------------------------
store_label = selected_store if selected_store != "ทุกสาขา" else "All stores"
st.subheader(f"📈 Forecast — {selected_product} · {store_label}")

filtered = preds.copy()
if selected_store != "ทุกสาขา":
    filtered = filtered[filtered["store_id"] == selected_store]
filtered = filtered[filtered["product_id"] == selected_product_id]

if len(filtered) == 0:
    st.warning("ไม่มีข้อมูลสำหรับการเลือกนี้")
else:
    plot_df = (
        filtered.groupby("date")
        .agg(actual=("qty_sold", "sum"), predicted=("pred_ml", "sum"))
        .reset_index()
        .sort_values("date")
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=plot_df["date"],
            y=plot_df["actual"],
            mode="lines+markers",
            name="Actual",
            line=dict(color="#185FA5", width=2.5),
            marker=dict(size=7),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df["date"],
            y=plot_df["predicted"],
            mode="lines+markers",
            name="Predicted (ML)",
            line=dict(color="#BA7517", width=2.5, dash="dash"),
            marker=dict(size=7),
        )
    )
    fig.update_layout(
        height=380,
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="",
        yaxis_title="Units sold per day",
        hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Per-selection MAE
    sel_mae_ml = filtered["err_ml"].mean()
    sel_mae_baseline = filtered["err_baseline"].mean()
    sel_improvement = (sel_mae_baseline - sel_mae_ml) / sel_mae_baseline * 100
    st.caption(
        f"MAE for this selection — ML: {sel_mae_ml:.2f} · Baseline: {sel_mae_baseline:.2f} · "
        f"Improvement: {sel_improvement:+.1f}%"
    )

st.divider()

# ---------------------------------------------------------------------------
# Two-column layout: Top waste table + Recommendations
# ---------------------------------------------------------------------------
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader("🎯 Top 10 waste — priority for forecast")
    top_waste = (
        waste.head(10)[["store_id", "product_name", "category", "waste_pct", "waste_baht"]]
        .copy()
        .rename(
            columns={
                "store_id": "Store",
                "product_name": "Product",
                "category": "Category",
                "waste_pct": "Waste %",
                "waste_baht": "Waste (฿, 2yr)",
            }
        )
    )
    top_waste["Waste (฿, 2yr)"] = top_waste["Waste (฿, 2yr)"].apply(
        lambda x: f"฿{x:,.0f}"
    )
    top_waste["Waste %"] = top_waste["Waste %"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(top_waste, hide_index=True, use_container_width=True)

with col_right:
    st.subheader("💡 Recommendations")

    # 1) Worst (store, product) overall
    worst = waste.head(1).iloc[0]
    st.markdown(f"**🎯 {worst['product_name']} ที่ {worst['store_id']}**")
    st.caption(
        f"เปลือง ฿{worst['waste_baht']:,.0f} ใน 2 ปี ({worst['waste_pct']:.1f}%) — "
        "เป้าหมาย Phase 1"
    )

    # 2) ML insight for current selection
    if len(filtered) > 0:
        recent_actual = plot_df["actual"].tail(7).mean()
        recent_pred = plot_df["predicted"].tail(7).mean()
        if recent_pred < recent_actual * 0.9:
            st.markdown(f"**📉 {selected_product}: ลด stock**")
            st.caption(
                f"Forecast {recent_pred:.0f} ชิ้น/วัน vs avg ปัจจุบัน {recent_actual:.0f}"
            )
        elif recent_pred > recent_actual * 1.1:
            st.markdown(f"**📈 {selected_product}: เพิ่ม stock**")
            st.caption(
                f"Forecast {recent_pred:.0f} ชิ้น/วัน vs avg ปัจจุบัน {recent_actual:.0f}"
            )
        else:
            st.markdown(f"**✓ {selected_product}: stock ปกติ**")
            st.caption(
                f"Forecast ใกล้เคียง avg ({recent_pred:.0f} vs {recent_actual:.0f})"
            )

    # 3) General operational rule
    st.markdown("**⚠️ วันหยุดสัปดาห์หน้า**")
    st.caption("ลด stock ที่ ST01/ST04 ลง 45% (office/university ตกหนัก)")

    # 4) Weather-based rule
    st.markdown("**🌧️ พยากรณ์ฝนพรุ่งนี้**")
    st.caption("ลด iced drinks 10% ทุกสาขา, เพิ่ม hot drinks 15%")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.caption(
    "Powered by LightGBM · Data refreshes every night at 02:00 · "
    "[GitHub repo →](https://github.com/chayakornpht/coffee-sme-forecast)"
)
