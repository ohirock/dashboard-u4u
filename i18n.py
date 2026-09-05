"""English/Ukrainian text catalogue for the public Streamlit dashboard.

Every user-facing string in `dashboard.py` is looked up here through `t()`
(free-form UI text) or `label()` (data-driven case/status/milestone names),
keyed off the language selected via `render_language_selector()`. Ukrainian
domain terms reuse the vocabulary already established in the Telegram bots'
`packages/case_tracker_core/formatter.py` so the same case type or status
reads the same way in a channel post and on the dashboard.
"""

import streamlit as st

DEFAULT_LANGUAGE = "uk"
LANGUAGES: dict[str, str] = {"en": "English", "uk": "Українська"}
_QUERY_PARAM = "lang"
_SESSION_KEY = "lang"


def get_language() -> str:
    query_value = st.query_params.get(_QUERY_PARAM)
    if query_value in LANGUAGES:
        return query_value
    session_value = st.session_state.get(_SESSION_KEY)
    if session_value in LANGUAGES:
        return session_value
    return DEFAULT_LANGUAGE


def render_language_selector() -> str:
    """Render the selector and return the language code in effect this run."""

    current = get_language()
    codes = list(LANGUAGES.keys())
    labels = [LANGUAGES[code] for code in codes]
    chosen_label = st.selectbox(
        "Language / Мова",
        labels,
        index=codes.index(current),
        key="_lang_selector",
        label_visibility="collapsed",
    )
    chosen_code = codes[labels.index(chosen_label)]
    st.session_state[_SESSION_KEY] = chosen_code
    if st.query_params.get(_QUERY_PARAM) != chosen_code:
        st.query_params[_QUERY_PARAM] = chosen_code
    return chosen_code


SOURCES: tuple[str, ...] = ("all", "published", "self_tracked")
_SOURCE_QUERY_PARAM = "source"
_SOURCE_SESSION_KEY = "source"
_DEFAULT_SOURCE = "all"


def get_source() -> str:
    query_value = st.query_params.get(_SOURCE_QUERY_PARAM)
    if query_value in SOURCES:
        return query_value
    session_value = st.session_state.get(_SOURCE_SESSION_KEY)
    if session_value in SOURCES:
        return session_value
    return _DEFAULT_SOURCE


def render_source_selector() -> str:
    """Render the selector and return the source code in effect this run."""

    current = get_source()
    label_keys = {
        "all": "source_all",
        "published": "source_published",
        "self_tracked": "source_self_tracked",
    }
    labels = [t(label_keys[code]) for code in SOURCES]
    chosen_label = st.selectbox(
        t("source_selector_label"),
        labels,
        index=SOURCES.index(current),
        key="_source_selector",
        label_visibility="collapsed",
    )
    chosen_code = SOURCES[labels.index(chosen_label)]
    st.session_state[_SOURCE_SESSION_KEY] = chosen_code
    if st.query_params.get(_SOURCE_QUERY_PARAM) != chosen_code:
        st.query_params[_SOURCE_QUERY_PARAM] = chosen_code
    return chosen_code


def t(key: str, **kwargs) -> str:
    """Look up `key` in the current language's string table."""

    template = _STRINGS[get_language()].get(key) or _STRINGS[DEFAULT_LANGUAGE][key]
    return template.format(**kwargs) if kwargs else template


def translations(key: str) -> tuple[str, ...]:
    """Return each distinct translation for a static UI string."""

    return tuple(dict.fromkeys(strings[key] for strings in _STRINGS.values()))


def label(value: str) -> str:
    """Translate a data-driven case/status/milestone code for display."""

    entry = _LABELS.get(value)
    if entry is not None:
        return entry[get_language()]
    return value.replace("_", " ").title()


def window_label(window_key: str) -> str:
    return _WINDOW_LABELS[get_language()][window_key]


# Order matters: the dropdown is offered in this sequence.
WINDOW_ORDER: tuple[str, ...] = (
    "week",
    "2weeks",
    "month",
    "3month",
    "6month",
    "year",
    "all_time",
)

_WINDOW_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "week": "Last week",
        "2weeks": "Last 2 weeks",
        "month": "Last month",
        "3month": "Last 3 months",
        "6month": "Last 6 months",
        "year": "Last year",
        "all_time": "All time",
    },
    "uk": {
        "week": "Останній тиждень",
        "2weeks": "Останні 2 тижні",
        "month": "Останній місяць",
        "3month": "Останні 3 місяці",
        "6month": "Останні 6 місяців",
        "year": "Останній рік",
        "all_time": "За весь час",
    },
}

