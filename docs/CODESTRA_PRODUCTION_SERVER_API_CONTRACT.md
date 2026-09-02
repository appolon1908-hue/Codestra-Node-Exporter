# Codestra Node Exporter Production Server and Native API Contract

## Authority

- Repository: `appolon1908-hue/Codestra-Node-Exporter`
- Role: host metrics and controlled operational-evidence authority
- Canonical hostname: `node.codestra.media`
- Central production host: `37.27.128.39`
- Core host `65.109.65.169`: separate approved agent installation after central certification
- Status: `SOURCE_CONTRACT_PREPARED_NOT_DEPLOYED`

Node Exporter owns host metrics, collector policy, approved textfile evidence, image/release evidence, and rollback. It does not own application metrics, container metrics, business mutation, or secret distribution.

## Native API surface

| Method | Path | Purpose | Boundary |
|---|---|---|---|
| `GET` | `/metrics` | host and approved textfile metrics | private mTLS Prometheus scrape only |

Unexpected `404`, `5xx`, plaintext/public port `9100`, unauthenticated scrape, or sensitive filesystem/process exposure blocks production.

## Collector and privacy policy

- Use an explicit collector allowlist and reviewed filesystem/process exclusions.
- Textfile metrics are limited to backup freshness, restore-validation age, certificate expiry, deployment/version identity, and configuration drift.
- Textfile writers use approved ownership, restricted permissions, temporary files, atomic rename, and bounded cardinality.
- Secret-bearing paths, customer data, command lines containing credentials, raw environment values, and high-cardinality identifiers are excluded.
- Native metrics remain private; no public hostname route is required.

## Production gates

```text
PROTECTED_PRODUCTION_SHA=PASS
COLLECTOR_ALLOWLIST=PASS
FILESYSTEM_EXCLUSIONS=PASS
PROCESS_EXPOSURE_REVIEW=PASS
TEXTFILE_OWNERSHIP=PASS
TEXTFILE_ATOMIC_WRITES=PASS
MTLS_SCRAPE=PASS
PUBLIC_9100=NO
IMMUTABLE_IMAGE_DIGEST=PASS
IMAGE_SIGNATURE=PASS
SBOM=PASS
PROVENANCE=PASS
SECRET_SCAN=PASS
ROLLBACK_MANIFEST=PASS
```

## Runtime certification

```text
GET_/metrics=PASS
UNAUTHENTICATED_SCRAPE_DENIED=PASS
PLAINTEXT_SCRAPE_DENIED=PASS
MTLS_CLIENT_VERIFY=PASS
COLLECTOR_ALLOWLIST=PASS
SECRET_BEARING_METRICS=0
HIGH_CARDINALITY_SENSITIVE_LABELS=0
BACKUP_FRESHNESS_METRIC=PASS
RESTORE_AGE_METRIC=PASS
CERTIFICATE_EXPIRY_METRIC=PASS
DEPLOYMENT_IDENTITY_METRIC=PASS
DRIFT_METRIC=PASS
UNEXPECTED_404=0
UNEXPECTED_5XX=0
SOURCE_RUNTIME_DRIFT=0
```

## Repository-first remediation

Preserve the existing healthy exporter if certification fails. Fix defects here with regression tests, commit/push, exact-head CI and review, protected merge, signed immutable rebuild, BOM update, and only then retry. Never patch a host-only collector or textfile script without updating this repository.

## Safety

This document does not deploy Node Exporter or enable scraping. SSH changes, business writes, communications delivery, provider actions, lending, payments, and trading remain outside scope and disabled.