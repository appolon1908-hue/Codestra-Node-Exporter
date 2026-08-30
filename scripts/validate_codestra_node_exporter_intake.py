#!/usr/bin/env python3
"""Fail-closed validation for the Node Exporter unified-intake host contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "codestra" / "intake-monitoring.v1.json"

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


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid Node Exporter intake contract: {exc}")

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
    if set(contract.get("events", [])) != EXPECTED_EVENTS:
        fail("Node Exporter intake event catalogue mismatch")
    if set(contract.get("safeDimensions", [])) != EXPECTED_SAFE_DIMENSIONS:
        fail("Node Exporter intake safe dimensions mismatch")

    forbidden = set(contract.get("forbiddenLabelsOrPayloads", []))
    if not REQUIRED_FORBIDDEN.issubset(forbidden):
        fail("Node Exporter intake contract omits protected fields")
    if forbidden & EXPECTED_SAFE_DIMENSIONS:
        fail("Node Exporter intake field cannot be both safe and forbidden")

    privacy = contract.get("privacyRules", {})
    if privacy != {
        "rawFormAnswersInTelemetry": False,
        "rawSurveyAnswersInTelemetry": False,
        "contactDataInMetricLabels": False,
    }:
        fail("Node Exporter intake privacy contract mismatch")

    activation = contract.get("activation", {})
    if not activation or any(value is not False for value in activation.values()):
        fail("all Node Exporter intake activation gates must remain false")
    if set(activation) != {
        "runtimeApplied",
        "productionTargetsEnabled",
        "liveBusinessWritesEnabledByThisContract",
    }:
        fail("Node Exporter intake activation catalogue mismatch")

    features = contract.get("features", {})
    if set(features.get("hostSignals", [])) != EXPECTED_HOST_SIGNALS:
        fail("Node Exporter intake host-signal catalogue mismatch")
    if set(features.get("textfileEvidence", [])) != EXPECTED_TEXTFILE_EVIDENCE:
        fail("Node Exporter intake textfile-evidence catalogue mismatch")
    if features.get("applicationIntakeMetricsOwnedHere") is not False:
        fail("application intake metrics must remain outside Node Exporter authority")

    serialized = CONTRACT.read_text(encoding="utf-8").lower()
    for secret_shape in (
        "-----begin private key-----",
        "bearer ",
        "password=",
        "api_key=",
        "client_secret=",
    ):
        if secret_shape in serialized:
            fail("secret-shaped content found in Node Exporter intake contract")

    print("Codestra Node Exporter intake contract validation PASS")


if __name__ == "__main__":
    main()