# Data-driven codes (case families, form types, subtypes, statuses,
# milestones, expedite channels). Ukrainian values mirror
# packages/case_tracker_core/formatter.py where that vocabulary already
# exists, so the same term reads identically in a channel post and here.
_LABELS: dict[str, dict[str, str]] = {
    "i_131": {"en": "I-131", "uk": "I-131"},
    "i_765": {"en": "I-765", "uk": "I-765"},
    "i_485": {"en": "I-485", "uk": "I-485"},
    "i_130": {"en": "I-130", "uk": "I-130"},
    "i_140": {"en": "I-140", "uk": "I-140"},
    "tps": {"en": "TPS", "uk": "TPS"},
    "ead": {"en": "EAD", "uk": "EAD"},
    "asylum": {"en": "Asylum", "uk": "Притулок"},
    "re_parole": {"en": "Re-parole", "uk": "Re-parole"},
    "u4u_initial": {"en": "U4U initial parole", "uk": "U4U initial parole"},
    "u4u_reparole": {"en": "U4U re-parole", "uk": "Re-parole"},
    "advance_parole": {"en": "Advance Parole", "uk": "Advance Parole"},
    "standalone_ead": {"en": "Standalone EAD", "uk": "Окремий дозвіл на роботу"},
    "tps_ead": {"en": "TPS EAD", "uk": "Дозвіл на роботу за TPS"},
    "family_adjustment": {"en": "Family adjustment", "uk": "Сімейна зміна статусу"},
    "employment_adjustment": {
        "en": "Employment adjustment",
        "uk": "Зміна статусу через працевлаштування",
    },
    "family_petition": {"en": "Family petition", "uk": "Сімейна імміграційна петиція"},
    "employment_petition": {
        "en": "Employment petition",
        "uk": "Імміграційна петиція через працевлаштування",
    },
    "other": {"en": "Other", "uk": "Інше"},
    "unknown": {"en": "Unknown", "uk": "Невідомо"},
    "pending": {"en": "Pending", "uk": "На розгляді"},
    "conditional_approval": {"en": "Conditional approval", "uk": "Умовне схвалення"},
    "payment_submitted": {"en": "Payment submitted", "uk": "Платіж надіслано"},
    "payment_received": {"en": "Payment received", "uk": "Платіж отримано"},
    "approved": {"en": "Approved", "uk": "Схвалено"},
    "denied": {"en": "Denied", "uk": "Відмовлено"},
    "withdrawn": {"en": "Withdrawn", "uk": "Відкликано"},
    "rfe": {"en": "RFE", "uk": "Запит додаткових доказів (RFE)"},
    "nta": {"en": "NTA", "uk": "Повідомлення про явку до суду (NTA)"},
    "congressional": {"en": "Via Congress member", "uk": "Через представника Конгресу"},
    "self_filed": {"en": "Self-filed", "uk": "Самостійно"},
    "pre_approval": {"en": "Conditional approval", "uk": "Умовне схвалення"},
    "pre_approval_to_approval": {
        "en": "Conditional to final approval",
        "uk": "Від умовного до фінального схвалення",
    },
    "biometrics": {"en": "Biometrics", "uk": "Біометрія"},
    "approval": {"en": "Approval", "uk": "Схвалення"},
    "decision": {"en": "Final decision", "uk": "Остаточне рішення"},
    "adjustment_of_status": {"en": "Adjustment of status", "uk": "Зміна статусу"},
}

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Community Immigration Case Tracker",
        "subtitle": "Processing-time trends from human-reviewed, self-reported case updates.",
        "subheader_about": "What is this?",
        "disclaimer_no_evidence": (
            "⚠️ **Informational purposes only.** This site does not constitute "
            "advice or a guarantee of any kind. **Nothing shown here can be used "
            "as evidence or support for an expedite request or any other "
            "official submission.**"
        ),
        "about_body": (
            "This site tracks how long Uniting for Ukraine cases (TPS, "
            "Re-parole, work permits) are taking, based on updates people "
            "voluntarily share in a Ukrainian community Telegram channel. "
            "It is **not** an official government website and has no "
            "connection to any U.S. government agency.\n\n"
            "This reflects only the subset of cases people chose to "
            "report here — real-world outcomes and timing can differ, "
            "and this is not a complete or representative picture of "
            "overall case processing.\n\n"
            "Every update is checked by a human or matched against dated "
            "screenshots before it's counted. We never collect raw "
            "messages, photos, receipt numbers, or names — only dates "
            "and case types are ever recorded. So far this covers "
            "**{report_count:,}** case updates from "
            "**{case_observation_count:,}** reported cases."
        ),
        "api_unavailable_info": (
            "The public aggregate service is temporarily unavailable. "
            "No private case data is stored in this dashboard."
        ),
        "snapshot_stale": "The latest snapshot is {hours} hours old ({freshness}).",
        "snapshot_fresh": "Snapshot {version} generated {freshness}.",
        "metric_case_observations": "Case observations",
        "metric_decisions_this_week": "Final decisions this week",
        "metric_decisions_this_month": "Final decisions this month",
        "caption_reparole_approval_rule": (
            "For Re-parole, decision counts and processing-time charts include "
            "final approvals only. Conditional approvals are shown separately; "
            "denials and withdrawals remain separate terminal statuses."
        ),
        "source_selector_label": "Data source",
        "source_published": "Historic data",
        "source_self_tracked": "Self-tracked cases",
        "source_all": "All community data",
        "source_provenance": (
            "{total:,} case observations: {published:,} published, "
            "{self_tracked:,} self-tracked."
        ),
        "subheader_filing_to_decision": "Filing to final decision by case type",
        "metric_tps_average": "TPS average",
        "metric_tps_median": "TPS median",
        "metric_tps_cases": "TPS cases",
        "metric_reparole_average": "Re-parole average",
        "metric_reparole_median": "Re-parole median",
        "metric_reparole_cases": "Re-parole cases",
        "metric_ead_average": "EAD average",
        "metric_ead_median": "EAD median",
        "metric_ead_cases": "EAD cases",
        "tab_speed": "Processing speed",
        "tab_cases": "Cases",
        "tab_expedite": "Expedite impact",
        "tab_estimates": "My case estimate",
        "tab_personal": "Community self-tracking",
        "tab_tps_decisions": "TPS decisions",
        "tab_how_it_works": "How it works",
        "tps_decisions_intro": (
            "Termination notices published during the current Trump administration, "
            "listed in Federal Register publication order."
        ),
        "tps_decisions_date_note": (
            "The expiration column shows the TPS expiration date DHS was reviewing, "
            "not necessarily the date a termination took effect. Court orders and later "
            "notices can change the practical result. Haiti's July 2025 notice was "
            "superseded, so both official notices are listed."
        ),
        "tps_column_country": "Country / designation",
        "tps_column_start": "TPS began",
        "tps_column_expiration": "Expiration reviewed",
        "tps_column_notice": "Notice published",
        "tps_column_timing": "Notice timing",
        "tps_column_source": "Official notice",
        "tps_source_label": "Federal Register",
        "tps_timing_before": "{days} days before expiration",
        "tps_timing_after": "{days} days after expiration",
        "tps_timing_same_day": "Same day",
        "tps_superseded_suffix": " — superseded notice",
        "tps_decisions_footer": "Last verified against the Federal Register: September 4, 2026.",
        "tps_country_afghanistan": "Afghanistan",
        "tps_country_cameroon": "Cameroon",
        "tps_country_nepal": "Nepal",
        "tps_country_honduras": "Honduras",
        "tps_country_nicaragua": "Nicaragua",
        "tps_country_haiti": "Haiti",
        "tps_country_venezuela_2023": "Venezuela — 2023 designation",
        "tps_country_venezuela_2021": "Venezuela — 2021 designation",
        "tps_country_syria": "Syria",
        "tps_country_south_sudan": "South Sudan",
        "tps_country_burma": "Burma (Myanmar)",
        "tps_country_ethiopia": "Ethiopia",
        "tps_country_somalia": "Somalia",
        "tps_country_yemen": "Yemen",
        "join_button": "Join",
        "how_title": "How your message becomes community statistics",
        "how_intro": (
            "Your report helps show real processing times for Re-parole, TPS, "
            "and EAD without publishing your personal information.\n\n"
            "1. **You describe the case in your own words** in the Telegram bot.\n"
            "2. **Google Gemini analyzes the text** and identifies the form, "
            "status, dates, and case milestones.\n"
            "3. **The bot shows you a clear summary** so you can check the result.\n"
            "4. **Only structured case facts are saved** after confirmation.\n"
            "5. **The dashboard combines many reports** into community-wide trends."
        ),
        "how_expected_title": "What we expect you to send",
        "how_expected_intro": (
            "Write naturally in one message. You do not need a special format. "
            "For example:"
        ),
        "how_expected_example": (
            "Filed I-131 for Re-parole on February 15, 2025.\n"
            "Biometrics were on March 11.\n"
            "On April 2 we contacted a Congress member about expediting.\n"
            "Conditional approval arrived on July 24.\n"
            "Final approval arrived on January 30, 2026.\n"
            "There are two applicants in our family."
        ),
        "how_confirmation_title": "What the bot shows for confirmation",
        "how_confirmation_intro": (
            "The wording may vary, but the confirmation will look approximately like this:"
        ),
        "how_confirmation_example": (
            "**Form:** I-131\n\n**Case type:** Re-parole\n\n"
            "**Status:** Approved\n\n**Applicants:** 2\n\n"
            "**Filed:** February 15, 2025\n\n"
            "**Biometrics:** March 11, 2025\n\n"
            "**Expedite request:** April 2, 2025 — via Congress member\n\n"
            "**Conditional approval:** July 24, 2025\n\n"
            "**Approved:** January 30, 2026"
        ),
        "how_stored_title": "What is saved",
        "how_stored_intro": (
            "We save the case facts, not the free-form message. In non-technical "
            "terms, the saved record looks like this:"
        ),
        "how_stored_example": (
            "**Form:** I-131  \n**Case type:** Re-parole  \n"
            "**Status:** Approved  \n**Filed:** February 15, 2025  \n"
            "**Biometrics:** March 11, 2025  \n"
            "**Expedite:** Via Congress member, April 2, 2025  \n"
            "**Conditional approval:** July 24, 2025  \n"
            "**Final approval:** January 30, 2026  \n**Applicants:** 2"
        ),
        "how_not_stored": (
            "The original free-form message is used for analysis, but this project "
            "does not keep it as part of the statistics. Names, dates of birth, "
            "addresses, contact details, A-numbers, and USCIS receipt numbers are "
            "not fields in the saved analytics record. If you save a case for later "
            "updates, the bot may keep a protected reference to your Telegram account "
            "only so it can find your cases; that reference is never shown publicly."
        ),
        "how_pii_title": "Do not send personal information",
        "how_pii_warning": (
            "Remove personal and sensitive information before sending your message. "
            "Automated detection can make mistakes."
        ),
        "how_pii_intro": (
            "Here is an example of what **not** to send. Every name, number, address, "
            "and date below is fictional:"
        ),
        "how_pii_example": (
            "My name is John Example Doe.\n"
            "Date of birth: January 1, 1900.\n"
            "Address: 000 Example Street.\n"
            "Email: john@example.invalid.\n"
            "A-number: A000000000.\n"
            "Receipt number: IOE0000000000.\n"
            "Filed I-765 on April 10, 2025.\n"
            "On April 15 I was told that my previous biometrics would be reused.\n"
            "The case was approved on September 1, 2025.\n"
            "The card was produced on September 3, 2025."
        ),
        "how_pii_handling": (
            "If the bot detects personal information, it cancels processing and asks "
            "you to remove it and submit the description again. Detection is not "
            "perfect. If personal information is not detected, the full message may "
            "be processed by Google Gemini during analysis. You should therefore "
            "remove it yourself before sending anything."
        ),
        "how_pii_extracted_title": "What would be extracted from that message",
        "how_pii_extracted_intro": (
            "If the personal information was not detected automatically, Gemini may "
            "analyze the full message, but only these case facts are extracted for "
            "the saved analytics record:"
        ),
        "how_pii_extracted_example": (
            "**Form:** I-765  \n**Case type:** EAD  \n"
            "**EAD basis:** Not specified  \n**Status:** Approved  \n"
            "**Filed:** April 10, 2025  \n"
            "**Biometrics reused:** April 15, 2025  \n"
            "**Approved:** September 1, 2025  \n"
            "**Card produced:** September 3, 2025  \n**Applicants:** 1"
        ),
        "how_pii_excluded": (
            "The fictional name, date of birth, address, email, A-number, receipt "
            "number, and original message are not included in the structured analytics "
            "record."
        ),
        "how_disclaimer_title": "Important: automated analysis and age requirement",
        "how_disclaimer_body": (
            "This service is only for people aged 18 or older. The Telegram bot uses "
            "Google Gemini as a technical tool to turn free-form text into structured "
            "case facts. The analysis is automated and may contain errors.\n\n"
            "The bot is not USCIS and does not provide legal advice. Do not rely on "
            "its output to determine your rights, deadlines, or next steps. Check all "
            "recognized information before confirming it and use official USCIS "
            "sources or a qualified professional when appropriate.\n\n"
            "We do not guarantee the accuracy, completeness, or availability of the "
            "automated analysis. To the extent permitted by law, the project authors "
            "and administrators are not responsible for decisions or losses resulting "
            "from use of the automated output."
        ),
        "subheader_recent_decisions": "Recent final decisions",
        "metric_last_7_days": "Last 7 days",
        "metric_previous_calendar_week": "Previous calendar week",
        "metric_current_week": "Current week",
        "metric_current_month": "Current month",
        "subheader_recent_pace": "Recent pace by case type",
        "caption_recent_pace": (
            "Bars show how many decisions happened; the line shows how long they "
            "took. A triangle marks a period that was notably faster or slower "
            "than the recent periods before it."
        ),
        "granularity_label": "Granularity",
        "granularity_monthly": "Monthly",
        "granularity_weekly": "Weekly",
        "duration_label_weighted": "Average days (weighted)",
        "duration_label_median": "Median days",
        "caption_monthly_weighted": (
            "Monthly points are an average of the weekly numbers. Switch to "
            "Weekly to see the exact typical value for each week."
        ),
        "no_recent_decisions_for": "No recent decision samples are available yet for {title}.",
        "decisions_series_name": "Decisions",
        "signal_slower": "Slower",
        "signal_faster": "Faster",
        "signal_stable": "Stable",
        "yaxis_decisions": "Decisions",
        "caption_flagged_periods": "Flagged periods, exact figures:",
        "column_period": "Period",
        "column_days": "Days",
        "column_signal": "Signal",
        "column_change": "Change",
        "column_case_type": "Case type",
        "subheader_filed_vintage": "Which filing vintage is being approved right now",
        "window_label": "Time window",
        "chart_title_filed_cohort": "Filed month of cases decided in the {window}",
        "chart_title_filed_cohort_all_time": "Filed month of all decided cases",
        "info_no_filed_cohort": (
            "Not enough recent decisions are available yet to show a filing-month "
            "breakdown."
        ),
        "caption_filed_cohort": (
            "Shows when the cases decided recently were originally filed. This "
            "is not a chance-of-approval number — it leaves out cases from the "
            "same month that are still waiting."
        ),
        "column_filed_month": "Filed month",
        "column_count": "Count",
        "metric_filed_cohort_total": "{case_type} total",
        "subheader_typical_time": "Typical time from filing",
        "info_no_milestone_samples": "No complete filing-to-milestone samples are available yet.",
        "typical_wait_sentence": (
            "**{family}**: most reported cases are decided within "
            "**{low}–{high} days** of filing (25th–75th percentile, "
            "{count} cases)."
        ),
        "typical_wait_unavailable": "**{family}**: not enough decided cases yet to estimate a typical range.",
        "column_milestone": "Milestone",
        "column_average_days": "Average days",
        "column_median_days": "Median days",
        "column_first_quartile": "25th percentile",
        "column_third_quartile": "75th percentile",
        "column_cases": "Cases",
        "subheader_weekly_trend": "Weekly processing-time trend",
        "info_no_weekly_trend": "Weekly trends will appear when dated milestones are available.",
        "column_week": "Week",
        "case_type_label": "Case type",
        "milestone_label": "Milestone",
        "measure_label": "Measure",
        "chart_title_trend": "{family}: filing to {milestone}",
        "caption_trend": (
            "A line going up means cases have recently been taking longer to "
            "reach this step. Hover over a point to see how many cases it's "
            "based on."
        ),
        "subheader_pace_signals": "Recent pace signals",
        "info_no_pace_signals": "At least two populated weeks are needed to flag a change.",
        "column_latest_week": "Latest week",
        "column_latest_median": "Latest median",
        "column_prior_baseline": "Prior-week baseline",
        "column_latest_cases": "Latest cases",
        "caption_pace_signals": (
            "Compares the most recent week to the few weeks before it. A "
            "change bigger than 15% is flagged as Slower or Faster."
        ),
        "chart_title_reports_by_month": "Reports by month",
        "chart_title_decisions_by_month": "Final decisions by month",
        "column_reported_month": "Reported month",
        "column_decision_month": "Decision month",
        "info_no_breakdown_data": "No data is available for this breakdown yet.",
        "caption_reports_by_month": "How many case updates were reported in each month.",
        "caption_decisions_by_month": "How many final decisions (approved or denied) happened in each month.",
        "chart_title_reports_by_form": "Reports by application type",
        "chart_title_reports_by_subtype": "Reports by case subtype",
        "column_form": "Form",
        "column_case_subtype": "Case subtype",
        "chart_title_status_distribution": "Current status distribution",
        "column_current_status": "Current status",
        "caption_reports_by_form": "Which application type each reported case is about.",
        "caption_reports_by_subtype": "A more specific breakdown of the case types above.",
        "caption_status_distribution": "Where all reported cases currently stand (pending, approved, denied, etc.).",
        "subheader_expedite_comparison": "Processing time with and without reported expedite",
        "info_no_expedite_comparison": "No complete expedite comparison samples are available yet.",
        "column_expedite_median": "Expedite median",
        "column_expedite_average": "Expedite average",
        "column_expedite_cases": "Expedite cases",
        "column_no_expedite_median": "No expedite median",
        "column_no_expedite_average": "No expedite average",
        "column_no_expedite_cases": "No expedite cases",
        "column_median_difference": "Median difference",
        "monthly_decision_chart_title": "{family}: time to final decision by month",
        "monthly_decision_no_samples": "No monthly {family} decision samples are available yet.",
        "caption_monthly_decision_chart": (
            "Median days from filing to a final decision, by the month the "
            "decision happened, split by whether an expedite was reported."
        ),
        "metric_expedite_requests": "Reported expedite requests",
        "metric_reports_with_expedite": "Reports with expedite",
        "chart_title_expedite_by_channel": "Reported expedite requests by channel",
        "column_channel": "Channel",
        "info_expedite_disclaimer": (
            "This is a comparison, not proof that expediting causes a faster "
            "decision — expedited cases may simply differ in other ways, like "
            "urgency or the evidence provided."
        ),
        "caption_personal_tab": (
            "Anonymous, aggregate-only counts from the separate personal "
            "tracking bot. Names, comments, receipt numbers, and Telegram "
            "identities are never collected for this feature."
        ),
        "info_no_personal_data": "Community self-tracking aggregates are not available yet.",
        "metric_self_tracked_submissions": "Self-tracked submissions",
        "metric_median_wait_pending": "Median wait so far (pending)",
        "chart_title_self_tracked_by_form": "Self-tracked submissions by form",
        "chart_title_self_tracked_status": "Self-tracked current status distribution",
        "chart_title_self_tracked_by_month": "Self-tracked submissions by filing month",
        "caption_self_tracked_by_form": "Which form the self-tracked submissions are about.",
        "caption_self_tracked_status": "Current status of the self-tracked submissions.",
        "caption_self_tracked_by_month": "When the self-tracked submissions were filed.",
        "caption_personal_generated": "Snapshot generated {generated_at}.",
        "days_value": "{value} days",
        "days_not_available": "Not available",
        "subheader_how_to_interpret": "Good to know before you read the charts",
        "how_to_interpret_body": (
            "- This is community-reported data from a subset of people who chose to "
            "share updates, not an official or complete sample — treat trends as a "
            "general sense of pace, not a guarantee, and real outcomes may differ.\n"
            "- This site is informational only: nothing here should be used as evidence "
            "or support for an expedite request or any other official submission.\n"
            "- If one report covers a family (e.g. \"3 of us got approved\"), all 3 "
            "cases count.\n"
            "- Only reviewed community reports are counted, and only ones with clear, "
            "non-conflicting dates.\n"
            "- Small weeks/months can look noisy — a couple of unusual cases can swing "
            "the number.\n"
            "- We never collect or store private details in the first place — no "
            "messages, photos, receipt numbers, or names are ever gathered.\n"
        ),
        "refresh_countdown_before": "Data refresh will happen in",
        "refresh_countdown_after": "— reopen this page after that to check.",
        "heatmap_no_expedite": "No reported expedite",
        "heatmap_expedite": "Reported expedite",
        "subheader_case_estimates": "Enter your filed date to see similar cases",
        "caption_case_estimates": (
            "This compares your filed date with other reported cases filed "
            "around the same time. It's a rough estimate from community "
            "data, not a prediction of your own outcome."
        ),
        "filed_date_label": "Date you filed",
        "window_1week_label": "± 1 week",
        "window_1month_label": "± 1 month",
        "window_3month_label": "± 3 months",
        "estimates_window_heading": "Cases filed within {window} of your date",
        "estimates_no_data": "No reported cases were filed in this window yet — try a wider window.",
        "estimates_approved_count": "Approved",
        "estimates_pending_count": "Still pending",
        "estimates_denied_count": "Denied",
        "estimates_pending_wait_median": "Median wait so far (pending cases)",
        "estimates_approved_wait_median": "Median time to approval (already decided)",
        "estimates_column_type": "Case type",
        "estimates_pick_date_prompt": "Pick a filed date above to see estimates.",
    },
    "uk": {
        "title": "Спільнотний трекер імміграційних справ",
        "subtitle": (
            "Тенденції термінів розгляду на основі перевірених людиною, "
            "самостійно поданих оновлень справ."
        ),
        "subheader_about": "Що це таке?",
        "disclaimer_no_evidence": (
            "⚠️ **Виключно в інформаційних цілях.** Цей сайт не є порадою чи "
            "гарантією жодного роду. **Нічого з показаного тут не можна "
            "використовувати як доказ чи підтвердження для запиту на "
            "прискорення чи будь-якого іншого офіційного звернення.**"
        ),
        "about_body": (
            "Цей сайт відстежує, скільки часу займають справи Uniting for "
            "Ukraine (TPS, Re-parole, дозволи на роботу), на основі "
            "оновлень, якими люди добровільно діляться в україномовному "
            "спільнотному каналі в Telegram. Це **не** офіційний "
            "державний сайт і не має жодного зв'язку з жодним державним "
            "органом США.\n\n"
            "Тут відображено лише ту частину справ, про яку люди "
            "вирішили розповісти, — реальні результати й терміни можуть "
            "відрізнятися, і це не повна чи репрезентативна картина "
            "загального розгляду справ.\n\n"
            "Кожне оновлення перевіряє людина або звіряє з датованими "
            "скриншотами, перш ніж воно потрапляє в статистику. Ми "
            "ніколи не збираємо самі повідомлення, фото, номери "
            "квитанцій чи імена — лише дати й типи справ. Наразі тут "
            "зібрано **{report_count:,}** оновлень по **{case_observation_count:,}** "
            "заявлених справах."
        ),
        "api_unavailable_info": (
            "Публічний агрегований сервіс тимчасово недоступний. "
            "Ці дані не містять приватної інформації про справи."
        ),
        "snapshot_stale": "Останній знімок даних має вік {hours} год. ({freshness}).",
        "snapshot_fresh": "Знімок {version}, згенеровано {freshness}.",
        "metric_case_observations": "Спостереження по справах",
        "metric_decisions_this_week": "Рішення цього тижня",
        "metric_decisions_this_month": "Рішення цього місяця",
        "caption_reparole_approval_rule": (
            "Для Re-parole у кількості рішень і графіках строків враховуються "
            "лише фінальні схвалення. Умовні схвалення показані окремо; "
            "відмови та відкликання залишаються окремими фінальними статусами."
        ),
        "source_selector_label": "Джерело даних",
        "source_published": "Історичні дані",
        "source_self_tracked": "Самостійно додані дані",
        "source_all": "Усі дані спільноти",
        "source_provenance": (
            "{total:,} спостережень по справах: {published:,} опубліковано, "
            "{self_tracked:,} з особистого відстеження."
        ),
        "subheader_filing_to_decision": "Від подання до остаточного рішення за типом кейсу",
        "metric_tps_average": "TPS, середнє",
        "metric_tps_median": "TPS, медіана",
        "metric_tps_cases": "TPS, справ",
        "metric_reparole_average": "Re-parole, середнє",
        "metric_reparole_median": "Re-parole, медіана",
        "metric_reparole_cases": "Re-parole, справ",
        "metric_ead_average": "EAD, середнє",
        "metric_ead_median": "EAD, медіана",
        "metric_ead_cases": "EAD, справ",
        "tab_speed": "Швидкість розгляду",
        "tab_cases": "Справи",
        "tab_expedite": "Вплив прискорення",
        "tab_estimates": "Оцінка моєї справи",
        "tab_personal": "Особисте відстеження спільноти",
        "tab_tps_decisions": "Рішення щодо TPS",
        "subheader_recent_decisions": "Нещодавні остаточні рішення",
        "metric_last_7_days": "Останні 7 днів",
        "metric_previous_calendar_week": "Попередній календарний тиждень",
        "metric_current_week": "Поточний тиждень",
        "metric_current_month": "Поточний місяць",
        "tab_how_it_works": "Як це працює",
        "tps_decisions_intro": (
            "Повідомлення про припинення TPS, опубліковані за чинної адміністрації "
            "Трампа, у порядку публікації у Federal Register."
        ),
        "tps_decisions_date_note": (
            "У колонці завершення вказано дату закінчення TPS, яку розглядав DHS, "
            "а не обов’язково дату набрання припиненням чинності. Судові рішення та "
            "пізніші повідомлення можуть змінити практичний результат. Повідомлення "
            "щодо Гаїті за липень 2025 року було замінене, тому наведено обидва."
        ),
        "tps_column_country": "Країна / призначення",
        "tps_column_start": "Початок TPS",
        "tps_column_expiration": "Розглянута дата завершення",
        "tps_column_notice": "Дата публікації",
        "tps_column_timing": "Час публікації",
        "tps_column_source": "Офіційне повідомлення",
        "tps_source_label": "Federal Register",
        "tps_timing_before": "За {days} дн. до завершення",
        "tps_timing_after": "Через {days} дн. після завершення",
        "tps_timing_same_day": "Того самого дня",
        "tps_superseded_suffix": " — замінене повідомлення",
        "tps_decisions_footer": "Остання перевірка за Federal Register: 4 вересня 2026 року.",
        "tps_country_afghanistan": "Афганістан",
        "tps_country_cameroon": "Камерун",
        "tps_country_nepal": "Непал",
        "tps_country_honduras": "Гондурас",
        "tps_country_nicaragua": "Нікарагуа",
        "tps_country_haiti": "Гаїті",
        "tps_country_venezuela_2023": "Венесуела — призначення 2023 року",
        "tps_country_venezuela_2021": "Венесуела — призначення 2021 року",
        "tps_country_syria": "Сирія",
        "tps_country_south_sudan": "Південний Судан",
        "tps_country_burma": "Бірма (М’янма)",
        "tps_country_ethiopia": "Ефіопія",
        "tps_country_somalia": "Сомалі",
        "tps_country_yemen": "Ємен",
        "join_button": "Долучитися",
        "how_title": "Як ваше повідомлення стає частиною статистики",
        "how_intro": (
            "Ваше повідомлення допомагає показувати реальні строки розгляду "
            "Re-parole, TPS та EAD — без публікації особистої інформації.\n\n"
            "1. **Ви описуєте справу звичайними словами** в Telegram-боті.\n"
            "2. **Google Gemini аналізує текст** і знаходить форму, статус, дати "
            "та етапи справи.\n"
            "3. **Бот показує зрозумілий підсумок**, щоб ви могли все перевірити.\n"
            "4. **Після підтвердження зберігаються лише структуровані факти.**\n"
            "5. **Дашборд об’єднує багато повідомлень** у загальну статистику."
        ),
        "how_expected_title": "Яке повідомлення ми очікуємо",
        "how_expected_intro": (
            "Напишіть усе природно одним повідомленням. Спеціальний формат не "
            "потрібен. Наприклад:"
        ),
        "how_expected_example": (
            "Подали I-131 на Re-parole 15 лютого 2025 року.\n"
            "Біометрія була 11 березня.\n"
            "2 квітня звернулися до конгресмена щодо пришвидшення.\n"
            "Умовне схвалення отримали 24 липня.\n"
            "Фінальне схвалення — 30 січня 2026 року.\n"
            "У сім’ї двоє аплікантів."
        ),
        "how_confirmation_title": "Що бот покаже для підтвердження",
        "how_confirmation_intro": (
            "Формулювання може трохи відрізнятися, але підсумок виглядатиме "
            "приблизно так:"
        ),
        "how_confirmation_example": (
            "**Форма:** I-131\n\n**Тип справи:** Re-parole\n\n"
            "**Статус:** схвалено\n\n**Кількість аплікантів:** 2\n\n"
            "**Подано:** 15 лютого 2025 року\n\n"
            "**Біометрія:** 11 березня 2025 року\n\n"
            "**Запит на пришвидшення:** 2 квітня 2025 року — через конгресмена\n\n"
            "**Умовне схвалення:** 24 липня 2025 року\n\n"
            "**Схвалено:** 30 січня 2026 року"
        ),
        "how_stored_title": "Що буде збережено",
        "how_stored_intro": (
            "Ми зберігаємо факти про справу, а не початкове повідомлення. "
            "Звичайною мовою збережений запис виглядає так:"
        ),
        "how_stored_example": (
            "**Форма:** I-131  \n**Тип справи:** Re-parole  \n"
            "**Статус:** схвалено  \n**Подано:** 15 лютого 2025 року  \n"
            "**Біометрія:** 11 березня 2025 року  \n"
            "**Пришвидшення:** через конгресмена, 2 квітня 2025 року  \n"
            "**Умовне схвалення:** 24 липня 2025 року  \n"
            "**Фінальне схвалення:** 30 січня 2026 року  \n"
            "**Кількість аплікантів:** 2"
        ),
        "how_not_stored": (
            "Початковий текст використовується для аналізу, але наш проєкт не "
            "зберігає його як частину статистики. Ім’я, дата народження, адреса, "
            "контактні дані, A-number і номер квитанції USCIS не є полями "
            "збереженого аналітичного запису. Якщо ви зберігаєте справу для "
            "подальших оновлень, бот може зберігати захищене посилання на ID "
            "Telegram-акаунта лише для пошуку ваших справ; воно ніколи не "
            "показується публічно."
        ),
        "how_pii_title": "Не надсилайте особисті дані",
        "how_pii_warning": (
            "Видаліть особисту й конфіденційну інформацію перед надсиланням. "
            "Автоматична перевірка може помилятися."
        ),
        "how_pii_intro": (
            "Ось приклад того, що **не потрібно** надсилати. Усі імена, номери, "
            "адреси та дати нижче вигадані:"
        ),
        "how_pii_example": (
            "Мене звати John Example Doe.\n"
            "Дата народження: 1 січня 1900 року.\n"
            "Адреса: 000 Example Street.\n"
            "Email: john@example.invalid.\n"
            "A-number: A000000000.\n"
            "Receipt number: IOE0000000000.\n"
            "Подав I-765 10 квітня 2025 року.\n"
            "15 квітня отримав повідомлення, що попередню біометрію буде "
            "використано повторно.\n"
            "Справу схвалили 1 вересня 2025 року.\n"
            "Картку виготовили 3 вересня 2025 року."
        ),
        "how_pii_handling": (
            "Якщо бот помітить особисту інформацію, він скасує обробку та "
            "попросить видалити її й надіслати опис повторно. Автоматична "
            "перевірка недосконала. Якщо особисту інформацію не буде помічено, "
            "повний текст може бути оброблений Google Gemini під час аналізу. "
            "Тому найнадійніше — видалити її самостійно ще до надсилання."
        ),
        "how_pii_extracted_title": "Що буде витягнуто з такого повідомлення",
        "how_pii_extracted_intro": (
            "Якщо особисту інформацію не було помічено автоматично, Gemini може "
            "проаналізувати повний текст, але для збереженого аналітичного запису "
            "буде витягнуто лише такі факти про справу:"
        ),
        "how_pii_extracted_example": (
            "**Форма:** I-765  \n**Тип справи:** EAD  \n"
            "**Підстава EAD:** не вказана  \n**Статус:** схвалено  \n"
            "**Подано:** 10 квітня 2025 року  \n"
            "**Біометрію використано повторно:** 15 квітня 2025 року  \n"
            "**Схвалено:** 1 вересня 2025 року  \n"
            "**Картку виготовлено:** 3 вересня 2025 року  \n"
            "**Кількість аплікантів:** 1"
        ),
        "how_pii_excluded": (
            "Вигадані ім’я, дата народження, адреса, email, A-number, номер "
            "квитанції та початковий текст не входять до структурованого "
            "аналітичного запису."
        ),
        "how_disclaimer_title": "Важливо: автоматичний аналіз і вимога 18+",
        "how_disclaimer_body": (
            "Сервіс призначений лише для осіб віком від 18 років. Telegram-бот "
            "використовує Google Gemini як технічний інструмент, щоб перетворити "
            "довільний текст на структуровані факти про справу. Аналіз виконується "
            "автоматично та може містити помилки.\n\n"
            "Бот не є сервісом USCIS і не надає юридичних консультацій. Не "
            "покладайтеся на його результат для визначення ваших прав, строків або "
            "подальших дій. Перевірте всі розпізнані дані перед підтвердженням, а "
            "за потреби використовуйте офіційні джерела USCIS або зверніться до "
            "кваліфікованого фахівця.\n\n"
            "Ми не гарантуємо точність, повноту або доступність автоматичного "
            "аналізу. У межах, дозволених законом, автори й адміністратори проєкту "
            "не відповідають за рішення або збитки, що виникли через використання "
            "автоматичного результату."
        ),
        "subheader_recent_pace": "Нещодавній темп за типом справи",
        "caption_recent_pace": (
            "Стовпці показують, скільки було рішень; лінія — скільки часу вони "
            "займали. Трикутник позначає період, помітно швидший або повільніший "
            "за попередні."
        ),
        "granularity_label": "Деталізація",
        "granularity_monthly": "Місячна",
        "granularity_weekly": "Тижнева",
        "duration_label_weighted": "Середні дні (зважені)",
        "duration_label_median": "Медіана днів",
        "caption_monthly_weighted": (
            "Місячні точки — це середнє за тижневими показниками. Перемкніть на "
            "тижневу деталізацію, щоб побачити точне типове значення за кожен "
            "тиждень."
        ),
        "no_recent_decisions_for": "Ще немає нещодавніх рішень для {title}.",
        "decisions_series_name": "Рішення",
        "signal_slower": "Повільніше",
        "signal_faster": "Швидше",
        "signal_stable": "Стабільно",
        "yaxis_decisions": "Рішення",
        "caption_flagged_periods": "Позначені періоди, точні цифри:",
        "column_period": "Період",
        "column_days": "Дні",
        "column_signal": "Сигнал",
        "column_change": "Зміна",
        "column_case_type": "Тип справи",
        "subheader_filed_vintage": "Справи якого періоду подання схвалюють зараз",
        "window_label": "Часовий діапазон",
        "chart_title_filed_cohort": "Місяць подання справ, вирішених за {window}",
        "chart_title_filed_cohort_all_time": "Місяць подання всіх вирішених справ",
        "info_no_filed_cohort": (
            "Ще недостатньо нещодавніх рішень, щоб показати розподіл за "
            "місяцем подання."
        ),
        "caption_filed_cohort": (
            "Показує, коли було подано справи, вирішені нещодавно. Це не "
            "показник шансу на схвалення — він не враховує справи того самого "
            "місяця, які досі на розгляді."
        ),
        "column_filed_month": "Місяць подання",
        "column_count": "Кількість",
        "metric_filed_cohort_total": "Усього, {case_type}",
        "subheader_typical_time": "Типовий час від подання",
        "info_no_milestone_samples": "Ще немає повних вибірок від подання до етапу.",
        "typical_wait_sentence": (
            "**{family}**: більшість заявлених справ вирішуються протягом "
            "**{low}–{high} днів** від подання (25-й–75-й перцентиль, "
            "{count} справ)."
        ),
        "typical_wait_unavailable": "**{family}**: ще недостатньо вирішених справ, щоб оцінити типовий діапазон.",
        "column_milestone": "Етап",
        "column_average_days": "Середні дні",
        "column_median_days": "Медіана днів",
        "column_first_quartile": "25-й перцентиль",
        "column_third_quartile": "75-й перцентиль",
        "column_cases": "Справ",
        "subheader_weekly_trend": "Тижнева динаміка часу обробки",
        "info_no_weekly_trend": "Тижневі тренди з'являться, коли будуть дати етапів.",
        "column_week": "Тиждень",
        "case_type_label": "Тип справи",
        "milestone_label": "Етап",
        "measure_label": "Показник",
        "chart_title_trend": "{family}: від подання до {milestone}",
        "caption_trend": (
            "Зростання лінії означає, що справи останнім часом доходять до "
            "цього етапу довше. Наведіть курсор на точку, щоб побачити, скільки "
            "справ враховано."
        ),
        "subheader_pace_signals": "Нещодавні сигнали темпу",
        "info_no_pace_signals": "Потрібно щонайменше два заповнені тижні, щоб позначити зміну.",
        "column_latest_week": "Останній тиждень",
        "column_latest_median": "Остання медіана",
        "column_prior_baseline": "Базове значення попереднього тижня",
        "column_latest_cases": "Справ за останній тиждень",
        "caption_pace_signals": (
            "Порівнює останній тиждень із кількома попередніми. Велика зміна "
            "(понад 15%) позначається як «Повільніше» або «Швидше»."
        ),
        "chart_title_reports_by_month": "Звіти за місяцями",
        "chart_title_decisions_by_month": "Остаточні рішення за місяцями",
        "column_reported_month": "Місяць звіту",
        "column_decision_month": "Місяць рішення",
        "info_no_breakdown_data": "Дані для цього розподілу ще недоступні.",
        "caption_reports_by_month": "Скільки оновлень по справах було подано щомісяця.",
        "caption_decisions_by_month": "Скільки остаточних рішень (схвалено чи відмовлено) було щомісяця.",
        "chart_title_reports_by_form": "Звіти за типом заяви",
        "chart_title_reports_by_subtype": "Звіти за підтипом справи",
        "column_form": "Форма",
        "column_case_subtype": "Підтип справи",
        "chart_title_status_distribution": "Розподіл поточних статусів",
        "column_current_status": "Поточний статус",
        "caption_reports_by_form": "На який тип заяви подана кожна заявлена справа.",
        "caption_reports_by_subtype": "Детальніший розподіл типів справ вище.",
        "caption_status_distribution": "На якому етапі зараз перебувають усі заявлені справи (на розгляді, схвалено, відмовлено тощо).",
        "subheader_expedite_comparison": "Час обробки з прискоренням і без нього",
        "info_no_expedite_comparison": "Ще немає повних вибірок для порівняння прискорення.",
        "column_expedite_median": "Медіана з прискоренням",
        "column_expedite_average": "Середнє з прискоренням",
        "column_expedite_cases": "Справ з прискоренням",
        "column_no_expedite_median": "Медіана без прискорення",
        "column_no_expedite_average": "Середнє без прискорення",
        "column_no_expedite_cases": "Справ без прискорення",
        "column_median_difference": "Різниця медіан",
        "monthly_decision_chart_title": "{family}: час до остаточного рішення за місяцями",
        "monthly_decision_no_samples": "Ще немає місячних даних рішень для {family}.",
        "caption_monthly_decision_chart": (
            "Медіанна кількість днів від подання до остаточного рішення, за "
            "місяцем рішення, з розподілом за наявністю заявленого прискорення."
        ),
        "metric_expedite_requests": "Заявлені запити на прискорення",
        "metric_reports_with_expedite": "Звітів із прискоренням",
        "chart_title_expedite_by_channel": "Запити на прискорення за каналом",
        "column_channel": "Канал",
        "info_expedite_disclaimer": (
            "Це порівняння, а не доказ того, що прискорення прискорює рішення "
            "— справи з прискоренням можуть просто відрізнятися іншим: "
            "терміновістю чи наданими доказами."
        ),
        "caption_personal_tab": (
            "Анонімні, лише агреговані підрахунки з окремого бота особистого "
            "відстеження. Імена, коментарі, номери квитанцій та "
            "ідентифікатори Telegram для цієї функції ніколи не збираються."
        ),
        "info_no_personal_data": "Агреговані дані особистого відстеження ще недоступні.",
        "metric_self_tracked_submissions": "Самостійно відстежені заявки",
        "metric_median_wait_pending": "Медіанне очікування дотепер (на розгляді)",
        "chart_title_self_tracked_by_form": "Самостійно відстежені заявки за формою",
        "chart_title_self_tracked_status": "Розподіл поточних статусів самостійного відстеження",
        "chart_title_self_tracked_by_month": "Самостійно відстежені заявки за місяцем подання",
        "caption_self_tracked_by_form": "На яку форму подані самостійно відстежені заявки.",
        "caption_self_tracked_status": "Поточний статус самостійно відстежених заявок.",
        "caption_self_tracked_by_month": "Коли були подані самостійно відстежені заявки.",
        "caption_personal_generated": "Знімок згенеровано {generated_at}.",
        "days_value": "{value} дн.",
        "days_not_available": "Немає даних",
        "subheader_how_to_interpret": "Корисно знати перед переглядом графіків",
        "how_to_interpret_body": (
            "- Це дані спільноти від частини людей, які вирішили поділитися "
            "оновленнями, а не офіційна чи повна вибірка — сприймайте тенденції як "
            "загальне уявлення про темп, а не гарантію; реальні результати можуть "
            "відрізнятися.\n"
            "- Цей сайт має виключно інформаційний характер: ніщо тут не можна "
            "використовувати як доказ чи підтвердження для запиту на прискорення чи "
            "будь-якого іншого офіційного звернення.\n"
            "- Якщо один звіт стосується родини (наприклад, «3 з нас отримали "
            "схвалення»), враховуються всі 3 справи.\n"
            "- Враховуються лише перевірені звіти спільноти, і лише ті, що мають чіткі, "
            "несуперечливі дати.\n"
            "- Малі тижні чи місяці можуть виглядати «шумними» — кілька нетипових "
            "справ можуть сильно змінити цифру.\n"
            "- Ми ніколи не збираємо й не зберігаємо приватні дані: жодні повідомлення, "
            "фото, номери квитанцій чи імена не потрапляють до системи.\n"
        ),
        "refresh_countdown_before": "Оновлення даних відбудеться через",
        "refresh_countdown_after": "— поверніться на цю сторінку пізніше, щоб перевірити.",
        "heatmap_no_expedite": "Без заявленого прискорення",
        "heatmap_expedite": "Із заявленим прискоренням",
        "subheader_case_estimates": "Введіть дату подання, щоб побачити схожі справи",
        "caption_case_estimates": (
            "Тут ваша дата подання порівнюється з іншими заявленими справами, "
            "поданими приблизно в той самий час. Це орієнтовна оцінка на основі "
            "даних спільноти, а не прогноз результату саме вашої справи."
        ),
        "filed_date_label": "Дата, коли ви подали справу",
        "window_1week_label": "± 1 тиждень",
        "window_1month_label": "± 1 місяць",
        "window_3month_label": "± 3 місяці",
        "estimates_window_heading": "Справи, подані в межах {window} від вашої дати",
        "estimates_no_data": "У цьому діапазоні ще немає заявлених справ — спробуйте ширший діапазон.",
        "estimates_approved_count": "Схвалено",
        "estimates_pending_count": "Ще на розгляді",
        "estimates_denied_count": "Відмовлено",
        "estimates_pending_wait_median": "Медіанне очікування дотепер (справи на розгляді)",
        "estimates_approved_wait_median": "Медіанний час до схвалення (уже вирішені)",
        "estimates_column_type": "Тип справи",
        "estimates_pick_date_prompt": "Оберіть дату подання вище, щоб побачити оцінку.",
    },
}
