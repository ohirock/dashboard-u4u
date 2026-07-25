"""Strict, bounded client for the public aggregate dashboard API."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime
from typing import Any, Self
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, model_validator

PUBLIC_API_URL_ENV = "U4U_PUBLIC_API_BASE_URL"
DEFAULT_PUBLIC_API_BASE_URL = "https://141-148-77-229.sslip.io"
DASHBOARD_PATH = "/api/public/dashboard"
MAX_SNAPSHOT_BYTES = 1_048_576


class PublicDashboardUnavailable(RuntimeError):
    """A sanitized public-snapshot retrieval or validation failure."""


class StrictModel(BaseModel):
    """Immutable API model that rejects accidental contract expansion."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class DashboardCountBucket(StrictModel):
    key: str = Field(min_length=1)
    count: int = Field(ge=0)


class DashboardDurationSummary(StrictModel):
    sample_size: int = Field(ge=0)
    median_days: float | None = None
    first_quartile_days: float | None = None
    third_quartile_days: float | None = None

    @model_validator(mode="after")
    def validate_sample(self) -> Self:
        values = (
            self.median_days,
            self.first_quartile_days,
            self.third_quartile_days,
        )
        if (self.sample_size == 0) != all(value is None for value in values):
            raise ValueError("duration values must match sample availability")
        return self


class DashboardMetrics(StrictModel):
    report_count: int = Field(ge=0)
    reports_by_month: tuple[DashboardCountBucket, ...]
    decisions_by_month: tuple[DashboardCountBucket, ...]
    reports_by_form: tuple[DashboardCountBucket, ...]
    reports_by_subtype: tuple[DashboardCountBucket, ...]
    current_status_distribution: tuple[DashboardCountBucket, ...]
    filing_to_decision: DashboardDurationSummary
    expedite_request_count: int = Field(ge=0)
    expedite_by_channel: tuple[DashboardCountBucket, ...]
    reports_with_expedite: int = Field(ge=0)
    outcomes_with_expedite: tuple[DashboardCountBucket, ...]
    outcomes_without_expedite: tuple[DashboardCountBucket, ...]
    historic_pending_count: int = Field(ge=0)
    historic_reviewed_count: int = Field(ge=0)


class DashboardQuality(StrictModel):
    included_report_count: int = Field(ge=0)
    excluded_report_count: int = Field(ge=0)
    unknown_form_count: int = Field(ge=0)
    unknown_status_count: int = Field(ge=0)
    reports_missing_filed_date: int = Field(ge=0)
    reports_missing_decision_date: int = Field(ge=0)
    conflicting_evidence_count: int = Field(ge=0)


class DashboardFilters(StrictModel):
    supported_form_types: tuple[str, ...]
    supported_statuses: tuple[str, ...]
    min_reported_date: date | None = None
    max_reported_date: date | None = None


class DashboardSnapshot(StrictModel):
    generated_at: datetime
    data_version: int = Field(gt=0)
    filters: DashboardFilters
    metrics: DashboardMetrics
    quality: DashboardQuality

    @model_validator(mode="after")
    def validate_generated_at(self) -> Self:
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("generated_at must include timezone information")
        return self


def public_api_base_url(
    environment: Mapping[str, str],
    *,
    secret_value: str | None = None,
) -> str:
    """Resolve and validate the public API origin without credentials."""

    value = (
        secret_value
        or environment.get(PUBLIC_API_URL_ENV, "")
        or DEFAULT_PUBLIC_API_BASE_URL
    ).strip()
    parts = urlsplit(value)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
    ):
        raise PublicDashboardUnavailable("The public dashboard API URL is invalid.")
    if parts.scheme != "https" and parts.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise PublicDashboardUnavailable("The public dashboard API must use HTTPS.")
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path.rstrip("/"),
            "",
            "",
        )
    )


def fetch_dashboard_snapshot(
    base_url: str,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout_seconds: float = 10.0,
) -> DashboardSnapshot:
    """Fetch, bound, decode, and strictly validate one aggregate snapshot."""

    normalized = public_api_base_url({PUBLIC_API_URL_ENV: base_url})
    if timeout_seconds <= 0 or timeout_seconds > 30:
        raise ValueError("timeout_seconds must be greater than 0 and at most 30")
    request = Request(
        normalized + DASHBOARD_PATH,
        headers={"Accept": "application/json"},
        method="GET",
    )
    try:
        response = opener(request, timeout=timeout_seconds)
        with response:
            length = response.headers.get("Content-Length")
            if length is not None and int(length) > MAX_SNAPSHOT_BYTES:
                raise PublicDashboardUnavailable("The dashboard snapshot is too large.")
            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type.lower():
                raise PublicDashboardUnavailable(
                    "The dashboard API returned an invalid content type."
                )
            payload = response.read(MAX_SNAPSHOT_BYTES + 1)
    except HTTPError:
        raise PublicDashboardUnavailable(
            "The dashboard snapshot is temporarily unavailable."
        ) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise PublicDashboardUnavailable(
            "The dashboard API could not be reached."
        ) from None
    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise PublicDashboardUnavailable("The dashboard snapshot is too large.")
    try:
        document = json.loads(payload)
        return DashboardSnapshot.model_validate(document)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        raise PublicDashboardUnavailable(
            "The dashboard snapshot failed validation."
        ) from None


def bucket_rows(
    buckets: tuple[DashboardCountBucket, ...],
    *,
    key_label: str,
) -> list[dict[str, str | int]]:
    return [{key_label: bucket.key, "Count": bucket.count} for bucket in buckets]


def snapshot_age_hours(
    snapshot: DashboardSnapshot,
    *,
    now: datetime | None = None,
) -> float:
    current = now or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must include timezone information")
    return max(
        0.0,
        (
            current.astimezone(UTC) - snapshot.generated_at.astimezone(UTC)
        ).total_seconds()
        / 3600,
    )
