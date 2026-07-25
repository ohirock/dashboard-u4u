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
