# Codestra Node Exporter Authority

Principal repository: `appolon1908-hue/Codestra-Node-Exporter`
Canonical service host: `node.codestra.media`
Canonical DNS target: `37.27.128.39`
TTL: `600`

DNS has been externally verified. This repository must not introduce alternate authoritative hostnames.

## Ownership
Own Node Exporter deployment/configuration, collector policy, host-metrics validation and upgrade runbooks. Do not own Prometheus scrape policy, Grafana dashboards, Caddy, or host administration outside exporter requirements.

## Exposure
Private/internal only. DNS may exist, but exporter ports must be restricted to Prometheus/private monitoring networks.

## Integration
Upstream: host kernel/filesystem/network/process metrics. Downstream: Prometheus scrapes.

## Branch policy
Persistent: `main`, `development`, `test`, `staging`, `production`.
Temporary: `feature/*`, `fix/*`, `upgrade/*`, `security/*`, `docs/*`, `hotfix/*`, optional `release/*`, `rollback/*`.
Promotion: work -> development -> test -> staging -> production -> main.
