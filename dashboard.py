"""Public Streamlit UI over the aggregate-only Oracle dashboard API."""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

try:
    from dashboard_data import (
        PublicDashboardUnavailable,
        bucket_rows,
        fetch_dashboard_snapshot,
        public_api_base_url,
        snapshot_age_hours,
    )
except ModuleNotFoundError:
    from apps.streamlit.dashboard_data import (
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
        "ead": "EAD",
        "re_parole": "Re-parole",
        "u4u_initial": "U4U initial parole",
        "u4u_reparole": "U4U re-parole",
        "pre_approval": "Pre-approval",
        "biometrics": "Biometrics",
        "approval": "Approval",
        "decision": "Final decision",
        "adjustment_of_status": "Adjustment of status",
    }
    return special.get(value, value.replace("_", " ").title())


def _frame(buckets, key_label):
    frame = pd.DataFrame(bucket_rows(buckets, key_label=key_label))
    if not frame.empty and key_label not in {"Reported month", "Decision month"}:
        frame[key_label] = frame[key_label].map(_label)
    return frame


def _bar(buckets, *, key_label, title, horizontal=False):
    frame = _frame(buckets, key_label)
    if frame.empty:
        st.info("No data is available for this breakdown yet.")
        return
    figure = px.bar(
        frame,
        x="Count" if horizontal else key_label,
        y=key_label if horizontal else "Count",
        orientation="h" if horizontal else "v",
        title=title,
    )
    st.plotly_chart(figure, width="stretch")


def _days(value: float | None) -> str:
    return f"{value:.0f} days" if value is not None else "Not available"


def _milestone_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Case type": _label(row.case_family),
                "Milestone": _label(row.milestone),
                "Average days": row.duration.average_days,
                "Median days": row.duration.median_days,
                "25th percentile": row.duration.first_quartile_days,
                "75th percentile": row.duration.third_quartile_days,
                "Cases": row.duration.sample_size,
            }
            for row in rows
        ]
    )


def _weekly_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Week": row.week_start,
                "Case type": _label(row.case_family),
                "Milestone": _label(row.milestone),
                "Average days": row.duration.average_days,
                "Median days": row.duration.median_days,
                "Cases": row.duration.sample_size,
            }
            for row in rows
        ]
    )


def _pace_signals(rows) -> pd.DataFrame:
    grouped: dict[tuple[str, str], list] = {}
    for row in rows:
        grouped.setdefault((row.case_family, row.milestone), []).append(row)
    signals = []
    for (family, milestone), values in sorted(grouped.items()):
        ordered = sorted(values, key=lambda value: value.week_start)
        if len(ordered) < 2 or ordered[-1].duration.median_days is None:
            continue
        latest = ordered[-1]
        baseline_rows = ordered[-5:-1]
        baseline_weight = sum(row.duration.sample_size for row in baseline_rows)
        if not baseline_weight:
            continue
        baseline = (
            sum((row.duration.median_days or 0) * row.duration.sample_size for row in baseline_rows)
            / baseline_weight
        )
        if baseline <= 0:
            continue
        change = ((latest.duration.median_days or 0) - baseline) / baseline * 100
        signal = "Slower" if change > 15 else "Faster" if change < -15 else "Stable"
        signals.append(
            {
                "Case type": _label(family),
                "Milestone": _label(milestone),
                "Latest week": latest.week_start,
                "Latest median": latest.duration.median_days,
                "Prior-week baseline": baseline,
                "Change": f"{change:+.0f}%",
                "Signal": signal,
                "Latest cases": latest.duration.sample_size,
            }
        )
    return pd.DataFrame(signals)


def _expedite_frame(rows) -> pd.DataFrame:
    result = []
    for row in rows:
        with_value = row.with_expedite
        without_value = row.without_expedite
        difference = (
            with_value.median_days - without_value.median_days
            if with_value.median_days is not None and without_value.median_days is not None
            else None
        )
        result.append(
            {
                "Case type": _label(row.case_family),
                "Milestone": _label(row.milestone),
                "Expedite median": with_value.median_days,
                "Expedite average": with_value.average_days,
                "Expedite cases": with_value.sample_size,
                "No expedite median": without_value.median_days,
                "No expedite average": without_value.average_days,
                "No expedite cases": without_value.sample_size,
                "Median difference": difference,
            }
        )
    return pd.DataFrame(result)


