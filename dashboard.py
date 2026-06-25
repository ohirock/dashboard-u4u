import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from db import ANALYTICS_DB

st.set_page_config(page_title="U4U/TPS/EAD Analytics", layout="wide")
st.title("U4U / TPS / EAD Analytics Dashboard")
st.info(
    "Community-reported data from [@u4uead](https://t.me/u4uead). "
    "To post your own case update, use [@eadu4u](https://t.me/eadu4u)."
)

MIN_RECEIPT_DATE = pd.Timestamp("2023-01-01")
MAX_PROCESSING_DAYS = 1250
MAX_EVENT_DATE_DRIFT = pd.Timedelta(days=14)


@st.cache_data(ttl=300)
def load_cases() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(ANALYTICS_DB)
        df = pd.read_sql_query(
            "SELECT * FROM parsed_cases WHERE category = 'CASE_UPDATE'", conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_all_rows() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(ANALYTICS_DB)
        df = pd.read_sql_query("SELECT * FROM parsed_cases", conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def load_review() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(ANALYTICS_DB)
        df = pd.read_sql_query(
            "SELECT message_id, message_date, source_type, category, case_type, "
            "event_type, event_date, days_processing, confidence, raw_text, parse_error "
            "FROM parsed_cases WHERE confidence = 'low' OR parse_error IS NOT NULL",
            conn,
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()


df = load_cases()
all_df = load_all_rows()

def _format_dt(value) -> str:
    if pd.isna(value):
        return "N/A"
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert(None)
    return ts.strftime("%Y-%m-%d %H:%M")


if df.empty:
    st.warning("No case updates found. Run `python parser.py` first.")
    st.stop()

df["case_type"] = df["case_type"].replace({"I765": "EAD", "U4U": "REPAROLE"})
if not all_df.empty and "case_type" in all_df.columns:
    all_df["case_type"] = all_df["case_type"].replace({"I765": "EAD", "U4U": "REPAROLE"})

# Convert date columns to datetime
df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
df["receipt_date"] = pd.to_datetime(df["receipt_date"], errors="coerce")
df["permit_valid_until"] = pd.to_datetime(df["permit_valid_until"], errors="coerce")
if not all_df.empty:
    all_df["message_date"] = pd.to_datetime(all_df["message_date"], errors="coerce")
    all_df["parsed_at"] = pd.to_datetime(all_df["parsed_at"], errors="coerce")
    all_df["event_date"] = pd.to_datetime(all_df["event_date"], errors="coerce")
    all_df["receipt_date"] = pd.to_datetime(all_df["receipt_date"], errors="coerce")
    all_df["permit_valid_until"] = pd.to_datetime(
        all_df["permit_valid_until"], errors="coerce"
    )
    all_computed = (all_df["event_date"] - all_df["receipt_date"]).dt.days
    all_valid_days = (
        all_df["category"].eq("CASE_UPDATE")
        & all_df["receipt_date"].ge(MIN_RECEIPT_DATE)
        & all_computed.ge(0)
        & all_computed.le(MAX_PROCESSING_DAYS)
    )
    all_df["days_processing"] = all_computed.where(all_valid_days)
    all_old_event = all_df["event_date"].lt(MIN_RECEIPT_DATE)
    all_future_event = all_df["event_date"].gt(
        all_df["message_date"] + MAX_EVENT_DATE_DRIFT
    )
    invalid_all_timeline = (
        all_df["category"].ne("CASE_UPDATE") | all_old_event | all_future_event
    )
    all_df.loc[invalid_all_timeline, "event_date"] = pd.NaT
    all_df.loc[invalid_all_timeline, "days_processing"] = pd.NA

# Recompute days_processing for robustness
computed = (df["event_date"] - df["receipt_date"]).dt.days
valid_days = (
    df["receipt_date"].ge(MIN_RECEIPT_DATE)
    & computed.ge(0)
    & computed.le(MAX_PROCESSING_DAYS)
)
df["days_processing"] = computed.where(valid_days)

future_event = df["event_date"].gt(
    pd.to_datetime(df["message_date"], errors="coerce") + MAX_EVENT_DATE_DRIFT
)
old_event = df["event_date"].lt(MIN_RECEIPT_DATE)
invalid_timeline = old_event | future_event
df.loc[invalid_timeline, "event_date"] = pd.NaT
df.loc[invalid_timeline, "days_processing"] = pd.NA

# ── Sidebar filters ────────────────────────────────────────────────────────────
st.sidebar.header("Filters")

ALL_CASE_TYPES = ["TPS", "EAD", "REPAROLE", "ADVANCE_PAROLE", "ASYLUM"]
ALL_EVENT_TYPES = [
    "received",
    "biometrics",
    "pre_approved",
    "approved",
    "card_mailed",
    "rfe",
    "denied",
    "other",
]

sel_case_types = st.sidebar.multiselect("Case Type", ALL_CASE_TYPES, default=ALL_CASE_TYPES)
sel_event_types = st.sidebar.multiselect("Event Type", ALL_EVENT_TYPES, default=ALL_EVENT_TYPES)

valid_dates = df["event_date"].dropna()
if not valid_dates.empty:
    min_d = valid_dates.min().date()
    max_d = valid_dates.max().date()
    date_range = st.sidebar.date_input(
        "Event Date Range", value=(min_d, max_d), min_value=min_d, max_value=max_d
    )
else:
    date_range = None

st.sidebar.subheader("Confidence")
conf_high = st.sidebar.checkbox("High", value=True)
conf_med = st.sidebar.checkbox("Medium", value=True)
conf_low_cb = st.sidebar.checkbox("Low", value=True)
sel_confidence = [c for c, v in [("high", conf_high), ("medium", conf_med), ("low", conf_low_cb)] if v]

family_filter = st.sidebar.radio("Family Unit", ["All", "Individual only", "Family only"])

# ── Apply filters ──────────────────────────────────────────────────────────────
filtered = df.copy()
if sel_case_types:
    filtered = filtered[filtered["case_type"].isin(sel_case_types)]
if sel_event_types:
    filtered = filtered[filtered["event_type"].isin(sel_event_types)]
if date_range and len(date_range) == 2:
    filtered = filtered[
        (filtered["event_date"] >= pd.Timestamp(date_range[0]))
        & (filtered["event_date"] <= pd.Timestamp(date_range[1]))
    ]
if sel_confidence:
    filtered = filtered[filtered["confidence"].isin(sel_confidence)]
if family_filter == "Individual only":
    filtered = filtered[filtered["family_unit"] == 0]
elif family_filter == "Family only":
    filtered = filtered[filtered["family_unit"] == 1]

# ── Panel 1: KPI row ───────────────────────────────────────────────────────────
st.subheader("Data Freshness")
latest_message_date = (
    all_df["message_date"].max() if not all_df.empty else pd.NaT
)
latest_parsed_at = all_df["parsed_at"].max() if not all_df.empty else pd.NaT
try:
    db_modified_at = datetime.fromtimestamp(Path(ANALYTICS_DB).stat().st_mtime)
except OSError:
    db_modified_at = pd.NaT

f1, f2, f3 = st.columns(3)
f1.metric("Last Parsed Message", _format_dt(latest_message_date))
f2.metric("Parser Updated DB", _format_dt(latest_parsed_at))
f3.metric("DB File Updated", _format_dt(db_modified_at))

st.subheader("Overview")

approved_df = filtered[
    (filtered["event_type"] == "approved") & filtered["days_processing"].notna()
]
median_days = approved_df["days_processing"].median() if not approved_df.empty else None

now = pd.Timestamp.now()
approvals_30d = int(
    approved_df[approved_df["event_date"] >= now - pd.Timedelta(days=30)].shape[0]
)
pct_days = (
    filtered["days_processing"].notna().sum() / len(filtered) * 100
    if len(filtered) > 0
    else 0.0
)
unique_people = int(filtered["person_hash"].nunique())

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Case Updates", len(filtered))
c2.metric(
    "Median Processing Days",
    f"{median_days:.0f}" if median_days is not None else "N/A",
)
c3.metric("Approvals (Last 30d)", approvals_30d)
c4.metric("% with Days Data", f"{pct_days:.1f}%")
c5.metric("Unique Reporters", unique_people)

# ── Panel 2: Min/max coverage tables ──────────────────────────────────────────
st.subheader("Min / Max by Category and Status")

left, right = st.columns(2)
with left:
    st.caption("All parsed rows")
    if not all_df.empty:
        category_summary = (
            all_df.assign(category=all_df["category"].fillna("UNPARSED"))
            .groupby("category", dropna=False)
            .agg(
                rows=("message_id", "count"),
                min_message_date=("message_date", "min"),
                max_message_date=("message_date", "max"),
                min_event_date=("event_date", "min"),
                max_event_date=("event_date", "max"),
                min_days=("days_processing", "min"),
                max_days=("days_processing", "max"),
            )
            .reset_index()
            .sort_values("rows", ascending=False)
        )
        st.dataframe(category_summary, use_container_width=True, hide_index=True)
    else:
        st.info("No parsed rows available.")

with right:
    st.caption("Current filtered case updates")
    if not filtered.empty:
        status_summary = (
            filtered.assign(event_type=filtered["event_type"].fillna("unknown"))
            .groupby("event_type", dropna=False)
            .agg(
                rows=("message_id", "count"),
                min_event_date=("event_date", "min"),
                max_event_date=("event_date", "max"),
                min_days=("days_processing", "min"),
                max_days=("days_processing", "max"),
            )
            .reset_index()
            .sort_values("rows", ascending=False)
        )
        st.dataframe(status_summary, use_container_width=True, hide_index=True)
    else:
        st.info("No rows in current filter.")

# ── Panel 3: Approval histogram ────────────────────────────────────────────────
st.subheader("Processing Time Distribution (Final Approvals)")
if not approved_df.empty:
    bins = [0, 30, 60, 90, 120, 180, 365, 9999]
    labels = ["0-30", "31-60", "61-90", "91-120", "121-180", "181-365", "365+"]
    appr = approved_df.copy()
    appr["bucket"] = pd.cut(
        appr["days_processing"], bins=bins, labels=labels, right=True
    )
    fig2 = px.histogram(
        appr,
        x="bucket",
        color="case_type",
        category_orders={"bucket": labels},
        labels={"bucket": "Days to Approval", "count": "Cases"},
        title="Processing Time Distribution (Final Approvals)",
    )
    st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No final approved cases with processing days in current filter.")

# ── Panel 4: Weekly velocity ───────────────────────────────────────────────────
st.subheader("Weekly Event Velocity")
vel_df = filtered.dropna(subset=["event_date"]).copy()
vel_df = vel_df[vel_df["event_date"] >= pd.Timestamp("2024-01-01")]
if not vel_df.empty:
    vel_df = vel_df.set_index("event_date")
    weekly = (
        vel_df.groupby([pd.Grouper(freq="W"), "case_type"])
        .size()
        .reset_index(name="count")
    )
    fig3 = px.line(
        weekly,
        x="event_date",
        y="count",
        color="case_type",
        title="Weekly Event Velocity Since 2024",
        labels={"event_date": "Week", "count": "Events"},
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No events since 2024 with dates in current filter.")

# ── Panel 5: Event funnel per case type ───────────────────────────────────────
st.subheader("Event Funnel by Case Type")
funnel_order = ["received", "biometrics", "pre_approved", "approved", "card_mailed"]
funnel_df = (
    filtered[filtered["event_type"].isin(funnel_order)]
    .groupby(["case_type", "event_type"])
    .size()
    .reset_index(name="count")
)
if not funnel_df.empty:
    funnel_df["event_type"] = pd.Categorical(
        funnel_df["event_type"], categories=funnel_order, ordered=True
    )
    fig4 = px.bar(
        funnel_df,
        x="count",
        y="event_type",
        color="case_type",
        orientation="h",
        title="Event Funnel by Case Type",
        category_orders={"event_type": funnel_order},
        labels={"event_type": "Stage", "count": "Cases"},
    )
    st.plotly_chart(fig4, use_container_width=True)
else:
    st.info("No funnel-stage events in current filter.")

# ── Panel 6: Status heatmap ───────────────────────────────────────────────────
st.subheader("Case Type x Status Heatmap")
heat_df = filtered.copy()
if not heat_df.empty:
    heat_counts = (
        heat_df.groupby(["event_type", "case_type"])
        .size()
        .reset_index(name="count")
        .pivot(index="event_type", columns="case_type", values="count")
        .reindex(index=ALL_EVENT_TYPES)
        .fillna(0)
    )
    heat_counts = heat_counts.loc[(heat_counts.sum(axis=1) > 0)]
    if not heat_counts.empty:
        fig_heat = px.imshow(
            heat_counts,
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Blues",
            labels={"x": "Case Type", "y": "Status", "color": "Rows"},
            title="Case Type x Status Count",
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("No status counts in current filter.")
else:
    st.info("No rows in current filter.")

# ── Panel 7: Case type share over time ────────────────────────────────────────
st.subheader("Case Type Share Over Time")
area_df = filtered.dropna(subset=["event_date"]).copy()
if not area_df.empty:
    area_df = area_df.set_index("event_date")
    monthly = (
        area_df.groupby([pd.Grouper(freq="MS"), "case_type"])
        .size()
        .reset_index(name="count")
    )
    fig5 = px.area(
        monthly,
        x="event_date",
        y="count",
        color="case_type",
        title="Case Type Share Over Time",
        labels={"event_date": "Month", "count": "Events"},
    )
    fig5.update_xaxes(
        dtick="M1",
        tickformat="%b\n%Y",
        ticklabelmode="period",
        showgrid=True,
    )
    st.plotly_chart(fig5, use_container_width=True)
else:
    st.info("No events with dates in current filter.")

# ── Panel 8: Permit expiry distribution ───────────────────────────────────────
st.subheader("Permit Expiry Distribution")
expiry_df = filtered.dropna(subset=["permit_valid_until"]).copy()
if not expiry_df.empty:
    fig6 = px.histogram(
        expiry_df,
        x="permit_valid_until",
        color="case_type",
        nbins=36,
        title="Community Permit Expiry Cliff",
        labels={"permit_valid_until": "Expiry Date", "count": "Cases"},
    )
    st.plotly_chart(fig6, use_container_width=True)
else:
    st.info("No permit expiry dates in current filter.")

# ── Panel 9: Rolling 30-event median processing time ──────────────────────────
st.subheader("Rolling Median Processing Time (Final Approvals, 2024-2026)")
roll_df = (
    filtered[
        (filtered["event_type"] == "approved") & filtered["days_processing"].notna()
    ]
    .dropna(subset=["event_date"])
    .sort_values("event_date")
    .copy()
)
roll_df = roll_df[
    (roll_df["event_date"] >= pd.Timestamp("2024-01-01"))
    & (roll_df["event_date"] <= pd.Timestamp("2026-12-31"))
]
if len(roll_df) >= 5:
    roll_df["rolling_median"] = (
        roll_df["days_processing"].rolling(30, min_periods=5).median()
    )
    fig7 = px.line(
        roll_df,
        x="event_date",
        y="rolling_median",
        title="Rolling 30-Event Median Processing Time (Final Approvals, 2024-2026)",
        labels={"rolling_median": "Median Days", "event_date": "Date"},
    )
    st.plotly_chart(fig7, use_container_width=True)
else:
    st.info("Not enough 2024-2026 approved cases for rolling median (need 5+).")

# ── Panel 10: Person journey view ─────────────────────────────────────────────
st.subheader("Person Journey View")
journey_df = filtered[filtered["person_hash"].notna()].copy()
if not journey_df.empty:
    hash_counts = journey_df.groupby("person_hash").size()
    multi_hashes = hash_counts[hash_counts >= 2].index
    journey_df = journey_df[journey_df["person_hash"].isin(multi_hashes)]

    if not journey_df.empty:
        for phash, group in journey_df.groupby("person_hash"):
            group = group.sort_values("event_date")
            author = (
                group["post_author"].dropna().iloc[0]
                if group["post_author"].notna().any()
                else "Unknown"
            )
            with st.expander(f"{str(phash)[:6]} — {author} ({len(group)} events)"):
                display = group[
                    ["event_date", "case_type", "event_type", "days_processing"]
                ].copy()
                display["event_date"] = display["event_date"].dt.strftime("%Y-%m-%d")
                display.columns = ["Date", "Case Type", "Event", "Days Processing"]
                st.dataframe(display.reset_index(drop=True), use_container_width=True)
    else:
        st.info("No persons with 2+ events in current filter.")
else:
    st.info("No events with person identifiers in current filter.")

# ── Panel 11: Low confidence / error review ───────────────────────────────────
st.subheader("Review: Low Confidence & Parse Errors")
review_df = load_review()
if not review_df.empty:
    review_df = review_df.copy()
    review_df["event_date"] = pd.to_datetime(review_df["event_date"], errors="coerce")
    review_df["preview"] = review_df["raw_text"].fillna("").str[:120]
    review_df["review_priority"] = "Low confidence"
    review_df.loc[review_df["parse_error"].notna(), "review_priority"] = "Parse error"
    review_df.loc[
        (review_df["category"] == "CASE_UPDATE") & (review_df["confidence"] == "low"),
        "review_priority",
    ] = "Low-confidence case"

    r1, r2, r3 = st.columns(3)
    r1.metric("Rows to Review", len(review_df))
    r2.metric(
        "Low-Confidence Case Updates",
        int(
            review_df[
                (review_df["category"] == "CASE_UPDATE")
                & (review_df["confidence"] == "low")
            ].shape[0]
        ),
    )
    r3.metric("Parse Errors", int(review_df["parse_error"].notna().sum()))

    by_review = (
        review_df.groupby(["review_priority", "category", "case_type", "event_type"])
        .size()
        .reset_index(name="rows")
        .sort_values("rows", ascending=False)
    )
    st.dataframe(by_review, use_container_width=True, hide_index=True, height=260)

    detail = review_df[
        [
            "message_id",
            "message_date",
            "source_type",
            "review_priority",
            "category",
            "case_type",
            "event_type",
            "event_date",
            "days_processing",
            "preview",
            "parse_error",
        ]
    ].rename(
        columns={
            "message_id": "ID",
            "message_date": "Message Date",
            "source_type": "Source",
            "review_priority": "Priority",
            "category": "Category",
            "case_type": "Case",
            "event_type": "Status",
            "event_date": "Event Date",
            "days_processing": "Days",
            "preview": "Text (120 chars)",
            "parse_error": "Error",
        }
    )
    st.dataframe(detail, use_container_width=True, height=420, hide_index=True)

    case_review = review_df[
        (review_df["category"] == "CASE_UPDATE") & (review_df["confidence"] == "low")
    ].head(25)
    if not case_review.empty:
        with st.expander("Raw text for first 25 low-confidence case updates"):
            for _, row in case_review.iterrows():
                st.markdown(
                    f"**ID {row['message_id']}** | {row['case_type']} / {row['event_type']}"
                )
                st.text(row["raw_text"] or "")
else:
    st.success("No low-confidence rows or parse errors.")
