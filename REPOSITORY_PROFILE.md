# Repository Profile — `Codestra-Node-Exporter`

## Identity

- **Repository:** `appolon1908-hue/Codestra-Node-Exporter`
- **Category:** Observability exporter — host metrics
- **Visibility:** `public`
- **Default branch:** `main`
- **Canonical hostname:** `node.codestra.media`
- **Exposure:** Internal/private only; no public native metrics endpoint
- **Authority:** Primary host CPU, memory, storage, network, pressure, clock, hardware, and governed textfile-metric authority

## Purpose

Exports safe aggregate host-health and operational-evidence metrics to Prometheus without exposing container details, customer data, or business authority.

## Owns

- Approved Node Exporter collector allowlist and exclusions
- Private mTLS metrics listener and immutable runtime source
- Governed textfile metrics for backup, restore, certificates, deployment provenance, drift, maintenance, and DR evidence

## Does not own

- Container metrics, logs, traces, or application business metrics
- Arbitrary scripts inside Node Exporter
- Customer, tenant, request, message, financial, or secret labels

## Key integrations

- Prometheus
- Grafana host and capacity dashboards
- Infrastructure backup, restore, deployment, and certificate evidence producers
- OpenBao for runtime secret delivery where adopted

## Current priorities

1. Clear every exact-head corporate configuration gate
2. Preserve bounded collectors, filesystem/network exclusions, and mTLS
3. Validate textfile producers, label/cardinality rules, and stale-evidence alerts
4. Prove immutable packaging, upgrade, rollback, and private scrape behavior

## Governance and safety

- Promotion model: `feature/docs/fix/security/upgrade -> development -> test -> staging -> production -> main`.
- Native port `9100` must remain private; `node.codestra.media` must not expose metrics publicly.
- Never commit private keys, certificates with sensitive material, tokens, customer data, or generated host evidence containing secrets.
- Textfile metrics must be atomic, bounded, and free of PII/secrets.
- Merge does not mount host filesystems, start Node Exporter, issue certificates, activate scraping, or expose ports.

## Account-wide catalog

See `appolon1908-hue/documentaions/REPOSITORY_CATALOG.md`.
