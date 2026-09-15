# Middleware-facing endpoints and API exposure

This document consolidates every endpoint that connects Node Exporter to
`appolon1908-hue/Middleware-` for controlled-intake staging work. It contains
**no secret values** — only paths, methods, scopes, and the names of external
secret objects that must be provisioned outside git. See
[STAGING-SECRETS-CONTRACT.md](./STAGING-SECRETS-CONTRACT.md) for the secret
name contract.

## Direction of the relationship

Node Exporter is a **passive metrics source**. It never calls out to
Middleware. The only two endpoints that matter are:

1. Node Exporter's own `/metrics` endpoint, which Middleware's monitoring
   plane reads (pull, read-only).
2. Middleware's own `/metrics` and safety endpoints, which the Codestra
   monitoring stack (Prometheus, via this repo's staging-activation
   contract) reads (pull, read-only) to certify the Middleware release
   before any Prometheus target transitions from `pending` to `active`.

No endpoint in this relationship is a write, mutation, or webhook delivery
path. `direct_webhook_calls` remains `false` per
[service-manifest.v1.json](../service-manifest.v1.json).

## Node Exporter native endpoint (exposed BY this repo)

| Method | Path | Access | Client | Scope | Public exposure |
|---|---|---|---|---|---|
| `GET` | `/metrics` | read_only | `monitoring-readonly` | `metrics.read` | `false` (private network only) |

Source: `codestra/api/service-contract.v1.json`, `nativeApi.operations`.
Transport: `private_network` (staged) / `private_mtls` (production hardened
runtime, see `codestra/deploy/compose.candidate.yaml` and
`codestra/runtime-v1/compose.yaml`). No authentication credential is embedded
in the exporter itself (`credentialSource: none`); network isolation and, in
the hardened runtime, mutual TLS are the access controls.

## Middleware endpoints (consumed FOR staging certification)

| Method | Path | Client | Scope | Public exposure | Purpose |
|---|---|---|---|---|---|
| `GET` | `/metrics` | `monitoring-readonly` | `metrics.read` | `false` | Prometheus scrape target once activated |
| `GET` | `/v1/runtime/safety` | `monitoring-readonly` | `health.read` | `false` | Pre-activation safety/health read-back |

Source: `integration/staging-activation-contract-v1.json`,
`private_endpoints`, and `integration/controlled-intake-monitoring-v1.json`,
`middleware_metrics_endpoint`.

Both endpoints are `GET`-only, read-only, and must reject unauthorized or
wrong-token requests (`must_verify` includes `unauthorized_request_denied`,
`wrong_token_denied`). Neither endpoint may be proxied, mutated, or have its
response body retained downstream (`responseBodyPolicy: discard`,
`controlPlaneProxyAllowed: false`).

## Locked Middleware release identity

Staging work against Middleware must target the exact signed, immutable
release already locked in `integration/staging-activation-contract-v1.json`:

- Repository: `appolon1908-hue/Middleware-`
- Source SHA: `f6748a58f8d2590520a4f28776770957061cdea1`
- Immutable image digest: `sha256:695fa3ce3f50ba4d0ae0784976b946a0a683ca731155e4bd3bd9e90a4670b820`
- Signature: sigstore-keyless, transparency log required
- Vulnerability policy: fail-high-or-critical-with-fix

Any staging run against a different Middleware SHA or image digest is out of
contract and must not be certified as evidence toward production activation.

## What remains explicitly unauthorized

Per `activation_policy` and `runtime_effects` in
`staging-activation-contract-v1.json`, none of the following may happen as a
side effect of this documentation or any staging dry run:

- `production_activation_authorized: false`
- `deployment_performed: false`
- `prometheus_target_activated` / `blackbox_target_activated: false`
- `tokens_provisioned: false`
- `external_delivery_enabled`, `odoo_write_enabled`, `n8n_delivery_enabled`,
  `sms_enabled`, `email_enabled`, `voice_or_pstn_enabled`: all `false`

Activating the Prometheus target requires a **separate PR** that cites the
locked image digest and a real staging evidence checksum
(`activation_policy.prometheus_activation_pr_required`). Blackbox activation
requires independent review on top of that. Production activation requires
explicit human approval recorded outside this repository.