def _decision_summary(rows, family: str):
    return next(
        (row.duration for row in rows if row.case_family == family and row.milestone == "decision"),
        None,
    )


def _decision_heatmap(rows, family: str) -> None:
    labels = {False: "No reported expedite", True: "Reported expedite"}
    frame = pd.DataFrame(
        [
            {
                "Month": row.month_start.strftime("%Y-%m"),
                "Expedite": labels[row.with_expedite],
                "Median days": row.duration.median_days,
                "Cases": row.duration.sample_size,
            }
            for row in rows
            if row.case_family == family
        ]
    )
    title = f"{_label(family)} filing-to-final-decision speed"
    if frame.empty:
        st.info(f"No monthly {_label(family)} decision samples are available yet.")
        return
    order = [labels[False], labels[True]]
    medians = frame.pivot(index="Expedite", columns="Month", values="Median days").reindex(order)
    samples = frame.pivot(index="Expedite", columns="Month", values="Cases").reindex(
        index=order,
        columns=medians.columns,
    )
    figure = go.Figure(
        data=go.Heatmap(
            z=medians.to_numpy(),
            x=list(medians.columns),
            y=list(medians.index),
            customdata=samples.to_numpy(),
            colorscale="RdYlGn_r",
            colorbar={"title": "Median days"},
            hovertemplate=(
                "Decision month: %{x}<br>%{y}<br>Median: %{z:.0f} days"
                "<br>Cases: %{customdata}<extra></extra>"
            ),
        )
    )
    figure.update_layout(title=title, height=320, margin={"l": 20, "r": 20, "t": 60, "b": 20})
    st.plotly_chart(figure, width="stretch")


st.title("USCIS Community Case Tracker")
st.caption("Processing-time trends from human-reviewed, self-reported case updates.")

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
    st.warning(f"The latest snapshot is {age_hours:.0f} hours old ({freshness}).")
else:
    st.caption(f"Snapshot {snapshot.data_version} generated {freshness}.")

metrics = snapshot.metrics
quality = snapshot.quality
decisions = metrics.final_decisions
reparole_decision = _decision_summary(metrics.milestone_durations, "re_parole")
ead_decision = _decision_summary(metrics.milestone_durations, "ead")

summary_1, summary_2, summary_3 = st.columns(3)
summary_1.metric("Case observations", metrics.case_observation_count)
summary_2.metric("Final decisions this week", decisions.current_calendar_week)
summary_3.metric("Final decisions this month", decisions.current_calendar_month)

st.subheader("Filing to final decision by benefit")
r1, r2, r3, e1, e2, e3 = st.columns(6)
r1.metric("Re-parole average", _days(reparole_decision.average_days if reparole_decision else None))
r2.metric("Re-parole median", _days(reparole_decision.median_days if reparole_decision else None))
r3.metric("Re-parole cases", reparole_decision.sample_size if reparole_decision else 0)
e1.metric("EAD average", _days(ead_decision.average_days if ead_decision else None))
e2.metric("EAD median", _days(ead_decision.median_days if ead_decision else None))
e3.metric("EAD cases", ead_decision.sample_size if ead_decision else 0)

speed_tab, cases_tab, expedite_tab, quality_tab = st.tabs(
    ("Processing speed", "Cases", "Expedite impact", "Data quality")
)

