"""Public Streamlit UI over the aggregate-only Oracle dashboard API."""

import html
import importlib
import json
import os
import re
import sys
import unicodedata
from datetime import UTC, date, datetime, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
from plotly.subplots import make_subplots
from streamlit.errors import StreamlitSecretNotFoundError

def _load_dashboard_data_module():
    """Import dashboard data, recovering from Streamlit's hot-reload race."""

    try:
        return importlib.import_module("dashboard_data")
    except KeyError as exc:
        if exc.args != ("dashboard_data",):
            raise
        # Streamlit's file watcher can briefly remove this module from
        # sys.modules during a rerun while Python is still resolving it.
        # Clear any partial entry and retry once from the stable source file.
        sys.modules.pop("dashboard_data", None)
        importlib.invalidate_caches()
        return importlib.import_module("dashboard_data")
    except ModuleNotFoundError:
        return importlib.import_module("apps.streamlit.dashboard_data")


_dashboard_data = _load_dashboard_data_module()
DashboardSnapshot = _dashboard_data.DashboardSnapshot
PersonalDashboardSnapshot = _dashboard_data.PersonalDashboardSnapshot
PublicDashboardUnavailable = _dashboard_data.PublicDashboardUnavailable
bucket_rows = _dashboard_data.bucket_rows
fetch_dashboard_snapshot = _dashboard_data.fetch_dashboard_snapshot
public_api_base_url = _dashboard_data.public_api_base_url
snapshot_age_hours = _dashboard_data.snapshot_age_hours

# A stale hosting code cache that predates the optional personal endpoint must
# degrade only that tab, never crash the canonical dashboard.
fetch_personal_dashboard_snapshot = getattr(
    _dashboard_data,
    "fetch_personal_dashboard_snapshot",
    None,
)

from i18n import (
    WINDOW_ORDER,
    get_source,
    label,
    render_language_selector,
    render_source_selector,
    t,
    translations,
    window_label,
)

st.set_page_config(
    page_title="Community Immigration Case Tracker",
    page_icon="📊",
    layout="wide",
)

# Single shared cadence for every cached data source on this page (the
# canonical snapshot and the personal-tracking snapshot alike), so there is
# one consistent number instead of two different ones to reconcile.
PAGE_DATA_CACHE_TTL_SECONDS = 300


_ANCHOR_HEADING_KEYS = (
    "title",
    "subheader_filing_to_decision",
    "subheader_recent_decisions",
    "subheader_recent_pace",
    "subheader_filed_vintage",
    "subheader_typical_time",
    "subheader_weekly_trend",
    "subheader_pace_signals",
    "subheader_expedite_comparison",
    "subheader_case_estimates",
    "how_title",
    "how_expected_title",
    "how_confirmation_title",
    "how_stored_title",
    "how_pii_title",
    "how_pii_extracted_title",
    "how_disclaimer_title",
    "subheader_how_to_interpret",
    "tab_speed",
    "tab_cases",
    "tab_personal",
)

_SECTION_HEADING_KEYS = dict(
    zip(
        (
            "overview", "decision", "recent", "pace", "filings", "typical",
            "trends", "signals", "expedite", "estimates", "how", "input",
            "confirm", "stored", "privacy", "extracted", "notice",
            "interpretation", "speed", "cases", "self_tracking",
        ),
        _ANCHOR_HEADING_KEYS,
        strict=True,
    )
)
_SECTION_TAB_KEYS = {
    **{section: "tab_speed" for section in (
        "speed", "recent", "pace", "filings", "typical", "trends", "signals",
    )},
    "expedite": "tab_expedite",
    "estimates": "tab_estimates",
    "cases": "tab_cases",
    "self_tracking": "tab_personal",
    **{section: "tab_how_it_works" for section in (
        "how", "input", "confirm", "stored", "privacy", "extracted", "notice",
    )},
}

_UKRAINIAN_TRANSLITERATION = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d",
        "е": "e", "є": "ye", "ж": "zh", "з": "z", "и": "y", "і": "i",
        "ї": "yi", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
        "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
        "щ": "shch", "ь": "", "ю": "yu", "я": "ya",
    }
)
_UKRAINIAN_TRANSLITERATION[ord("\u0438")] = "i"


