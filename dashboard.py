"""Public Streamlit UI over the aggregate-only Oracle dashboard API."""

import os
from datetime import UTC, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from plotly.subplots import make_subplots
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

# Imported separately and defensively: a stale hosting-platform code cache
# that hasn't picked up a new name in dashboard_data yet must degrade this
# one optional tab, never crash the whole page.
try:
    from dashboard_data import fetch_personal_dashboard_snapshot
except ImportError:
    try:
        from apps.streamlit.dashboard_data import fetch_personal_dashboard_snapshot
    except ImportError:
        fetch_personal_dashboard_snapshot = None

from i18n import WINDOW_ORDER, label, render_language_selector, t, window_label

st.set_page_config(
    page_title="USCIS Community Case Tracker",
    page_icon="📊",
    layout="wide",
)

# Single shared cadence for every cached data source on this page (the
# canonical snapshot and the personal-tracking snapshot alike), so there is
# one consistent number instead of two different ones to reconcile.
PAGE_DATA_CACHE_TTL_SECONDS = 300


def _secret_api_url() -> str | None:
    try:
        value = st.secrets.get("U4U_PUBLIC_API_BASE_URL")
    except (FileNotFoundError, KeyError, StreamlitSecretNotFoundError):
        return None
    return value if isinstance(value, str) else None


@st.cache_data(ttl=PAGE_DATA_CACHE_TTL_SECONDS, show_spinner=False)
def _load_snapshot(base_url: str):
    """Return (snapshot, fetched_at).

    `st.cache_data` is a server-wide cache shared by every visitor, not a
    per-browser-session value — `fetched_at` is captured once, when this
    cache entry is (re)populated, so the same value and countdown are seen
    by all concurrent users and survive any single user's manual refresh.
    """

    return fetch_dashboard_snapshot(base_url), datetime.now(UTC)


@st.cache_data(ttl=PAGE_DATA_CACHE_TTL_SECONDS, show_spinner=False)
def _load_personal_snapshot(base_url: str):
    """Return (snapshot_or_none, fetched_at); see `_load_snapshot` above."""

    snapshot = None if fetch_personal_dashboard_snapshot is None else fetch_personal_dashboard_snapshot(base_url)
    return snapshot, datetime.now(UTC)


def _render_refresh_countdown(fetched_at: datetime) -> None:
    """A purely informational, repeating countdown.

    Communicates the underlying shared cache's refresh cadence — it never
    reloads or reruns the page. Reopen the page after it reaches zero to
    see whether new data arrived. `fetched_at` reflects when the server-wide
    cache was last populated, so this countdown is identical for every
    visitor at any given moment, not reset by one user's page reload.
    """

    period_seconds = PAGE_DATA_CACHE_TTL_SECONDS
    next_refresh_at = fetched_at + timedelta(seconds=period_seconds)
    components.html(
        f"""
        <div style="font-family:'Source Sans Pro',sans-serif;font-size:0.8rem;
                     color:gray;">
        {t("refresh_countdown_before")}
        <span id="page-data-countdown">{period_seconds}s</span>
        {t("refresh_countdown_after")}
        </div>
        <script>
        (function() {{
            let target = new Date("{next_refresh_at.isoformat()}").getTime();
            const periodMs = {period_seconds} * 1000;
            const el = document.getElementById("page-data-countdown");
            function tick() {{
                let remaining = Math.round((target - Date.now()) / 1000);
                while (remaining <= 0) {{
                    target += periodMs;
                    remaining = Math.round((target - Date.now()) / 1000);
                }}
                el.textContent = remaining + "s";
            }}
            tick();
            setInterval(tick, 1000);
        }})();
        </script>
        """,
        height=24,
    )


def _label(value: str) -> str:
    return label(value)


def _frame(buckets, key_label):
    frame = pd.DataFrame(bucket_rows(buckets, key_label=key_label))
    if frame.empty:
        return frame
    frame = frame.rename(columns={"Count": t("column_count")})
    if key_label not in {t("column_reported_month"), t("column_decision_month")}:
        frame[key_label] = frame[key_label].map(_label)
    return frame


def _bar(buckets, *, key_label, title, horizontal=False):
    frame = _frame(buckets, key_label)
    if frame.empty:
        st.info(t("info_no_breakdown_data"))
        return
    figure = px.bar(
        frame,
        x=t("column_count") if horizontal else key_label,
        y=key_label if horizontal else t("column_count"),
        orientation="h" if horizontal else "v",
        title=title,
    )
    st.plotly_chart(figure, width="stretch")


