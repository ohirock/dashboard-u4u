"""Public Streamlit UI over the aggregate-only Oracle dashboard API."""

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from dashboard_data import (
    PublicDashboardUnavailable,
    bucket_rows,
    fetch_dashboard_snapshot,
    public_api_base_url,
    snapshot_age_hours,
)

st.set_page_config(
    page_title="USCIS Community Case Tracker",
    page_icon="📊",
    layout="wide",
)


def _secret_api_url() -> str | None:
    try:
        value = st.secrets.get("U4U_PUBLIC_API_BASE_URL")
    except (FileNotFoundError, KeyError, StreamlitSecretNotFoundError):
        return None
    return value if isinstance(value, str) else None


@st.cache_data(ttl=300, show_spinner=False)
def _load_snapshot(base_url: str):
    return fetch_dashboard_snapshot(base_url)


def _label(value: str) -> str:
    special = {
        "i_131": "I-131",
        "i_765": "I-765",
        "i_485": "I-485",
        "i_130": "I-130",
        "i_140": "I-140",
        "tps": "TPS",
        "u4u_initial": "U4U initial parole",
        "u4u_reparole": "U4U re-parole",
        "conditional_approval": "Conditional approval",
    }
    return special.get(value, value.replace("_", " ").title())


def _frame(buckets, key_label):
    frame = pd.DataFrame(bucket_rows(buckets, key_label=key_label))
    if not frame.empty and key_label not in {
        "Reported month",
        "Decision month",
    }:
        frame[key_label] = frame[key_label].map(_label)
    return frame


def _bar(buckets, *, key_label, title, horizontal=False):
    frame = _frame(buckets, key_label)
    if frame.empty:
        st.info("No data is available for this breakdown yet.")
        return
    if horizontal:
        figure = px.bar(
            frame,
            x="Count",
            y=key_label,
            orientation="h",
            title=title,
        )
    else:
        figure = px.bar(
            frame,
            x=key_label,
            y="Count",
            title=title,
        )
    st.plotly_chart(figure, width="stretch")


def _outcome_frame(with_expedite, without_expedite):
    rows = []
    for cohort, buckets in (
        ("Reported expedite", with_expedite),
        ("No reported expedite", without_expedite),
    ):
        rows.extend(
            {
                "Outcome": _label(bucket.key),
                "Count": bucket.count,
                "Cohort": cohort,
            }
            for bucket in buckets
        )
    return pd.DataFrame(rows)


st.title("USCIS Community Case Tracker")
st.caption("Aggregate trends from human-reviewed, self-reported Telegram case updates.")

try:
    api_base_url = public_api_base_url(
        os.environ,
        secret_value=_secret_api_url(),
    )
    snapshot = _load_snapshot(api_base_url)
except PublicDashboardUnavailable as error:
    st.error(str(error))
    st.info(
        "The public aggregate service is temporarily unavailable. "
        "No private case data is stored in this dashboard."
    )
    st.stop()

age_hours = snapshot_age_hours(snapshot)
freshness = snapshot.generated_at.strftime("%Y-%m-%d %H:%M UTC")
if age_hours > 24:
    st.warning(
        f"The latest aggregate snapshot is {age_hours:.0f} hours old ({freshness})."
    )
else:
    st.caption(f"Snapshot {snapshot.data_version} generated {freshness}.")