def _anchor_slug(value: str) -> str:
    """Approximate Streamlit's share-link slug for either supported language."""

    transliterated = value.casefold().translate(_UKRAINIAN_TRANSLITERATION)
    ascii_value = unicodedata.normalize("NFKD", transliterated).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def _section_heading(level: str, key: str, section: str) -> None:
    """Render a heading with a clipboard-ready durable section URL."""

    heading_class, aria_level = {
        "title": ("u4u-title", 1),
        "header": ("u4u-header", 2),
        "subheader": ("u4u-subheader", 3),
    }[level]
    language = st.query_params.get("lang") or "uk"
    href = html.escape(
        f"https://u4u-dashboard.streamlit.app/?lang={language}&section={section}",
        quote=True,
    )
    st.markdown(
        f'<div id="{section}" class="u4u-section-heading {heading_class}" '
        f'role="heading" aria-level="{aria_level}">{html.escape(t(key))}'
        f'<span class="u4u-section-link" data-copy-url="{href}" role="button" '
        f'tabindex="0" title="Copy link" aria-label="Copy section link">#</span></div>',
        unsafe_allow_html=True,
    )


def _render_section_styles() -> None:
    """Keep durable section links compact and hidden until interaction."""

    st.markdown(
        """
<style>
.u4u-section-heading {
  font-family: inherit;
  font-weight: 700;
  letter-spacing: -0.005em;
  line-height: 1.2;
}
.u4u-title {
  font-size: 2.75rem;
  margin: 0 0 0.5rem;
}
.u4u-header {
  font-size: 2.25rem;
  margin: 1rem 0 0.5rem;
}
.u4u-subheader {
  font-size: 1.5rem;
  margin: 1rem 0 0.5rem;
}
.u4u-section-heading .u4u-section-link {
  color: inherit;
  cursor: pointer;
  font-size: 0.62em;
  font-weight: 400;
  margin-left: 0.35rem;
  opacity: 0;
  text-decoration: none;
  transition: opacity 100ms ease-in-out;
  vertical-align: middle;
}
.u4u-section-heading:hover .u4u-section-link,
.u4u-section-heading .u4u-section-link:focus-visible { opacity: 0.45; }
.u4u-section-heading .u4u-section-link:hover { opacity: 0.85; }
</style>
""",
        unsafe_allow_html=True,
    )


def _render_section_scroll_support() -> None:
    """Scroll to a selected section and make heading links copy-only."""

    section = st.query_params.get("section")
    scroll_section = section if section in _SECTION_HEADING_KEYS else ""
    st.iframe(
        f"""
<script>
(() => {{
  const section = {json.dumps(scroll_section)};
  const appWindow = window.parent;
  const appDocument = appWindow.document;

  if (appWindow.__u4uSectionClipboardClickHandler) {{
    appDocument.removeEventListener(
      "click", appWindow.__u4uSectionClipboardClickHandler, true
    );
  }}
  if (appWindow.__u4uSectionClipboardKeyHandler) {{
    appDocument.removeEventListener(
      "keydown", appWindow.__u4uSectionClipboardKeyHandler, true
    );
  }}

  const copyHandler = async (event) => {{
      const link = event.target.closest?.(".u4u-section-link[data-copy-url]");
      if (!link) return;

      event.preventDefault();
      event.stopPropagation();
      const url = link.dataset.copyUrl;
      let copied = false;

      try {{
        await appWindow.navigator.clipboard.writeText(url);
        copied = true;
      }} catch (_) {{
        const textarea = appDocument.createElement("textarea");
        textarea.value = url;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        appDocument.body.appendChild(textarea);
        textarea.select();
        copied = appDocument.execCommand("copy");
        textarea.remove();
      }}

      if (copied) {{
        const originalText = link.textContent;
        link.textContent = "✓";
        link.setAttribute("aria-label", "Link copied");
        appWindow.setTimeout(() => {{
          link.textContent = originalText;
          link.setAttribute("aria-label", "Copy section link");
        }}, 1200);
      }}
  }};

  const keyHandler = (event) => {{
    const link = event.target.closest?.(".u4u-section-link[data-copy-url]");
    if (!link || !["Enter", " "].includes(event.key)) return;

    event.preventDefault();
    event.stopPropagation();
    link.click();
  }};

  appWindow.__u4uSectionClipboardClickHandler = copyHandler;
  appWindow.__u4uSectionClipboardKeyHandler = keyHandler;
  appDocument.addEventListener("click", copyHandler, true);
  appDocument.addEventListener("keydown", keyHandler, true);
  appWindow.__u4uSectionClipboardInstalled = true;

  let attempts = 0;
  function scrollToSection() {{
    const target = appDocument.getElementById(section);
    if (target) {{
      target.scrollIntoView({{ behavior: "auto", block: "start" }});
    }} else if (attempts++ < 80) {{
      appWindow.setTimeout(scrollToSection, 100);
    }}
  }}
  if (section) appWindow.requestAnimationFrame(scrollToSection);
}})();
</script>
""",
        height=1,
    )

