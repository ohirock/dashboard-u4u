# USCIS Community Case Tracker Dashboard

Public Streamlit dashboard for aggregate immigration-case trends.

The dashboard reads only the sanitized snapshot exposed by the Oracle API:

```text
browser -> Streamlit -> Oracle aggregate API -> MongoDB Atlas
```

It does not connect to MongoDB and does not receive Telegram, Gemini, receipt,
message, image, or administrator data.

## Dashboard metrics

- average, median, and quartile processing time from filing to biometrics,
  pre-approval, and approval by case family;
- weekly processing-time trends and descriptive faster/slower signals;
- final-decision counts for the last 7 days, previous week, current week,
  and current month;
- processing-time comparisons for reports with and without expedite activity;
- case mix, status distribution, historic-review progress, and data quality.

Multi-person reports are weighted by their reviewed `reported_case_count`.
Weekly trend output is bounded to the latest 104 populated weeks per case-family
and milestone combination. Expedite comparisons are descriptive correlation,
not a causal estimate.

## Community self-tracking tab

A fifth, independent tab shows anonymized, aggregate-only counts from the
separate personal tracking Telegram bot (submission counts by form type,
status, and filing month, plus pending-wait-days). It is fed by its own
endpoint, `/api/public/personal-dashboard`, entirely separate from the
canonical `/api/public/dashboard` snapshot above — no raw comments,
Telegram identities, or other private fields ever leave the personal-bot's
private MongoDB collection. If the personal bot's storage feature flag is
disabled, this tab shows "not available yet" without affecting the rest of
the page.

## Data refresh

Both the canonical snapshot and the personal-tracking snapshot share the
same 300-second server-side cache (`PAGE_DATA_CACHE_TTL_SECONDS`). A single
"Data refresh will happen in..." countdown is shown once, above all tabs —
not per tab — reflecting whichever of the two caches will expire soonest.
The cache is shared by every visitor (not per-browser-session), so the
countdown shows the same value to everyone and is unaffected by any one
visitor's manual page refresh. The countdown is purely informational: it
never reloads or reruns the page on its own; reopen the page after it
reaches zero to see whether new data arrived.

## Run locally

```powershell
python -m pip install -r requirements.txt
$env:U4U_PUBLIC_API_BASE_URL = "https://141-148-77-229.sslip.io"
python -m streamlit run dashboard.py
```

`U4U_PUBLIC_API_BASE_URL` is optional for the current deployment because the
public Oracle origin is the safe default. It can be overridden in a Streamlit
secret or environment variable without changing code.

## Deployment

Streamlit Community Cloud deploys `dashboard.py` from branch `main`.
No backend credentials are required or permitted.