def _days(value: float | None) -> str:
    return t("days_value", value=value) if value is not None else t("days_not_available")


def _milestone_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                t("column_case_type"): _label(row.case_family),
                t("column_milestone"): _label(row.milestone),
                t("column_average_days"): row.duration.average_days,
                t("column_median_days"): row.duration.median_days,
                t("column_first_quartile"): row.duration.first_quartile_days,
                t("column_third_quartile"): row.duration.third_quartile_days,
                t("column_cases"): row.duration.sample_size,
            }
            for row in rows
        ]
    )


def _weekly_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                t("column_week"): row.week_start,
                t("column_case_type"): _label(row.case_family),
                t("column_milestone"): _label(row.milestone),
                t("column_average_days"): row.duration.average_days,
                t("column_median_days"): row.duration.median_days,
                t("column_cases"): row.duration.sample_size,
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
            sum(
                (row.duration.median_days or 0) * row.duration.sample_size
                for row in baseline_rows
            )
            / baseline_weight
        )
        if baseline <= 0:
            continue
        change = ((latest.duration.median_days or 0) - baseline) / baseline * 100
        signal = (
            t("signal_slower")
            if change > 15
            else t("signal_faster")
            if change < -15
            else t("signal_stable")
        )
        signals.append(
            {
                t("column_case_type"): _label(family),
                t("column_milestone"): _label(milestone),
                t("column_latest_week"): latest.week_start,
                t("column_latest_median"): latest.duration.median_days,
                t("column_prior_baseline"): baseline,
                t("column_change"): f"{change:+.0f}%",
                t("column_signal"): signal,
                t("column_latest_cases"): latest.duration.sample_size,
            }
        )
    return pd.DataFrame(signals)


def _rolling_pace_signal(
    values: list[float | None],
    weights: list[float],
    *,
    baseline_window: int = 4,
    threshold_percent: float = 15,
) -> list[tuple[str | None, float | None]]:
    """Per-point Slower/Faster/Stable vs. the weighted average of up to
    `baseline_window` preceding points. (None, None) where there isn't yet
    enough baseline to compare against.
    """
    results: list[tuple[str | None, float | None]] = []
    for index, value in enumerate(values):
        baseline_values = values[max(0, index - baseline_window) : index]
        baseline_weights = weights[max(0, index - baseline_window) : index]
        baseline_weight = sum(
            weight
            for weight, baseline_value in zip(baseline_weights, baseline_values)
            if baseline_value is not None
        )
        if value is None or not baseline_weight:
            results.append((None, None))
            continue
        baseline = (
            sum(
                (baseline_value or 0) * weight
                for weight, baseline_value in zip(baseline_weights, baseline_values)
            )
            / baseline_weight
        )
        if baseline <= 0:
            results.append((None, None))
            continue
        change = (value - baseline) / baseline * 100
        signal = (
            t("signal_slower")
            if change > threshold_percent
            else t("signal_faster")
            if change < -threshold_percent
            else t("signal_stable")
        )
        results.append((signal, change))
    return results


def _decision_series(weekly_rows, family: str, *, monthly: bool) -> pd.DataFrame:
    """Filing-to-decision volume and duration for one case family.

    Monthly points are a `Cases`-weighted average of the underlying weekly
    `average_days` (medians of medians would be wrong to combine); weekly
    points use the exact weekly median directly.
    """
    filtered = [
        row
        for row in weekly_rows
        if row.case_family == family and row.milestone == "decision" and row.duration.sample_size
    ]
    if not filtered:
        return pd.DataFrame(columns=["Period", "Cases", "Days"])
    if not monthly:
        frame = pd.DataFrame(
            [
                {
                    "Period": row.week_start,
                    "Cases": row.duration.sample_size,
                    "Days": row.duration.median_days,
                }
                for row in filtered
            ]
        )
        return frame.sort_values("Period").reset_index(drop=True)
    raw = pd.DataFrame(
        [
            {
                "Period": pd.Timestamp(row.week_start).to_period("M").to_timestamp(),
                "Cases": row.duration.sample_size,
                "WeightedDays": (row.duration.average_days or 0) * row.duration.sample_size,
            }
            for row in filtered
        ]
    )
    grouped = raw.groupby("Period", as_index=False).agg(
        Cases=("Cases", "sum"), WeightedDays=("WeightedDays", "sum")
    )
    grouped["Days"] = grouped["WeightedDays"] / grouped["Cases"]
    return grouped.drop(columns="WeightedDays").sort_values("Period").reset_index(drop=True)