def _render_section_link_support() -> None:
    """Turn Streamlit heading fragments into durable section query links."""

    heading_groups = [
        {
            "section": section,
            "hashes": [section, *[_anchor_slug(text) for text in translations(key)]],
            "currentText": t(key),
        }
        for section, key in _SECTION_HEADING_KEYS.items()
    ]
    groups_json = json.dumps(heading_groups, ensure_ascii=False).replace("</", "<\\/")
    current_language = st.query_params.get("lang") or "uk"
    st.html(
        f"""
<script>
(() => {{
  const headingGroups = {groups_json};
  const currentLanguage = {json.dumps(current_language)};
  let attempts = 0;
  let scheduled = false;

  function groupForHash(hash) {{
    const normalized = hash.toLowerCase();
    return headingGroups.find((item) => item.hashes.includes(normalized)) || null;
  }}

  function durableUrl(section) {{
    const url = new URL(window.parent.location.href);
    url.searchParams.set("lang", currentLanguage);
    url.searchParams.set("section", section);
    url.hash = "";
    return url.toString();
  }}

  function requestedSection() {{
    const url = new URL(window.parent.location.href);
    try {{
      const group = groupForHash(decodeURIComponent(url.hash.slice(1)));
      if (group) return group.section;
    }} catch (_) {{
      // Fall through to the server-readable section parameter.
    }}
    const querySection = url.searchParams.get("section");
    if (querySection && headingGroups.some((item) => item.section === querySection)) {{
      return querySection;
    }}
    return "";
  }}

  function findHeading(doc, group) {{
    const direct = doc.getElementById(group.section);
    if (direct) return direct;

    return Array.from(doc.querySelectorAll("h1,h2,h3,h4,h5,h6")).find(
      (heading) => heading.textContent.trim() === group.currentText
    ) || null;
  }}

  function rewriteHeadingLinks(doc) {{
    for (const link of doc.querySelectorAll('a[href*="#"]')) {{
      let group = null;
      try {{
        const url = new URL(link.getAttribute("href"), window.parent.location.href);
        group = groupForHash(decodeURIComponent(url.hash.slice(1)));
      }} catch (_) {{
        continue;
      }}
      if (group) link.href = durableUrl(group.section);
    }}
  }}

  function activateAndScroll() {{
    scheduled = false;
    let doc;
    try {{
      doc = window.parent.document;
    }} catch (_) {{
      return true;
    }}
    rewriteHeadingLinks(doc);

    const section = requestedSection();
    if (!section) return true;
    const group = headingGroups.find((item) => item.section === section);
    const target = group && findHeading(doc, group);
    if (!target) return false;

    const panel = target.closest('[data-testid="stTabPanel"]');
    if (panel) {{
      const tabsContainer = panel.closest('[data-testid="stTabs"]');
      if (tabsContainer) {{
        const panels = Array.from(
          tabsContainer.querySelectorAll('[data-testid="stTabPanel"]')
        );
        const tabs = Array.from(
          tabsContainer.querySelectorAll('[data-testid="stTab"]')
        );
        const tab = tabs[panels.indexOf(panel)];
        if (tab && tab.getAttribute("aria-selected") !== "true") tab.click();
      }}
    }}

    window.parent.setTimeout(
      () => target.scrollIntoView({{ behavior: "auto", block: "start" }}),
      panel ? 100 : 0
    );
    return true;
  }}

  function schedule() {{
    if (scheduled) return;
    scheduled = true;
    window.parent.requestAnimationFrame(() => {{
      if (!activateAndScroll() && attempts++ < 80) window.parent.setTimeout(schedule, 100);
    }});
  }}

  try {{
    window.parent.document.addEventListener("click", (event) => {{
      const link = event.target.closest && event.target.closest("a[href]");
      if (!link) return;
      let group = null;
      try {{
        const url = new URL(link.getAttribute("href"), window.parent.location.href);
        group = groupForHash(decodeURIComponent(url.hash.slice(1)));
      }} catch (_) {{
        return;
      }}
      if (!group) return;
      link.href = durableUrl(group.section);
    }}, true);
    new window.parent.MutationObserver(schedule).observe(window.parent.document.body, {{
      childList: true,
      subtree: true,
    }});
  }} catch (_) {{
    // If browser scripting is restricted, query links still select the right tab.
  }}
  schedule();
}})();
</script>
""",
        unsafe_allow_javascript=True,
    )