metrics = snapshot.metrics
quality = snapshot.quality
duration = metrics.filing_to_decision
review_total = metrics.historic_pending_count + metrics.historic_reviewed_count
review_percent = (
    metrics.historic_reviewed_count / review_total * 100 if review_total else 0.0
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Published / confirmed reports", metrics.report_count)
k2.metric(
    "Median filing-to-decision",
    (
        f"{duration.median_days:.0f} days"
        if duration.median_days is not None
        else "Not available"
    ),
)
k3.metric("Duration sample", duration.sample_size)
k4.metric("Reports with expedite", metrics.reports_with_expedite)
k5.metric("Historic review complete", f"{review_percent:.1f}%")

overview, cases, expedite, quality_tab = st.tabs(
    ("Timeline", "Cases", "Expedite", "Data quality")
)

with overview:
    left, right = st.columns(2)
    with left:
        _bar(
            metrics.reports_by_month,
            key_label="Reported month",
            title="Reports by reported month",
        )
    with right:
        _bar(
            metrics.decisions_by_month,
            key_label="Decision month",
            title="Decisions by decision month",
        )
    if duration.sample_size:
        st.subheader("Filing-to-decision distribution")
        d1, d2, d3 = st.columns(3)
        d1.metric(
            "First quartile",
            f"{duration.first_quartile_days:.0f} days",
        )
        d2.metric("Median", f"{duration.median_days:.0f} days")
        d3.metric(
            "Third quartile",
            f"{duration.third_quartile_days:.0f} days",
        )
        st.caption(
            f"Based on {duration.sample_size} reports containing both an "
            "explicit filing date and decision date."
        )

with cases:
    left, right = st.columns(2)
    with left:
        _bar(
            metrics.reports_by_form,
            key_label="Form",
            title="Reports by USCIS form",
        )
        _bar(
            metrics.reports_by_subtype,
            key_label="Case subtype",
            title="Reports by case subtype",
            horizontal=True,
        )
    with right:
        _bar(
            metrics.current_status_distribution,
            key_label="Current status",
            title="Current status distribution",
            horizontal=True,
        )
    st.subheader("Historic review progress")
    progress = pd.DataFrame(
        [
            {
                "State": "Reviewed",
                "Count": metrics.historic_reviewed_count,
            },
            {
                "State": "Pending",
                "Count": metrics.historic_pending_count,
            },
        ]
    )
    st.plotly_chart(
        px.bar(
            progress,
            x="State",
            y="Count",
            color="State",
            title="Historic review progress",
        ),
        width="stretch",
    )

with expedite:
    e1, e2, e3 = st.columns(3)
    e1.metric("Expedite requests", metrics.expedite_request_count)
    e2.metric("Reports with expedite", metrics.reports_with_expedite)
    e3.metric(
        "Requests per expedite report",
        (
            f"{metrics.expedite_request_count / metrics.reports_with_expedite:.2f}"
            if metrics.reports_with_expedite
            else "Not available"
        ),
    )
    left, right = st.columns(2)
    with left:
        _bar(
            metrics.expedite_by_channel,
            key_label="Channel",
            title="Reported expedite requests by channel",
            horizontal=True,
        )
    with right:
        outcomes = _outcome_frame(
            metrics.outcomes_with_expedite,
            metrics.outcomes_without_expedite,
        )
        if outcomes.empty:
            st.info("No outcome cohort data is available yet.")
        else:
            st.plotly_chart(
                px.bar(
                    outcomes,
                    x="Outcome",
                    y="Count",
                    color="Cohort",
                    barmode="group",
                    title="Outcomes by reported expedite cohort",
                ),
                width="stretch",
            )
    st.info(
        "The expedite comparison is descriptive. Self-reported correlation "
        "does not establish that an expedite request caused an outcome."
    )

with quality_tab:
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Included reports", quality.included_report_count)
    q2.metric("Excluded reports", quality.excluded_report_count)
    q3.metric("Unknown form", quality.unknown_form_count)
    q4.metric("Unknown status", quality.unknown_status_count)
    quality_rows = pd.DataFrame(
        [
            {
                "Quality signal": "Missing filed date",
                "Count": quality.reports_missing_filed_date,
            },
            {
                "Quality signal": "Missing decision date",
                "Count": quality.reports_missing_decision_date,
            },
            {
                "Quality signal": "Conflicting evidence",
                "Count": quality.conflicting_evidence_count,
            },
        ]
    )
    st.plotly_chart(
        px.bar(
            quality_rows,
            x="Quality signal",
            y="Count",
            title="Aggregate data-quality signals",
        ),
        width="stretch",
    )

st.divider()
st.subheader("How to interpret this dashboard")
st.markdown(
    """
- The source is self-reported community data, not a random sample of USCIS cases.
- Only human-confirmed historic reports and successfully published bot reports are counted.
- Dates and statuses can be incomplete even after review.
- Reported expedite activity and outcomes should not be interpreted as causal.
- No raw messages, images, receipt numbers, Telegram identifiers, or
  administrator identities are sent to this dashboard.
"""
)
