# Codestra Node Exporter

This repository is the service authority for host-level CPU, memory, filesystem, network, load, kernel, process-count, and textfile metrics. `appolon1908-hue/Codestra-Prometheus` owns scraping, labels, recording rules, alerts, and retention.

## Runtime boundary

Node Exporter runs once on each Linux host with host networking and the host PID namespace because it is measuring the host, not its container. The host root is mounted read-only at `/host`; the container is otherwise read-only and drops all Linux capabilities.

Each deployment must set an immutable `NODE_EXPORTER_IMAGE` containing `@sha256:` and bind the listener to the host's private Hetzner vSwitch address:

| Server | Private listener |
|---|---|
| `codestra-core-01` | `10.40.0.1:9100` |
| `codestra-telephony-01` | `10.40.0.2:9100` |
| `codestra-provider-01` | `10.40.0.4:9100` |

Port 9100 must be denied on public interfaces and allowed only from the approved Prometheus source on the private network. Do not assign public DNS, route it through Caddy/Kong, or add a Docker `ports:` mapping.

## Labels and tenant safety

Prometheus adds `environment`, `server`, `application=infrastructure`, `service=node-exporter`, and `tenant_scope=aggregate`. Textfile metrics must describe host-owned jobs only and must not contain tenant, customer, user, email, phone, token, request, trace, message, order, or raw-path labels.

## Validation

```bash
cp .env.example .env
# Set the reviewed digest and this server's private IP.
docker compose -f deploy/compose.yaml config
docker compose -f deploy/compose.yaml up -d
curl --fail http://PRIVATE_IP:9100/-/healthy
```

Deployment is a separate approved operation. Before Prometheus target activation, prove private-only reachability, `node_exporter_build_info`, expected host identity, filesystem visibility, a successful scrape with required labels, and rollback.

Promotion is `feature/* -> development -> test -> staging -> production -> main`. Merging does not deploy.
