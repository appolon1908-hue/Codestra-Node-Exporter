# Codestra Node Exporter

This repository is the service authority for host-level CPU, memory, filesystem, network, load, kernel, process-count, pressure, clock, and controlled textfile metrics. `appolon1908-hue/Codestra-Prometheus` owns scraping, canonical labels, recording rules, alerts, SLO evaluation, and retention.

## Runtime boundary

Node Exporter runs once on each Linux host using read-only `/proc`, `/sys`, host-root, udev, and approved textfile mounts. The hardened authority does not use host networking or the host PID namespace. It is otherwise read-only, drops all Linux capabilities, enables `no-new-privileges`, publishes no host port, and requires Prometheus mTLS through `codestra/web-config.yml`.

The runtime image is assembled from a repository-only value and an exact SHA-256 digest. The container listener remains on port 9100 inside the private `codestra-observability` network. Tags, `latest`, embedded digests, and malformed hashes are rejected by repository validation.

Port 9100 must be denied on public interfaces and allowed only from the approved Prometheus source on the private network. The existing `node.codestra.media` public DNS assignment is an ownership identifier only. It must be preserved as canonical authority metadata, but it does **not** authorize publishing, proxying, or exposing the native exporter endpoint through DNS, Caddy, Kong, or the public firewall.

## Corporate metric contract

The approved source covers CPU, memory, swap, filesystem, network, load, pressure, clock, process-count, and kernel health. The controlled textfile collector may publish host-owned operational evidence such as backup age, restore-validation age, certificate-expiry horizon, deployment provenance, configuration drift, and security-maintenance status.

Prometheus adds `codestra_business`, `application`, `service`, `environment`, `server`, `region`, and `deployment` labels. Exporter or textfile metrics must never contain customer, tenant-user, email, phone, token, credential, request, trace, message, order, raw path, business payload, or other high-cardinality identifiers.

See `codestra/enterprise-profile.v1.json` and `codestra/docs/CORPORATE-FEATURES.md` for the source-controlled corporate feature model.

## Validation

Repository validation renders `codestra/deploy/compose.candidate.yaml`, proves repository-plus-digest image construction, mTLS enforcement, private networking, read-only host mounts, dropped capabilities, and the absence of public port publication.

A future approved deployment procedure must run the preflight against the exact environment file before any Compose command:

```bash
cp codestra/deploy/runtime.env.example .env
# Replace all placeholder image/build digests and deployment identity values.
python3 scripts/validate_codestra_node_exporter.py --env-file .env
docker compose --env-file .env -f codestra/deploy/compose.candidate.yaml config
```

A direct `docker compose up` that bypasses repository validation and the reviewed environment is not an approved Codestra deployment path. Any later apply remains a separate, explicitly approved deployment task.

Those commands are documentation only during the repository-first phase. Before Prometheus target activation, later deployment evidence must prove private-only reachability, `node_exporter_build_info`, expected host identity, filesystem visibility, required labels, scrape success, and rollback.

Automated upstream synchronization requires the repository Actions secret `CODESTRA_AUTOMATION_TOKEN`, backed by an approved GitHub App or fine-grained token with contents and pull-request permissions. The non-default token is required so generated review PRs trigger normal validation; absence of the secret fails the sync closed.

## Promotion and safety

Promotion is `feature/* -> development -> test -> staging -> production -> main`. Merging changes source authority only and does not deploy. `DEPLOYMENT_ENABLED=NO` remains binding until the corporate suite release manifest is accepted.
