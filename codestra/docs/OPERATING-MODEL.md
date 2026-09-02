# Codestra Node Exporter Operating Model

## Corporate role

Node Exporter is the authoritative host-metrics endpoint for Codestra servers. It presents CPU, memory, pressure, disk, filesystem, network, file-descriptor, process, clock, hardware and operating-system health to Prometheus and exposes approved operational evidence through the textfile collector.

Node Exporter does not own container metrics, application metrics, synthetic probes, logs, traces, SLO evaluation, alert routing, secrets, business workflows or deployment execution.

## Private scrape model

- Native endpoint: container port `9100` on the private observability network.
- No host port is published.
- TLS 1.3 is required.
- Prometheus must present a certificate signed by the configured client CA.
- Basic authentication and anonymous plaintext HTTP are not configured.
- The server certificate, private key and Prometheus client CA are external runtime secrets.

Prometheus target configuration adds the corporate target labels:

- `codestra_business=platform`
- `application=observability`
- `service=node-exporter`
- `environment`
- `server`
- `region`
- `deployment`

## Collector allowlist

Default collectors are disabled. The runtime enables only the reviewed allowlist recorded in `codestra/runtime.v1.json` and the Compose candidate. Pseudo filesystems, container overlay filesystems, loop/virtual block devices and ephemeral container network interfaces are excluded from normal host views.

The allowlist deliberately excludes the systemd DBus collector. Critical service state is monitored by service-native metrics, Blackbox probes, process indicators, or bounded textfile evidence rather than giving Node Exporter a host control socket.

## Host visibility and security boundary

Node Exporter needs read-only views of host `/proc`, `/sys` and the root mount for host filesystem statistics. These mounts are broad and must be treated as trusted host-agent access.

Controls are:

- UID/GID `10001:10001`;
- non-privileged container;
- no host network;
- no host PID namespace;
- no Docker socket;
- read-only root filesystem;
- all Linux capabilities dropped;
- `no-new-privileges` enabled;
- host mounts read-only;
- private observability network only;
- immutable image and resource limits;
- no shell-based health check.

A production packet must document why each host mount is required and prove that the non-root identity cannot read protected host secrets beyond the minimum kernel/filesystem metadata required by Node Exporter.

## Textfile evidence

The textfile directory is mounted read-only into Node Exporter. External producers create bounded, validated `.prom` files using atomic rename. Node Exporter never runs those producers.

The contract covers:

- backup freshness and last-attempt result;
- backup repository reachability;
- isolated restore-validation freshness, result and duration;
- internal certificate expiry;
- current immutable deployment version and source revision;
- configuration drift state;
- pending security updates;
- reboot-required state;
- disaster-recovery archive freshness and integrity.

Public HTTPS/TLS endpoint expiry remains Blackbox Exporter authority. The Node Exporter certificate metric is for host-local/internal certificates that are not publicly probed.

## Alert and dashboard use

Prometheus recording and alert rules should derive:

- CPU saturation and sustained load;
- memory pressure, swap activity and OOM risk;
- disk latency, throughput and saturation;
- filesystem capacity, inode exhaustion and read-only state;
- network errors, drops and throughput;
- pressure-stall information;
- time synchronization and clock drift;
- file-descriptor exhaustion;
- process/fork pressure;
- hardware temperature, RAID and hardware signals where supported;
- backup, restore, certificate, deployment, drift, patch and DR evidence age.

Grafana displays and correlates these signals. Alertmanager routes incidents. Node Exporter does not evaluate alerts or send notifications.

## Initial engineering objectives

Subject to staging calibration:

- private scrape availability at least 99.9%;
- scrape p95 below 5 seconds;
- scrape payload and series count inside the Prometheus target budget;
- zero public native listeners;
- zero unauthenticated scrapes;
- zero host-network, host-PID, privileged or Docker-socket access;
- textfile parse errors equal to zero;
- all required operational evidence present and fresh;
- no unbounded labels or sample timestamps in textfile files;
- Node Exporter CPU below 10% of one core and memory below the approved limit during normal scrapes.

## Required staging evidence

1. Build and record immutable builder, upstream and final image digests.
2. Validate the exact collector flags against the locked Node Exporter source.
3. Start the candidate with representative `/proc`, `/sys`, root and textfile mounts.
4. Prove a Prometheus-style mTLS scrape succeeds.
5. Prove no-cert, wrong-CA and plaintext requests fail.
6. Measure scrape duration, payload size, series count and collector errors.
7. Validate every example and staging textfile file against the contract.
8. Prove atomic replacement and restart behavior.
9. Prove stale backup/restore/certificate/deployment evidence remains visible.
10. Review filesystem, block-device and network exclusions on each server class.
11. Verify Prometheus target labels and Grafana dashboard correlation.
12. Record rollback instructions and previous immutable digest.

## Release boundary

Promotion is:

```text
feature/* -> development -> test -> staging -> production -> main
```

`CONFIG_PREPARED_NOT_DEPLOYED` remains the source state. Merge or CI success does not mount host filesystems, issue certificates, create textfile producers, expose port 9100, start Node Exporter or activate production scraping.
