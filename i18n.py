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


def t(key: str, **kwargs) -> str:
    """Look up `key` in the current language's string table."""

    template = _STRINGS[get_language()].get(key) or _STRINGS[DEFAULT_LANGUAGE][key]
    return template.format(**kwargs) if kwargs else template


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
    "rfe": {"en": "RFE", "uk": "Запит додаткових доказів (RFE)"},
    "nta": {"en": "NTA", "uk": "Повідомлення про явку до суду (NTA)"},
    "congressional": {"en": "Via Congress member", "uk": "Через представника Конгресу"},
    "self_filed": {"en": "Self-filed", "uk": "Самостійно"},
    "pre_approval": {"en": "Pre-approval", "uk": "Попереднє схвалення"},
    "biometrics": {"en": "Biometrics", "uk": "Біометрія"},
    "approval": {"en": "Approval", "uk": "Схвалення"},
    "decision": {"en": "Final decision", "uk": "Остаточне рішення"},
    "adjustment_of_status": {"en": "Adjustment of status", "uk": "Зміна статусу"},
}

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title": "USCIS Community Case Tracker",
        "subtitle": "Processing-time trends from human-reviewed, self-reported case updates.",
        "subheader_about": "What is this?",
        "about_body": (
            "This site tracks how long Uniting for Ukraine cases (TPS, "
            "Re-parole, work permits) are taking, based on updates people "
            "voluntarily share in a Ukrainian community Telegram channel. "
            "It is **not** an official USCIS website and has no connection "
            "to USCIS or the US government.\n\n"
            "Every update is checked by a human or matched against dated "
            "screenshots before it's counted — never raw messages, photos, "
            "receipt numbers, or names, only dates and case types. So far "
            "this covers **{report_count:,}** case updates from "
            "**{case_observation_count:,}** reported cases."
        ),
        "api_unavailable_info": (
            "The public aggregate service is temporarily unavailable. "
            "No private case data is stored in this dashboard."
        ),
        "snapshot_stale": "The latest snapshot is {hours:.0f} hours old ({freshness}).",
        "snapshot_fresh": "Snapshot {version} generated {freshness}.",
        "metric_case_observations": "Case observations",
        "metric_decisions_this_week": "Final decisions this week",
        "metric_decisions_this_month": "Final decisions this month",
        "subheader_filing_to_decision": "Filing to final decision by benefit",
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
            "**{low:.0f}–{high:.0f} days** of filing (25th–75th percentile, "
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
        "chart_title_reports_by_form": "Reports by USCIS form",
        "chart_title_reports_by_subtype": "Reports by case subtype",
        "column_form": "Form",
        "column_case_subtype": "Case subtype",
        "chart_title_status_distribution": "Current status distribution",
        "column_current_status": "Current status",
        "caption_reports_by_form": "Which USCIS form each reported case is about.",
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
            "tracking bot. No names, comments, receipt numbers, or Telegram "
            "identities are ever included here."
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
        "days_value": "{value:.0f} days",
        "days_not_available": "Not available",
        "subheader_how_to_interpret": "Good to know before you read the charts",
        "how_to_interpret_body": (
            "- This is community-reported data, not an official USCIS sample — treat "
            "trends as a general sense of pace, not a guarantee.\n"
            "- If one report covers a family (e.g. \"3 of us got approved\"), all 3 "
            "cases count.\n"
            "- Only reviewed community reports are counted, and only ones with clear, "
            "non-conflicting dates.\n"
            "- Small weeks/months can look noisy — a couple of unusual cases can swing "
            "the number.\n"
            "- Nothing private is ever shown here: no messages, photos, receipt numbers, "
            "or names.\n"
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
        "title": "Спільнотний трекер справ USCIS",
        "subtitle": (
            "Тенденції термінів розгляду на основі перевірених людиною, "
            "самостійно поданих оновлень справ."
        ),
        "subheader_about": "Що це таке?",
        "about_body": (
            "Цей сайт відстежує, скільки часу займають справи Uniting for "
            "Ukraine (TPS, Re-parole, дозволи на роботу), на основі "
            "оновлень, якими люди добровільно діляться в україномовному "
            "спільнотному каналі в Telegram. Це **не** офіційний сайт "
            "USCIS і не має жодного зв'язку з USCIS чи урядом США.\n\n"
            "Кожне оновлення перевіряє людина або звіряє з датованими "
            "скриншотами, перш ніж воно потрапляє в статистику — сюди "
            "ніколи не потрапляють самі повідомлення, фото, номери "
            "квитанцій чи імена, лише дати й типи справ. Наразі тут "
            "зібрано **{report_count:,}** оновлень по **{case_observation_count:,}** "
            "заявлених справах."
        ),
        "api_unavailable_info": (
            "Публічний агрегований сервіс тимчасово недоступний. "
            "Ці дані не містять приватної інформації про справи."
        ),
        "snapshot_stale": "Останній знімок даних має вік {hours:.0f} год. ({freshness}).",
        "snapshot_fresh": "Знімок {version}, згенеровано {freshness}.",
        "metric_case_observations": "Спостереження по справах",
        "metric_decisions_this_week": "Рішення цього тижня",
        "metric_decisions_this_month": "Рішення цього місяця",
        "subheader_filing_to_decision": "Від подання до остаточного рішення за пільгою",
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
        "subheader_recent_decisions": "Нещодавні остаточні рішення",
        "metric_last_7_days": "Останні 7 днів",
        "metric_previous_calendar_week": "Попередній календарний тиждень",
        "metric_current_week": "Поточний тиждень",
        "metric_current_month": "Поточний місяць",
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
            "**{low:.0f}–{high:.0f} днів** від подання (25-й–75-й перцентиль, "
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
        "chart_title_reports_by_form": "Звіти за формою USCIS",
        "chart_title_reports_by_subtype": "Звіти за підтипом справи",
        "column_form": "Форма",
        "column_case_subtype": "Підтип справи",
        "chart_title_status_distribution": "Розподіл поточних статусів",
        "column_current_status": "Поточний статус",
        "caption_reports_by_form": "На яку форму USCIS подана кожна заявлена справа.",
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
            "відстеження. Тут ніколи не буде імен, коментарів, номерів "
            "квитанцій чи ідентифікаторів Telegram."
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
        "days_value": "{value:.0f} дн.",
        "days_not_available": "Немає даних",
        "subheader_how_to_interpret": "Корисно знати перед переглядом графіків",
        "how_to_interpret_body": (
            "- Це дані спільноти, подані самостійно, а не офіційна вибірка USCIS — "
            "сприймайте тенденції як загальне уявлення про темп, а не гарантію.\n"
            "- Якщо один звіт стосується родини (наприклад, «3 з нас отримали "
            "схвалення»), враховуються всі 3 справи.\n"
            "- Враховуються лише перевірені звіти спільноти, і лише ті, що мають чіткі, "
            "несуперечливі дати.\n"
            "- Малі тижні чи місяці можуть виглядати «шумними» — кілька нетипових "
            "справ можуть сильно змінити цифру.\n"
            "- Тут ніколи не показуються приватні дані: жодних повідомлень, фото, "
            "номерів квитанцій чи імен.\n"
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
