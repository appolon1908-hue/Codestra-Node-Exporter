#!/usr/bin/env python3
"""Fail-closed validation for the Node Exporter unified-intake host contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "codestra" / "intake-monitoring.v1.json"

EXPECTED_TOP_LEVEL = {
    "schemaVersion",
    "status",
    "domain",
    "canonicalFlow",
    "events",
    "safeDimensions",
    "forbiddenLabelsOrPayloads",
    "privacyRules",
    "activation",
    "component",
    "responsibility",
    "features",
}
EXPECTED_FLOW = [
    "website-or-widget",
    "@codestra/intake-form-or-intake-survey",
    "@codestra/intake-sdk",
    "same-origin-intake-bff",
    "caddy",
    "kong",
    "middleware-durable-intake",
    "odoo-or-analytics-or-approved-workflow",
]
EXPECTED_EVENTS = {
    "codestra.events.lead_submitted",
    "codestra.events.survey_response_submitted",
}
EXPECTED_SAFE_DIMENSIONS = {
    "codestra_business",
    "application",
    "service",
    "environment",
    "server",
    "region",
    "deployment",
}
REQUIRED_FORBIDDEN = {
    "tenant_id",
    "site_id",
    "campaign_id",
    "form_id",
    "survey_id",
    "question_id",
    "customer_id",
    "contact_id",
    "lead_id",
    "response_id",
    "account_id",
    "user_id",
    "email",
    "phone",
    "message",
    "transcript",
    "answers",
    "custom_fields",
    "consent_text",
    "request_id",
    "trace_id",
    "idempotency_key",
}
EXPECTED_HOST_SIGNALS = {
    "cpu",
    "memory",
    "filesystem",
    "network",
    "clock",
    "process-count",
}
EXPECTED_TEXTFILE_EVIDENCE = {
    "backup-age",
    "restore-validation-age",
    "certificate-expiry",
    "deployment-version",
    "configuration-drift",
}
EXPECTED_PRIVACY = {
    "rawFormAnswersInTelemetry": False,
    "rawSurveyAnswersInTelemetry": False,
    "contactDataInMetricLabels": False,
}
EXPECTED_ACTIVATION = {
    "runtimeApplied": False,
    "productionTargetsEnabled": False,
    "liveBusinessWritesEnabledByThisContract": False,
}
EXPECTED_FEATURE_KEYS = {
    "hostSignals",
    "textfileEvidence",
    "applicationIntakeMetricsOwnedHere",
}
CREDENTIAL_KEYS = {
    "authorization",
    "bearer_token",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "client_secret",
    "access_token",
    "refresh_token",
    "session_token",
    "private_key",
    "root_token",
    "cookie",
    "set_cookie",
}
PEM_PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
    flags=re.IGNORECASE,
)


def fail(message: str) -> None:
    raise SystemExit(message)


def require_catalogue(value: Any, expected: set[str], label: str) -> set[str]:
    if not isinstance(value, list):
        fail(f"{label} must be a JSON array")
    if any(not isinstance(item, str) or not item for item in value):
        fail(f"{label} must contain non-empty strings only")
    if len(value) != len(set(value)):
        fail(f"{label} contains duplicate entries")
    actual = set(value)
    if actual != expected:
        fail(f"{label} catalogue mismatch")
    return actual


def require_superset_catalogue(value: Any, required: set[str], label: str) -> set[str]:
    if not isinstance(value, list):
        fail(f"{label} must be a JSON array")
    if any(not isinstance(item, str) or not item for item in value):
        fail(f"{label} must contain non-empty strings only")
    if len(value) != len(set(value)):
        fail(f"{label} contains duplicate entries")
    actual = set(value)
    if not required.issubset(actual):
        fail(f"{label} omits required entries")
    return actual


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def scan_credential_values(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if normalize_key(str(key)) in CREDENTIAL_KEYS and child not in (
                None,
                "",
                False,
                [],
                {},
            ):
                fail(f"credential-shaped value found at {child_path}")
            scan_credential_values(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            scan_credential_values(child, f"{path}[{index}]")
    elif isinstance(value, str) and PEM_PRIVATE_KEY.search(value):
        fail(f"PEM private-key material found at {path}")


def main() -> None:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid Node Exporter intake contract: {exc}")
    if not isinstance(contract, dict):
        fail("Node Exporter intake contract must be a JSON object")
    if set(contract) != EXPECTED_TOP_LEVEL:
        fail("Node Exporter intake top-level contract shape mismatch")

    expected_identity = {
        "schemaVersion": "1.0",
        "status": "CONTRACT_PREPARED_NOT_DEPLOYED",
        "domain": "unified-intake",
        "component": "node-exporter",
        "responsibility": "host capacity and operational evidence for intake runtime hosts",
    }
    for field, expected in expected_identity.items():
        if contract.get(field) != expected:
            fail(f"Node Exporter intake identity mismatch for {field}")

    if contract.get("canonicalFlow") != EXPECTED_FLOW:
        fail("Node Exporter intake canonical flow mismatch")
    require_catalogue(contract.get("events"), EXPECTED_EVENTS, "events")
    safe = require_catalogue(
        contract.get("safeDimensions"),
        EXPECTED_SAFE_DIMENSIONS,
        "safeDimensions",
    )
    forbidden = require_superset_catalogue(
        contract.get("forbiddenLabelsOrPayloads"),
        REQUIRED_FORBIDDEN,
        "forbiddenLabelsOrPayloads",
    )
    if forbidden & safe:
        fail("Node Exporter intake field cannot be both safe and forbidden")

    if contract.get("privacyRules") != EXPECTED_PRIVACY:
        fail("Node Exporter intake privacy contract mismatch")
    if contract.get("activation") != EXPECTED_ACTIVATION:
        fail("Node Exporter intake activation contract mismatch")

    features = contract.get("features")
    if not isinstance(features, dict) or set(features) != EXPECTED_FEATURE_KEYS:
        fail("Node Exporter intake feature contract shape mismatch")
    require_catalogue(
        features.get("hostSignals"),
        EXPECTED_HOST_SIGNALS,
        "features.hostSignals",
    )
    require_catalogue(
        features.get("textfileEvidence"),
        EXPECTED_TEXTFILE_EVIDENCE,
        "features.textfileEvidence",
    )
    if features.get("applicationIntakeMetricsOwnedHere") is not False:
        fail("application intake metrics must remain outside Node Exporter authority")

    scan_credential_values(contract)
    if PEM_PRIVATE_KEY.search(CONTRACT.read_text(encoding="utf-8")):
        fail("PEM private-key material found in Node Exporter intake contract")

    print("Codestra Node Exporter intake contract validation PASS")


if __name__ == "__main__":
    main()