def _secret_api_url() -> str | None:
    try:
        value = st.secrets.get("U4U_PUBLIC_API_BASE_URL")
    except (FileNotFoundError, KeyError, StreamlitSecretNotFoundError):
        return None
    return value if isinstance(value, str) else None


@st.cache_data(ttl=PAGE_DATA_CACHE_TTL_SECONDS, show_spinner=False)
def _load_snapshot_payload(base_url: str, source: str):
    """Return a pickle-stable JSON payload and ISO fetch timestamp.

    `st.cache_data` is a server-wide cache shared by every visitor, not a
    per-browser-session value — `fetched_at` is captured once, when this
    cache entry is (re)populated, so the same value and countdown are seen
    by all concurrent users and survive any single user's manual refresh.
    Keyed on `source` too, so each of the three selector positions gets its
    own cache entry instead of colliding.
    """

    snapshot = fetch_dashboard_snapshot(base_url, source=source)
    return snapshot.model_dump(mode="json"), datetime.now(UTC).isoformat()


def _load_snapshot(base_url: str, source: str):
    """Rehydrate the strictly validated model outside Streamlit's pickle cache."""

    payload, fetched_at = _load_snapshot_payload(base_url, source)
    return (
        DashboardSnapshot.model_validate(payload),
        datetime.fromisoformat(fetched_at),
    )


@st.cache_data(ttl=PAGE_DATA_CACHE_TTL_SECONDS, show_spinner=False)
def _load_personal_snapshot_payload(base_url: str):
    """Return a pickle-stable optional personal payload and timestamp."""

    snapshot = (
        None
        if fetch_personal_dashboard_snapshot is None
        else fetch_personal_dashboard_snapshot(base_url)
    )
    payload = None if snapshot is None else snapshot.model_dump(mode="json")
    return payload, datetime.now(UTC).isoformat()


def _load_personal_snapshot(base_url: str):
    """Rehydrate the optional personal model outside Streamlit's pickle cache."""

    payload, fetched_at = _load_personal_snapshot_payload(base_url)
    snapshot = (
        None
        if payload is None
        else PersonalDashboardSnapshot.model_validate(payload)
    )
    return snapshot, datetime.fromisoformat(fetched_at)