def _decision_combo_chart(
    frame: pd.DataFrame,
    *,
    title: str,
    duration_label: str,
) -> pd.DataFrame | None:
    """Render a volume+duration combo chart with spikes marked on the line.

    Returns a table of flagged (Slower/Faster) periods for the caller to fold
    into a shared summary table, or `None` when there's nothing to flag.
    """
    if frame.empty:
        st.info(t("no_recent_decisions_for", title=title))
        return None
    signals = _rolling_pace_signal(list(frame["Days"]), list(frame["Cases"]))
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    figure.add_bar(
        x=frame["Period"],
        y=frame["Cases"],
        name=t("decisions_series_name"),
        opacity=0.35,
        secondary_y=False,
    )
    figure.add_scatter(
        x=frame["Period"],
        y=frame["Days"],
        name=duration_label,
        mode="lines+markers",
        secondary_y=True,
    )
    marker_style = {
        t("signal_slower"): {"color": "#d62728", "symbol": "triangle-up"},
        t("signal_faster"): {"color": "#2ca02c", "symbol": "triangle-down"},
    }
    flagged_rows = []
    for signal_name, style in marker_style.items():
        points = [
            (period, days, change)
            for period, days, (signal, change) in zip(frame["Period"], frame["Days"], signals)
            if signal == signal_name
        ]
        if not points:
            continue
        xs, ys, changes = zip(*points)
        figure.add_scatter(
            x=list(xs),
            y=list(ys),
            mode="markers",
            name=signal_name,
            marker={**style, "size": 12},
            secondary_y=True,
        )
        flagged_rows.extend(
            {
                t("column_period"): period,
                t("column_days"): days,
                t("column_signal"): signal_name,
                t("column_change"): f"{change:+.0f}%",
            }
            for period, days, change in zip(xs, ys, changes)
        )
    figure.update_layout(
        title=title,
        height=320,
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        legend={"orientation": "h"},
    )
    figure.update_yaxes(title_text=t("yaxis_decisions"), secondary_y=False)
    figure.update_yaxes(title_text=duration_label, secondary_y=True)
    st.plotly_chart(figure, width="stretch")
    if not flagged_rows:
        return None
    return pd.DataFrame(flagged_rows).sort_values(t("column_period"))


def _filed_cohort_frame(cohorts) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                t("column_filed_month"): row.filed_month.strftime("%Y-%m"),
                t("column_case_type"): _label(row.case_family),
                t("column_count"): row.count,
            }
            for row in sorted(cohorts, key=lambda row: row.filed_month)
        ]
    )


def _expedite_frame(rows) -> pd.DataFrame:
    result = []
    for row in rows:
        with_value = row.with_expedite
        without_value = row.without_expedite
        difference = (
            with_value.median_days - without_value.median_days
            if with_value.median_days is not None
            and without_value.median_days is not None
            else None
        )
        result.append(
            {
                t("column_case_type"): _label(row.case_family),
                t("column_milestone"): _label(row.milestone),
                t("column_expedite_median"): with_value.median_days,
                t("column_expedite_average"): with_value.average_days,
                t("column_expedite_cases"): with_value.sample_size,
                t("column_no_expedite_median"): without_value.median_days,
                t("column_no_expedite_average"): without_value.average_days,
                t("column_no_expedite_cases"): without_value.sample_size,
                t("column_median_difference"): difference,
            }
        )
    return pd.DataFrame(result)


def _decision_summary(rows, family: str):
    return next(
        (
            row.duration
            for row in rows
            if row.case_family == family and row.milestone == "decision"
        ),
        None,
    )


def _decision_heatmap(rows, family: str) -> None:
    labels = {False: t("heatmap_no_expedite"), True: t("heatmap_expedite")}
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
    title = t("heatmap_title", family=_label(family))
    if frame.empty:
        st.info(t("heatmap_no_samples", family=_label(family)))
        return
    order = [labels[False], labels[True]]
    medians = frame.pivot(
        index="Expedite", columns="Month", values="Median days"
    ).reindex(order)
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
            colorbar={"title": t("heatmap_colorbar_title")},
            hovertemplate=t("heatmap_hovertemplate"),
        )
    )
    figure.update_layout(
        title=title, height=320, margin={"l": 20, "r": 20, "t": 60, "b": 20}
    )
    st.plotly_chart(figure, width="stretch")


