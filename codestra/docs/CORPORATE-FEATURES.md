# Codestra Node Exporter Corporate Features

## Mission

Node Exporter is the standard host-health metrics source across Codestra-managed servers. It provides consistent operating-system evidence to Prometheus and Grafana without exposing business data.

## Baseline host coverage

Track CPU, memory, swap, disks, filesystem capacity, disk I/O, network, load, uptime, file descriptors, pressure and clock/time health.

## Codestra textfile expansion

Use reviewed textfile collectors for operational facts that do not belong in application code, including:

- age of the last successful backup;
- age of the last restore validation;
- TLS certificate expiry windows;
- deployed source/image/version metadata;
- source-to-runtime drift state;
- age of security maintenance/update evidence;
- filesystem/backup status.

These metrics must remain numeric/state oriented and must never contain secrets, customer identifiers or raw file contents.

## Corporate use

Grafana can group host health by server role and environment and associate each host with the business/services running there. Host metrics remain infrastructure telemetry; they do not become application or customer state.

## Security

The Node Exporter listener stays private and is scraped by Prometheus over an approved network path. `node.codestra.media` is an internal/private identity even when DNS exists.

## Release rule

Codestra configuration and textfile contracts stay outside imported upstream source. Merge alone does not expose a port or deploy the exporter.