def _next_wall_clock_mark(now: datetime, *, period_seconds: int) -> datetime:
    """Smallest multiple of `period_seconds` past the hour, strictly after `now`.

    Matches `apps/worker/main.py`'s `_next_dashboard_rebuild_mark` on the
    backend — both compute the same schedule independently from the shared
    wall clock (e.g. :00/:05/:10 for a 300s period), with no API call
    between them.
    """

    epoch = now.replace(minute=0, second=0, microsecond=0)
    elapsed_seconds = (now - epoch).total_seconds()
    marks_elapsed = int(elapsed_seconds // period_seconds) + 1
    return epoch + timedelta(seconds=marks_elapsed * period_seconds)


def _render_refresh_countdown() -> None:
    """A purely informational, repeating countdown.

    Shows time until the next wall-clock-aligned mark (e.g. :00/:05/:10),
    matching the backend worker's own rebuild schedule (see
    `apps/worker/main.py`) — computed independently from the current time,
    with no API call to ask when the last/next rebuild actually happened.
    It never reloads or reruns the page; reopen the page after it reaches
    zero to see whether new data arrived. Since it's derived purely from
    wall-clock time, every visitor sees the same countdown at any given
    moment.
    """

    period_seconds = PAGE_DATA_CACHE_TTL_SECONDS
    next_refresh_at = _next_wall_clock_mark(
        datetime.now(UTC), period_seconds=period_seconds
    )
    st.iframe(
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


def _bar(buckets, *, key_label, title, horizontal=False, caption=None):
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
    if caption:
        st.caption(caption)


def _one_decimal(value: float | int | None) -> int | float | None:
    """Round to one decimal and omit a redundant zero decimal."""

    if value is None or pd.isna(value):
        return None
    rounded = round(float(value), 1)
    return int(rounded) if rounded.is_integer() else rounded


def _one_decimal_text(value: float | int | None) -> str:
    """Return the compact dashboard representation of a measured value."""

    rounded = _one_decimal(value)
    return "" if rounded is None else str(rounded)


def _signed_percent(value: float | int) -> str:
    """Render a signed percentage using the compact decimal policy."""

    rounded = _one_decimal(value)
    return f"{rounded:+}%"


def _date_only(value: object) -> object:
    """Render table dates without an unnecessary midnight timestamp."""

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, datetime | date):
        return value.strftime("%Y-%m-%d")
    return value


def _display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply the dashboard-wide table display policy."""

    result = frame.copy()
    for column in result.columns:
        if pd.api.types.is_float_dtype(result[column]):
            result[column] = result[column].map(_one_decimal_text)
        elif pd.api.types.is_datetime64_any_dtype(result[column]):
            result[column] = result[column].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_object_dtype(result[column]):
            result[column] = result[column].map(_date_only)
    return result


def _dataframe(frame: pd.DataFrame) -> None:
    st.dataframe(_display_frame(frame), hide_index=True, width="stretch")


def _days(value: float | None) -> str:
    rounded = _one_decimal(value)
    return t("days_value", value=rounded) if rounded is not None else t("days_not_available")


def _milestone_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                t("column_case_type"): _label(row.case_family),
                t("column_milestone"): _label(row.milestone),
                t("column_average_days"): _one_decimal(row.duration.average_days),
                t("column_median_days"): _one_decimal(row.duration.median_days),
                t("column_first_quartile"): _one_decimal(row.duration.first_quartile_days),
                t("column_third_quartile"): _one_decimal(row.duration.third_quartile_days),
                t("column_cases"): row.duration.sample_size,
            }
            for row in rows
        ]
    )


def _weekly_frame(rows) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                t("column_week"): row.week_start.isoformat(),
                t("column_case_type"): _label(row.case_family),
                t("column_milestone"): _label(row.milestone),
                t("column_average_days"): _one_decimal(row.duration.average_days),
                t("column_median_days"): _one_decimal(row.duration.median_days),
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
                t("column_latest_week"): latest.week_start.isoformat(),
                t("column_latest_median"): _one_decimal(latest.duration.median_days),
                t("column_prior_baseline"): _one_decimal(baseline),
                t("column_change"): _signed_percent(change),
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
                    "Days": _one_decimal(row.duration.median_days),
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
    grouped["Days"] = (grouped["WeightedDays"] / grouped["Cases"]).round(1)
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
                t("column_period"): _date_only(period),
                t("column_days"): _one_decimal(days),
                t("column_signal"): signal_name,
                t("column_change"): _signed_percent(change),
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
                t("column_expedite_median"): _one_decimal(with_value.median_days),
                t("column_expedite_average"): _one_decimal(with_value.average_days),
                t("column_expedite_cases"): with_value.sample_size,
                t("column_no_expedite_median"): _one_decimal(without_value.median_days),
                t("column_no_expedite_average"): _one_decimal(without_value.average_days),
                t("column_no_expedite_cases"): without_value.sample_size,
                t("column_median_difference"): _one_decimal(difference),
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


def _monthly_decision_chart(rows, family: str) -> None:
    labels = {False: t("heatmap_no_expedite"), True: t("heatmap_expedite")}
    frame = pd.DataFrame(
        [
            {
                "Month": row.month_start.strftime("%Y-%m"),
                "Expedite": labels[row.with_expedite],
                "Median days": _one_decimal(row.duration.median_days),
                "Cases": row.duration.sample_size,
            }
            for row in rows
            if row.case_family == family and row.duration.median_days is not None
        ]
    )
    title = t("monthly_decision_chart_title", family=_label(family))
    if frame.empty:
        st.info(t("monthly_decision_no_samples", family=_label(family)))
        return
    month_order = sorted(frame["Month"].unique())
    figure = px.bar(
        frame,
        x="Month",
        y="Median days",
        color="Expedite",
        barmode="group",
        category_orders={"Month": month_order, "Expedite": [labels[False], labels[True]]},
        hover_data=["Cases"],
        title=title,
    )
    figure.update_layout(height=320, margin={"l": 20, "r": 20, "t": 60, "b": 20})
    st.plotly_chart(figure, width="stretch")


def _case_estimates_table(observations, filed_date, window_days: int, generated_date):
    """One row per case family for reports filed within `window_days` of
    `filed_date` (in either direction): approved/pending/denied counts,
    how long pending cases in this window have been waiting so far, and
    how long the already-approved ones in this window actually took.
    """
    window_rows = [
        obs for obs in observations if abs((obs.filed_date - filed_date).days) <= window_days
    ]
    if not window_rows:
        return None
    rows = []
    for family in ("tps", "re_parole", "ead"):
        family_rows = [obs for obs in window_rows if obs.case_family == family]
        if not family_rows:
            continue
        pending_waits = [
            (generated_date - obs.filed_date).days
            for obs in family_rows
            if obs.status_bucket == "pending"
            for _ in range(obs.weight)
        ]
        approved_durations = [
            (obs.decision_date - obs.filed_date).days
            for obs in family_rows
            if obs.status_bucket == "approved" and obs.decision_date is not None
            for _ in range(obs.weight)
        ]
        rows.append(
            {
                t("estimates_column_type"): _label(family),
                t("estimates_approved_count"): sum(
                    obs.weight for obs in family_rows if obs.status_bucket == "approved"
                ),
                t("estimates_pending_count"): sum(
                    obs.weight for obs in family_rows if obs.status_bucket == "pending"
                ),
                t("estimates_denied_count"): sum(
                    obs.weight for obs in family_rows if obs.status_bucket == "denied"
                ),
                t("estimates_pending_wait_median"): (
                    _days(pd.Series(pending_waits).median()) if pending_waits else t("days_not_available")
                ),
                t("estimates_approved_wait_median"): (
                    _days(pd.Series(approved_durations).median())
                    if approved_durations
                    else t("days_not_available")
                ),
            }
        )
    return pd.DataFrame(rows) if rows else None


_render_section_styles()
_lang_col, _source_col, _join_col, _ = st.columns([1, 1.4, 1, 2.6])
with _lang_col:
    render_language_selector()
with _source_col:
    _selected_source = render_source_selector()
with _join_col:
    st.link_button(
        t("join_button"),
        "https://t.me/u4u_personal_tracking_bot",
        type="primary",
        width="stretch",
    )

_section_heading("title", "title", "overview")
st.caption(t("subtitle"))

try:
    api_base_url = public_api_base_url(
        os.environ,
        secret_value=_secret_api_url(),
    )
    snapshot, _canonical_fetched_at = _load_snapshot(api_base_url, _selected_source)
except PublicDashboardUnavailable as error:
    st.error(str(error))
    st.info(t("api_unavailable_info"))
    st.stop()

st.error(t("disclaimer_no_evidence"))

with st.expander(t("subheader_about"), expanded=True):
    st.markdown(
        t(
            "about_body",
            report_count=snapshot.metrics.report_count,
            case_observation_count=snapshot.metrics.case_observation_count,
        )
    )

# Loaded once here (not inside the personal tab) so one global countdown can
# cover every cached data source on the page, including the personal tab's.
personal_snapshot, _personal_fetched_at = _load_personal_snapshot(api_base_url)
_render_refresh_countdown()

age_hours = snapshot_age_hours(snapshot)
freshness = snapshot.generated_at.strftime("%Y-%m-%d %H:%M UTC")
if age_hours > 24:
    st.warning(t("snapshot_stale", hours=_one_decimal(age_hours), freshness=freshness))
else:
    st.caption(t("snapshot_fresh", version=snapshot.data_version, freshness=freshness))

metrics = snapshot.metrics
decisions = metrics.final_decisions
reparole_decision = _decision_summary(metrics.milestone_durations, "re_parole")
ead_decision = _decision_summary(metrics.milestone_durations, "ead")
tps_decision = _decision_summary(metrics.milestone_durations, "tps")

summary_1, summary_2, summary_3 = st.columns(3)
summary_1.metric(t("metric_case_observations"), metrics.case_observation_count)
summary_2.metric(t("metric_decisions_this_week"), decisions.current_calendar_week)
summary_3.metric(t("metric_decisions_this_month"), decisions.current_calendar_month)

if metrics.source_counts is not None:
    st.caption(
        t(
            "source_provenance",
            total=metrics.case_observation_count,
            published=metrics.source_counts.published_case_observation_count,
            self_tracked=metrics.source_counts.self_tracked_case_observation_count,
        )
    )

_section_heading("subheader", "subheader_filing_to_decision", "decision")
for average_key, median_key, cases_key, duration in (
    ("metric_tps_average", "metric_tps_median", "metric_tps_cases", tps_decision),
    (
        "metric_reparole_average",
        "metric_reparole_median",
        "metric_reparole_cases",
        reparole_decision,
    ),
    ("metric_ead_average", "metric_ead_median", "metric_ead_cases", ead_decision),
):
    average_column, median_column, cases_column = st.columns(3)
    average_column.metric(
        t(average_key), _days(duration.average_days if duration else None)
    )
    median_column.metric(
        t(median_key), _days(duration.median_days if duration else None)
    )
    cases_column.metric(t(cases_key), duration.sample_size if duration else 0)

_requested_section = st.query_params.get("section")
_tab_labels = (
    t("tab_speed"),
    t("tab_cases"),
    t("tab_expedite"),
    t("tab_estimates"),
    t("tab_personal"),
    t("tab_how_it_works"),
)
_requested_tab_key = _SECTION_TAB_KEYS.get(_requested_section)
_requested_tab_label = t(_requested_tab_key) if _requested_tab_key else _tab_labels[0]

_language = st.query_params.get("lang") or "uk"
_tab_widget_key = f"dashboard_tabs_{_language}_{_requested_section or 'root'}"

speed_tab, cases_tab, expedite_tab, estimates_tab, personal_tab, how_tab = st.tabs(
    _tab_labels,
    default=_requested_tab_label,
    key=_tab_widget_key,
)

with speed_tab:
    _section_heading("subheader", "tab_speed", "speed")
    for family_key, family_decision in (
        ("tps", tps_decision),
        ("re_parole", reparole_decision),
        ("ead", ead_decision),
    ):
        if (
            family_decision
            and family_decision.first_quartile_days is not None
            and family_decision.third_quartile_days is not None
        ):
            st.markdown(
                "- "
                + t(
                    "typical_wait_sentence",
                    family=_label(family_key),
                    low=_one_decimal(family_decision.first_quartile_days),
                    high=_one_decimal(family_decision.third_quartile_days),
                    count=family_decision.sample_size,
                )
            )
        else:
            st.markdown("- " + t("typical_wait_unavailable", family=_label(family_key)))

    _section_heading("subheader", "subheader_recent_decisions", "recent")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric(t("metric_last_7_days"), decisions.last_7_days)
    d2.metric(t("metric_previous_calendar_week"), decisions.previous_calendar_week)
    d3.metric(t("metric_current_week"), decisions.current_calendar_week)
    d4.metric(t("metric_current_month"), decisions.current_calendar_month)

    _section_heading("subheader", "subheader_recent_pace", "pace")
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
        _dataframe(pd.concat(flagged_frames, ignore_index=True))

    _section_heading("subheader", "subheader_filed_vintage", "filings")
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
        family_totals: dict[str, int] = {}
        for row in windowed_cohorts:
            family_totals[row.case_family] = family_totals.get(row.case_family, 0) + row.count
        ordered_families = [family for family in ("tps", "re_parole", "ead") if family in family_totals]
        total_columns = st.columns(len(ordered_families))
        for column, family in zip(total_columns, ordered_families):
            column.metric(
                t("metric_filed_cohort_total", case_type=_label(family)),
                family_totals[family],
            )
    st.caption(t("caption_filed_cohort"))

    summary = _milestone_frame(metrics.milestone_durations)
    if not summary.empty:
        summary = summary[summary[t("column_milestone")] != _label("approval")]
    _section_heading("subheader", "subheader_typical_time", "typical")
    if summary.empty:
        st.info(t("info_no_milestone_samples"))
    else:
        preferred = [_label("tps"), _label("re_parole"), _label("ead")]
        order = {name: index for index, name in enumerate(preferred)}
        summary["_order"] = summary[t("column_case_type")].map(
            lambda value: order.get(value, len(order))
        )
        summary = summary.sort_values(["_order", t("column_case_type"), t("column_milestone")])
        _dataframe(summary.drop(columns="_order"))

    weekly = _weekly_frame(metrics.weekly_milestone_durations)
    if not weekly.empty:
        weekly = weekly[weekly[t("column_milestone")] != _label("approval")]
    _section_heading("subheader", "subheader_weekly_trend", "trends")
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
        _section_heading("subheader", "subheader_pace_signals", "signals")
        if signals.empty:
            st.info(t("info_no_pace_signals"))
        else:
            _dataframe(signals)
            st.caption(t("caption_pace_signals"))

    left, right = st.columns(2)
    with left:
        _bar(
            metrics.reports_by_month,
            key_label=t("column_reported_month"),
            title=t("chart_title_reports_by_month"),
            caption=t("caption_reports_by_month"),
        )
    with right:
        _bar(
            metrics.decisions_by_month,
            key_label=t("column_decision_month"),
            title=t("chart_title_decisions_by_month"),
            caption=t("caption_decisions_by_month"),
        )

with cases_tab:
    _section_heading("subheader", "tab_cases", "cases")
    left, right = st.columns(2)
    with left:
        _bar(
            metrics.reports_by_form,
            key_label=t("column_form"),
            title=t("chart_title_reports_by_form"),
            caption=t("caption_reports_by_form"),
        )
        _bar(
            metrics.reports_by_subtype,
            key_label=t("column_case_subtype"),
            title=t("chart_title_reports_by_subtype"),
            horizontal=True,
            caption=t("caption_reports_by_subtype"),
        )
    with right:
        _bar(
            metrics.current_status_distribution,
            key_label=t("column_current_status"),
            title=t("chart_title_status_distribution"),
            horizontal=True,
            caption=t("caption_status_distribution"),
        )

with expedite_tab:
    comparison = _expedite_frame(metrics.expedite_duration_comparisons)
    if not comparison.empty:
        comparison = comparison[
            comparison[t("column_case_type")].isin([_label("re_parole"), _label("ead")])
            & (comparison[t("column_milestone")] == _label("decision"))
        ]
    _section_heading("subheader", "subheader_expedite_comparison", "expedite")
    if comparison.empty:
        st.info(t("info_no_expedite_comparison"))
    else:
        _dataframe(comparison)
    heatmap_left, heatmap_right = st.columns(2)
    monthly_decision_durations = getattr(
        metrics,
        "monthly_decision_durations",
        (),
    )
    with heatmap_left:
        _monthly_decision_chart(monthly_decision_durations, "re_parole")
    with heatmap_right:
        _monthly_decision_chart(monthly_decision_durations, "ead")
    st.caption(t("caption_monthly_decision_chart"))
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

with estimates_tab:
    _section_heading("subheader", "subheader_case_estimates", "estimates")
    st.caption(t("caption_case_estimates"))
    filed_date_input = st.date_input(
        t("filed_date_label"),
        value=None,
        max_value=snapshot.generated_at.date(),
        key="estimates_filed_date",
    )
    if filed_date_input is None:
        st.info(t("estimates_pick_date_prompt"))
    else:
        for window_days, window_key in (
            (7, "window_1week_label"),
            (30, "window_1month_label"),
            (90, "window_3month_label"),
        ):
            st.markdown(f"**{t('estimates_window_heading', window=t(window_key))}**")
            table = _case_estimates_table(
                metrics.filed_case_observations,
                filed_date_input,
                window_days,
                snapshot.generated_at.date(),
            )
            if table is None:
                st.info(t("estimates_no_data"))
            else:
                _dataframe(table)

with personal_tab:
    _section_heading("subheader", "tab_personal", "self_tracking")
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
                caption=t("caption_self_tracked_by_form"),
            )
        with right:
            _bar(
                counts.by_status,
                key_label=t("column_current_status"),
                title=t("chart_title_self_tracked_status"),
                horizontal=True,
                caption=t("caption_self_tracked_status"),
            )
        _bar(
            counts.by_filed_month,
            key_label=t("column_reported_month"),
            title=t("chart_title_self_tracked_by_month"),
            caption=t("caption_self_tracked_by_month"),
        )
        st.caption(
            t(
                "caption_personal_generated",
                generated_at=personal_snapshot.generated_at.strftime("%Y-%m-%d %H:%M UTC"),
            )
        )

with how_tab:
    _section_heading("header", "how_title", "how")
    st.markdown(t("how_intro"))

    _section_heading("subheader", "how_expected_title", "input")
    st.markdown(t("how_expected_intro"))
    st.code(t("how_expected_example"), language=None, wrap_lines=True)

    _section_heading("subheader", "how_confirmation_title", "confirm")
    st.markdown(t("how_confirmation_intro"))
    st.info(t("how_confirmation_example"))

    _section_heading("subheader", "how_stored_title", "stored")
    st.markdown(t("how_stored_intro"))
    st.success(t("how_stored_example"))
    st.markdown(t("how_not_stored"))

    _section_heading("subheader", "how_pii_title", "privacy")
    st.warning(t("how_pii_warning"))
    st.markdown(t("how_pii_intro"))
    st.code(t("how_pii_example"), language=None, wrap_lines=True)
    st.markdown(t("how_pii_handling"))

    _section_heading("subheader", "how_pii_extracted_title", "extracted")
    st.markdown(t("how_pii_extracted_intro"))
    st.success(t("how_pii_extracted_example"))
    st.markdown(t("how_pii_excluded"))

    _section_heading("subheader", "how_disclaimer_title", "notice")
    st.warning(t("how_disclaimer_body"))

_render_section_scroll_support()

st.divider()
_section_heading("subheader", "subheader_how_to_interpret", "interpretation")
st.markdown(t("how_to_interpret_body"))