_lang_col, _ = st.columns([1, 5])
with _lang_col:
    render_language_selector()

st.title(t("title"))
st.caption(t("subtitle"))

try:
    api_base_url = public_api_base_url(
        os.environ,
        secret_value=_secret_api_url(),
    )
    snapshot, canonical_fetched_at = _load_snapshot(api_base_url)
except PublicDashboardUnavailable as error:
    st.error(str(error))
    st.info(t("api_unavailable_info"))
    st.stop()

# Loaded once here (not inside the personal tab) so one global countdown can
# cover every cached data source on the page, including the personal tab's.
personal_snapshot, personal_fetched_at = _load_personal_snapshot(api_base_url)
_render_refresh_countdown(min(canonical_fetched_at, personal_fetched_at))

age_hours = snapshot_age_hours(snapshot)
freshness = snapshot.generated_at.strftime("%Y-%m-%d %H:%M UTC")
if age_hours > 24:
    st.warning(t("snapshot_stale", hours=age_hours, freshness=freshness))
else:
    st.caption(t("snapshot_fresh", version=snapshot.data_version, freshness=freshness))

metrics = snapshot.metrics
quality = snapshot.quality
decisions = metrics.final_decisions
reparole_decision = _decision_summary(metrics.milestone_durations, "re_parole")
ead_decision = _decision_summary(metrics.milestone_durations, "ead")

summary_1, summary_2, summary_3 = st.columns(3)
summary_1.metric(t("metric_case_observations"), metrics.case_observation_count)
summary_2.metric(t("metric_decisions_this_week"), decisions.current_calendar_week)
summary_3.metric(t("metric_decisions_this_month"), decisions.current_calendar_month)

st.subheader(t("subheader_filing_to_decision"))
r1, r2, r3, e1, e2, e3 = st.columns(6)
r1.metric(
    t("metric_reparole_average"),
    _days(reparole_decision.average_days if reparole_decision else None),
)
r2.metric(
    t("metric_reparole_median"),
    _days(reparole_decision.median_days if reparole_decision else None),
)
r3.metric(t("metric_reparole_cases"), reparole_decision.sample_size if reparole_decision else 0)
e1.metric(t("metric_ead_average"), _days(ead_decision.average_days if ead_decision else None))
e2.metric(t("metric_ead_median"), _days(ead_decision.median_days if ead_decision else None))
e3.metric(t("metric_ead_cases"), ead_decision.sample_size if ead_decision else 0)

speed_tab, cases_tab, expedite_tab, quality_tab, personal_tab = st.tabs(
    (
        t("tab_speed"),
        t("tab_cases"),
        t("tab_expedite"),
        t("tab_quality"),
        t("tab_personal"),
    )
)

