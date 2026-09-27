# Codestra Node Exporter Textfile Evidence Contract

The textfile collector exposes operational evidence that Node Exporter cannot discover safely by itself. Node Exporter only reads metrics; it never executes backup, restore, certificate, deployment, patching or drift scripts.

## Approved evidence domains

- backup success, attempt time and repository reachability;
- isolated restore-validation success, time and duration;
- internal certificate expiry;
- immutable deployment version, deployment ID and source revision;
- bounded configuration drift state;
- pending security-update count;
- reboot-required state;
- disaster-recovery archive time and integrity.

## Producer rules

1. A producer runs under its own least-privilege identity.
2. It writes a temporary file in the same filesystem as the final `.prom` file.
3. It validates metric names, label names, label counts, values, file size and series count against `metric-contract.v1.json`.
4. It sets restrictive ownership and mode.
5. It atomically renames the temporary file to a bounded final name.
6. It never uses symlinks, sample timestamps or append-in-place writes.
7. It removes stale output when the producer is retired.
8. It emits its own last-attempt and success evidence rather than reporting a false healthy value after failure.

Illustrative atomic pattern:

```bash
set -euo pipefail
umask 027
out=/var/lib/node_exporter/textfile_collector/codestra-backup.prom
tmp="$(mktemp "${out}.tmp.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
produce_validated_metrics >"$tmp"
chmod 0640 "$tmp"
mv -f "$tmp" "$out"
trap - EXIT
```

`produce_validated_metrics` is an external approved producer. It is not supplied or executed by Node Exporter.

## Cardinality rules

Labels identify a bounded scope or current release; they must never contain customer, account, user, email, phone, request, correlation, trace, message, order, path, filename, URL, query, token, secret, container or process identifiers.

`deployment`, `version` and `git_sha` are allowed only on the current `codestra_node_deployment_info` series. Producers must replace the old file atomically so obsolete releases do not remain active.

## Timestamp semantics

Time is represented as a gauge value containing Unix seconds. Prometheus sample timestamps are forbidden. Prometheus calculates age using `time() - <metric>` so stale evidence remains visible.

## Failure behavior

A producer failure must not leave a new healthy value. The previous file may remain temporarily so Prometheus can show its age, but the producer must expose a failed last-attempt metric or remove the file according to its runbook. Silent freshness reset is prohibited.