with speed_tab:
    st.subheader("Recent final decisions")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Last 7 days", decisions.last_7_days)
    d2.metric("Previous calendar week", decisions.previous_calendar_week)
    d3.metric("Current week", decisions.current_calendar_week)
    d4.metric("Current month", decisions.current_calendar_month)

    summary = _milestone_frame(metrics.milestone_durations)
    if not summary.empty:
        summary = summary[summary["Milestone"] != "Approval"]
    st.subheader("Typical time from filing")
    if summary.empty:
        st.info("No complete filing-to-milestone samples are available yet.")
    else:
        preferred = ["TPS", "Re-parole", "EAD"]
        order = {name: index for index, name in enumerate(preferred)}
        summary["_order"] = summary["Case type"].map(lambda value: order.get(value, len(order)))
        summary = summary.sort_values(["_order", "Case type", "Milestone"])
        st.dataframe(summary.drop(columns="_order"), hide_index=True, width="stretch")

    weekly = _weekly_frame(metrics.weekly_milestone_durations)
    if not weekly.empty:
        weekly = weekly[weekly["Milestone"] != "Approval"]
    st.subheader("Weekly processing-time trend")
    if weekly.empty:
        st.info("Weekly trends will appear when dated milestones are available.")
    else:
        families = list(dict.fromkeys(weekly["Case type"]))
        default_family = next(
            (name for name in ("Re-parole", "TPS", "EAD") if name in families),
            families[0],
        )
        c1, c2 = st.columns(2)
        family = c1.selectbox(
            "Case type",
            families,
            index=families.index(default_family),
        )
        milestones = list(dict.fromkeys(weekly.loc[weekly["Case type"] == family, "Milestone"]))
        milestone = c2.selectbox("Milestone", milestones)
        selected = weekly[(weekly["Case type"] == family) & (weekly["Milestone"] == milestone)]
        trend = selected.melt(
            id_vars=["Week", "Cases"],
            value_vars=["Average days", "Median days"],
            var_name="Measure",
            value_name="Days",
        )
        figure = px.line(
            trend,
            x="Week",
            y="Days",
            color="Measure",
            markers=True,
            hover_data=["Cases"],
            title=f"{family}: filing to {milestone.lower()}",
        )
        st.plotly_chart(figure, width="stretch")
        st.caption(
            "A rising line means recently reported cases took longer. "
            "Hover over each point to see the sample size."
        )

        signals = _pace_signals(metrics.weekly_milestone_durations)
        st.subheader("Recent pace signals")
        if signals.empty:
            st.info("At least two populated weeks are needed to flag a change.")
        else:
            st.dataframe(signals, hide_index=True, width="stretch")
            st.caption(
                "Signals compare the latest populated week with up to four prior "
                "populated weeks. A change beyond 15% is flagged descriptively."
            )

    left, right = st.columns(2)
    with left:
        _bar(
            metrics.reports_by_month,
            key_label="Reported month",
            title="Reports by month",
        )
    with right:
        _bar(
            metrics.decisions_by_month,
            key_label="Decision month",
            title="Final decisions by month",
        )

with cases_tab:
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

with expedite_tab:
    comparison = _expedite_frame(metrics.expedite_duration_comparisons)
    if not comparison.empty:
        comparison = comparison[
            comparison["Case type"].isin(["Re-parole", "EAD"])
            & (comparison["Milestone"] == "Final decision")
        ]
    st.subheader("Processing time with and without reported expedite")
    if comparison.empty:
        st.info("No complete expedite comparison samples are available yet.")
    else:
        st.dataframe(comparison, hide_index=True, width="stretch")
    heatmap_left, heatmap_right = st.columns(2)
    with heatmap_left:
        _decision_heatmap(metrics.monthly_decision_durations, "re_parole")
    with heatmap_right:
        _decision_heatmap(metrics.monthly_decision_durations, "ead")
    st.caption(
        "Each cell is the median time from the reported initial filing date to a final "
        "approval or denial, grouped by decision month. Empty cells have no complete sample."
    )
    e1, e2 = st.columns(2)
    e1.metric("Reported expedite requests", metrics.expedite_request_count)
    e2.metric("Reports with expedite", metrics.reports_with_expedite)
    _bar(
        metrics.expedite_by_channel,
        key_label="Channel",
        title="Reported expedite requests by channel",
        horizontal=True,
    )
    st.info(
        "This comparison is descriptive. Expedite cases may differ in urgency, "
        "evidence, timing, or other factors; correlation does not prove causation."
    )

with quality_tab:
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Included reports", quality.included_report_count)
    q2.metric("Excluded reports", quality.excluded_report_count)
    q3.metric("Unknown form", quality.unknown_form_count)
    q4.metric("Unknown status", quality.unknown_status_count)
    review_total = metrics.historic_pending_count + metrics.historic_reviewed_count
    review_percent = metrics.historic_reviewed_count / review_total * 100 if review_total else 0.0
    st.metric("Historic review complete", f"{review_percent:.1f}%")
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
- A multi-person report contributes its reported number of cases to processing samples.
- Only human-confirmed historic reports and successfully published bot reports are counted.
- Averages and medians use only records with explicit, non-conflicting dates.
- Weekly spikes can be noisy when the displayed sample is small.
- No raw messages, images, receipt numbers, Telegram identifiers, or
  administrator identities are sent to this dashboard.
"""
)