with speed_tab:
    st.subheader(t("subheader_recent_decisions"))
    d1, d2, d3, d4 = st.columns(4)
    d1.metric(t("metric_last_7_days"), decisions.last_7_days)
    d2.metric(t("metric_previous_calendar_week"), decisions.previous_calendar_week)
    d3.metric(t("metric_current_week"), decisions.current_calendar_week)
    d4.metric(t("metric_current_month"), decisions.current_calendar_month)

    st.subheader(t("subheader_recent_pace"))
    st.caption(t("caption_recent_pace"))
    granularity = st.radio(
        t("granularity_label"),
        [t("granularity_monthly"), t("granularity_weekly")],
        horizontal=True,
        key="pace_granularity",
    )
    use_monthly = granularity == t("granularity_monthly")
    duration_label = (
        t("duration_label_weighted") if use_monthly else t("duration_label_median")
    )
    if use_monthly:
        st.caption(t("caption_monthly_weighted"))
    families = ["tps", "re_parole", "ead"]
    pace_columns = st.columns(len(families))
    flagged_frames = []
    for family, pace_column in zip(families, pace_columns):
        series = _decision_series(
            metrics.weekly_milestone_durations, family, monthly=use_monthly
        )
        with pace_column:
            flagged = _decision_combo_chart(
                series, title=_label(family), duration_label=duration_label
            )
        if flagged is not None:
            flagged = flagged.copy()
            flagged.insert(0, t("column_case_type"), _label(family))
            flagged_frames.append(flagged)
    if flagged_frames:
        st.caption(t("caption_flagged_periods"))
        st.dataframe(
            pd.concat(flagged_frames, ignore_index=True), hide_index=True, width="stretch"
        )

    st.subheader(t("subheader_filed_vintage"))
    window_options = list(WINDOW_ORDER)
    selected_window = st.selectbox(
        t("window_label"),
        window_options,
        index=window_options.index("3month"),
        format_func=window_label,
        key="filed_cohort_window",
    )
    recent_decision_filed_cohorts_by_window = getattr(
        metrics,
        "recent_decision_filed_cohorts_by_window",
        (),
    )
    windowed_cohorts = [
        row
        for row in recent_decision_filed_cohorts_by_window
        if row.window == selected_window
    ]
    cohort_frame = _filed_cohort_frame(windowed_cohorts)
    if cohort_frame.empty:
        st.info(t("info_no_filed_cohort"))
    else:
        month_order = list(dict.fromkeys(cohort_frame[t("column_filed_month")]))
        chart_title = (
            t("chart_title_filed_cohort_all_time")
            if selected_window == "all_time"
            else t("chart_title_filed_cohort", window=window_label(selected_window).lower())
        )
        figure = px.bar(
            cohort_frame,
            x=t("column_filed_month"),
            y=t("column_count"),
            color=t("column_case_type"),
            barmode="group",
            category_orders={t("column_filed_month"): month_order},
            title=chart_title,
        )
        st.plotly_chart(figure, width="stretch")
    st.caption(t("caption_filed_cohort"))

    summary = _milestone_frame(metrics.milestone_durations)
    if not summary.empty:
        summary = summary[summary[t("column_milestone")] != _label("approval")]
    st.subheader(t("subheader_typical_time"))
    if summary.empty:
        st.info(t("info_no_milestone_samples"))
    else:
        preferred = [_label("tps"), _label("re_parole"), _label("ead")]
        order = {name: index for index, name in enumerate(preferred)}
        summary["_order"] = summary[t("column_case_type")].map(
            lambda value: order.get(value, len(order))
        )
        summary = summary.sort_values(["_order", t("column_case_type"), t("column_milestone")])
        st.dataframe(summary.drop(columns="_order"), hide_index=True, width="stretch")

    weekly = _weekly_frame(metrics.weekly_milestone_durations)
    if not weekly.empty:
        weekly = weekly[weekly[t("column_milestone")] != _label("approval")]
    st.subheader(t("subheader_weekly_trend"))
    if weekly.empty:
        st.info(t("info_no_weekly_trend"))
    else:
        families = list(dict.fromkeys(weekly[t("column_case_type")]))
        default_family = next(
            (
                name
                for name in (_label("re_parole"), _label("tps"), _label("ead"))
                if name in families
            ),
            families[0],
        )
        c1, c2 = st.columns(2)
        family = c1.selectbox(
            t("case_type_label"),
            families,
            index=families.index(default_family),
        )
        milestones = list(
            dict.fromkeys(
                weekly.loc[weekly[t("column_case_type")] == family, t("column_milestone")]
            )
        )
        milestone = c2.selectbox(t("milestone_label"), milestones)
        selected = weekly[
            (weekly[t("column_case_type")] == family) & (weekly[t("column_milestone")] == milestone)
        ]
        trend = selected.melt(
            id_vars=[t("column_week"), t("column_cases")],
            value_vars=[t("column_average_days"), t("column_median_days")],
            var_name=t("measure_label"),
            value_name=t("column_days"),
        )
        figure = px.line(
            trend,
            x=t("column_week"),
            y=t("column_days"),
            color=t("measure_label"),
            markers=True,
            hover_data=[t("column_cases")],
            title=t("chart_title_trend", family=family, milestone=milestone.lower()),
        )
        st.plotly_chart(figure, width="stretch")
        st.caption(t("caption_trend"))

        signals = _pace_signals(metrics.weekly_milestone_durations)
        st.subheader(t("subheader_pace_signals"))
        if signals.empty:
            st.info(t("info_no_pace_signals"))
        else:
            st.dataframe(signals, hide_index=True, width="stretch")
            st.caption(t("caption_pace_signals"))

    left, right = st.columns(2)
    with left:
        _bar(
            metrics.reports_by_month,
            key_label=t("column_reported_month"),
            title=t("chart_title_reports_by_month"),
        )
    with right:
        _bar(
            metrics.decisions_by_month,
            key_label=t("column_decision_month"),
            title=t("chart_title_decisions_by_month"),
        )

