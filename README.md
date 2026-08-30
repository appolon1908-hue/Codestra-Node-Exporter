# Codestra Node Exporter

This repository is the service authority for host-level CPU, memory, filesystem, network, load, kernel, process-count, pressure, clock, and controlled textfile metrics. `appolon1908-hue/Codestra-Prometheus` owns scraping, canonical labels, recording rules, alerts, SLO evaluation, and retention.

## Runtime boundary

Node Exporter runs once on each Linux host with host networking and the host PID namespace because it measures the host rather than its container. The host root is mounted read-only at `/host`; the container is otherwise read-only, drops all Linux capabilities, enables `no-new-privileges`, and exposes no Docker host-port mapping.

The runtime image is assembled from a repository-only value and an exact SHA-256 digest. The listener must be an approved IPv4 address inside `10.40.0.0/24` and remain on port 9100:

| Server class | Reference private listener |
|---|---|
| Core | `10.40.0.1:9100` |
| Telephony | `10.40.0.2:9100` |
| Provider | `10.40.0.4:9100` |

The mandatory preflight rejects tags, `latest`, embedded digests, malformed hashes, wildcard addresses, loopback, link-local, public addresses, and private addresses outside the approved Codestra subnet.

Port 9100 must be denied on public interfaces and allowed only from the approved Prometheus source on the private network. The existing `node.codestra.media` public DNS assignment is an ownership identifier only. It must be preserved as canonical authority metadata, but it does **not** authorize publishing, proxying, or exposing the native exporter endpoint through DNS, Caddy, Kong, or the public firewall.

## Corporate metric contract

The approved source covers CPU, memory, swap, filesystem, network, load, pressure, clock, process-count, and kernel health. The controlled textfile collector may publish host-owned operational evidence such as backup age, restore-validation age, certificate-expiry horizon, deployment provenance, configuration drift, and security-maintenance status.

Prometheus adds `codestra_business`, `application`, `service`, `environment`, `server`, `region`, and `deployment` labels. Exporter or textfile metrics must never contain customer, tenant-user, email, phone, token, credential, request, trace, message, order, raw path, business payload, or other high-cardinality identifiers.

See `codestra/enterprise-profile.v1.json` and `codestra/docs/CORPORATE-FEATURES.md` for the source-controlled corporate feature model.

## Validation

Repository validation renders `deploy/compose.yaml`, proves repository-plus-digest image construction, private binding, host namespace/mount requirements, read-only runtime hardening, dropped capabilities, and the absence of public port publication.

A future approved deployment procedure must run the preflight against the exact environment file before any Compose command:

```bash
cp .env.example .env
# Set NODE_EXPORTER_IMAGE_DIGEST and the server's approved private IP.
python3 scripts/validate_runtime_environment.py --env-file .env
docker compose --env-file .env -f deploy/compose.yaml config
```

A direct `docker compose up` that bypasses `scripts/validate_runtime_environment.py` is not an approved Codestra deployment path. Any later apply remains a separate, explicitly approved deployment task.

Those commands are documentation only during the repository-first phase. Before Prometheus target activation, later deployment evidence must prove private-only reachability, `node_exporter_build_info`, expected host identity, filesystem visibility, required labels, scrape success, and rollback.

## Promotion and safety

Promotion is `feature/* -> development -> test -> staging -> production -> main`. Merging changes source authority only and does not deploy. `DEPLOYMENT_ENABLED=NO` remains binding until the corporate suite release manifest is accepted.
