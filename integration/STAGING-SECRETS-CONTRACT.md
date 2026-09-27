# Staging secrets contract (names only — no values)

This file enumerates every secret/credential **name** required to run
controlled-intake staging evidence collection against the locked Middleware
release, and to operate the hardened Node Exporter runtime with mTLS. It
contains **no secret values, tokens, keys, or certificates**. All actual
values must be provisioned outside git, per
`staging_credentials.storage: OUTSIDE_GIT` in
[staging-activation-contract-v1.json](./staging-activation-contract-v1.json).

Do not add real values to this file, to `.env`, or to any committed file.
Populate these names in your secret manager / OpenBao / CI environment only.

## Runtime mTLS secrets (Node Exporter, this repo)

External Docker/Compose secrets already declared in
`codestra/deploy/compose.candidate.yaml` and `codestra/runtime-v1/compose.yaml`:

| Secret name (override env var) | Default external name | Purpose |
|---|---|---|
| `NODE_EXPORTER_SERVER_CERT_SECRET_NAME` | `node-exporter-server-cert` | TLS server certificate for `--web.config.file` |
| `NODE_EXPORTER_SERVER_KEY_SECRET_NAME` | `node-exporter-server-key` | TLS server private key |
| `PROMETHEUS_CLIENT_CA_SECRET_NAME` | `prometheus-client-ca` | CA used to verify Prometheus's client certificate (`RequireAndVerifyClientCert`) |

## Staging credential contract (Middleware read-back)

Per `staging_credentials` in `staging-activation-contract-v1.json`:

| Property | Value |
|---|---|
| Storage | `OUTSIDE_GIT` |
| Static/long-lived tokens | not allowed |
| Token TTL | 60–900 seconds |
| Issuer boundary | Keycloak service identity, runtime material managed by OpenBao |

Required secret/credential **names** (values issued at runtime by Keycloak +
OpenBao, never committed):

| Name | Consumer | Scope | Notes |
|---|---|---|---|
| `MIDDLEWARE_STAGING_CLIENT_ID` | staging harness (Codestra-Prometheus) | n/a | Keycloak service-account client ID, `monitoring-readonly` |
| `MIDDLEWARE_STAGING_CLIENT_SECRET` | staging harness | n/a | Keycloak service-account secret; OpenBao-issued, short TTL |
| `MIDDLEWARE_METRICS_READ_SCOPE` | staging harness | `metrics.read` | scope requested for `GET /metrics` |
| `MIDDLEWARE_HEALTH_READ_SCOPE` | staging harness | `health.read` | scope requested for `GET /v1/runtime/safety` |
| `PROMETHEUS_CLIENT_CERT_SECRET_NAME` | staging harness | n/a | mTLS client cert used when scraping Middleware over `private_mtls` |
| `PROMETHEUS_CLIENT_KEY_SECRET_NAME` | staging harness | n/a | mTLS client key, paired with the cert above |

## Where these are NOT provisioned

This repository (`Codestra-Node-Exporter`) does not run the staging harness
and must never hold real values for the names above. Per
`integration/staging-activation-contract-v1.json`, the collector and evidence
owner is `appolon1908-hue/Codestra-Prometheus` (branch `development`).
Real secret material belongs in that repository's runtime/CI secret store
(OpenBao-backed), not here.

## Verification checklist before any staging run

- [ ] `MIDDLEWARE_STAGING_CLIENT_ID`/`_SECRET` resolve to a live, short-TTL
      (≤900s) Keycloak service identity — never a static token.
- [ ] The Middleware image pulled matches the locked digest
      `sha256:695fa3ce3f50ba4d0ae0784976b946a0a683ca731155e4bd3bd9e90a4670b820`
      exactly.
- [ ] `git grep` / secret-scanning shows zero matches for any of the names
      above holding an actual value in this repository.
- [ ] Evidence checksum collected during the run is distinct from every
      release/image/SBOM/vulnerability-report checksum already locked in the
      contract (enforced by `controlled-intake-staging-activation-gate.yml`).