with cases_tab:
    left, right = st.columns(2)
    with left:
        _bar(
            metrics.reports_by_form,
            key_label=t("column_form"),
            title=t("chart_title_reports_by_form"),
        )
        _bar(
            metrics.reports_by_subtype,
            key_label=t("column_case_subtype"),
            title=t("chart_title_reports_by_subtype"),
            horizontal=True,
        )
    with right:
        _bar(
            metrics.current_status_distribution,
            key_label=t("column_current_status"),
            title=t("chart_title_status_distribution"),
            horizontal=True,
        )

with expedite_tab:
    comparison = _expedite_frame(metrics.expedite_duration_comparisons)
    if not comparison.empty:
        comparison = comparison[
            comparison[t("column_case_type")].isin([_label("re_parole"), _label("ead")])
            & (comparison[t("column_milestone")] == _label("decision"))
        ]
    st.subheader(t("subheader_expedite_comparison"))
    if comparison.empty:
        st.info(t("info_no_expedite_comparison"))
    else:
        st.dataframe(comparison, hide_index=True, width="stretch")
    heatmap_left, heatmap_right = st.columns(2)
    monthly_decision_durations = getattr(
        metrics,
        "monthly_decision_durations",
        (),
    )
    with heatmap_left:
        _decision_heatmap(monthly_decision_durations, "re_parole")
    with heatmap_right:
        _decision_heatmap(monthly_decision_durations, "ead")
    st.caption(t("caption_heatmap"))
    e1, e2 = st.columns(2)
    e1.metric(t("metric_expedite_requests"), metrics.expedite_request_count)
    e2.metric(t("metric_reports_with_expedite"), metrics.reports_with_expedite)
    _bar(
        metrics.expedite_by_channel,
        key_label=t("column_channel"),
        title=t("chart_title_expedite_by_channel"),
        horizontal=True,
    )
    st.info(t("info_expedite_disclaimer"))

with quality_tab:
    q1, q2, q3, q4 = st.columns(4)
    q1.metric(t("metric_included_reports"), quality.included_report_count)
    q2.metric(t("metric_excluded_reports"), quality.excluded_report_count)
    q3.metric(t("metric_unknown_form"), quality.unknown_form_count)
    q4.metric(t("metric_unknown_status"), quality.unknown_status_count)
    review_total = metrics.historic_pending_count + metrics.historic_reviewed_count
    review_percent = (
        metrics.historic_reviewed_count / review_total * 100 if review_total else 0.0
    )
    st.metric(t("metric_historic_review_complete"), f"{review_percent:.1f}%")
    quality_rows = pd.DataFrame(
        [
            {
                t("column_quality_signal"): t("quality_signal_missing_filed_date"),
                t("column_count"): quality.reports_missing_filed_date,
            },
            {
                t("column_quality_signal"): t("quality_signal_missing_decision_date"),
                t("column_count"): quality.reports_missing_decision_date,
            },
            {
                t("column_quality_signal"): t("quality_signal_conflicting_evidence"),
                t("column_count"): quality.conflicting_evidence_count,
            },
        ]
    )
    st.plotly_chart(
        px.bar(
            quality_rows,
            x=t("column_quality_signal"),
            y=t("column_count"),
            title=t("chart_title_quality_signals"),
        ),
        width="stretch",
    )

with personal_tab:
    st.caption(t("caption_personal_tab"))
    if personal_snapshot is None:
        st.info(t("info_no_personal_data"))
    else:
        counts = personal_snapshot.counts
        p1, p2 = st.columns(2)
        p1.metric(t("metric_self_tracked_submissions"), counts.submission_count)
        wait = personal_snapshot.pending_wait_days
        p2.metric(
            t("metric_median_wait_pending"),
            _days(wait.median_days) if wait.sample_size else t("days_not_available"),
        )
        left, right = st.columns(2)
        with left:
            _bar(
                counts.by_form_type,
                key_label=t("column_form"),
                title=t("chart_title_self_tracked_by_form"),
            )
        with right:
            _bar(
                counts.by_status,
                key_label=t("column_current_status"),
                title=t("chart_title_self_tracked_status"),
                horizontal=True,
            )
        _bar(
            counts.by_filed_month,
            key_label=t("column_reported_month"),
            title=t("chart_title_self_tracked_by_month"),
        )
        st.caption(
            t(
                "caption_personal_generated",
                generated_at=personal_snapshot.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
            )
        )

st.divider()
st.subheader(t("subheader_how_to_interpret"))
st.markdown(t("how_to_interpret_body"))
