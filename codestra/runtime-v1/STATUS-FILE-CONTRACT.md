# Codestra Node Exporter status-file contract

The textfile collector publishes **bounded operational facts**, not customer or request data. A root-owned timer or deployment job writes one scalar value per file under `CODESTRA_STATUS_DIR` (default `/run/codestra/status`). The renderer writes atomically to the protected Node Exporter textfile directory.

| File | Value | Corporate purpose |
|---|---:|---|
| `backup-database.last_success` | Unix seconds | Database backup freshness |
| `backup-object-storage.last_success` | Unix seconds | Object-store backup freshness |
| `backup-configuration.last_success` | Unix seconds | Git/configuration backup freshness |
| `restore-validation.last_success` | Unix seconds | Recovery proof freshness |
| `certificate-edge.expiry` | Unix seconds | Public-edge certificate expiry |
| `certificate-internal-pki.expiry` | Unix seconds | Internal workload certificate expiry |
| `configuration-drift.state` | `0` or `1` | Reviewed source versus deployed state |

The producer must write a temporary file, validate it, then rename it into place. Never put host credentials, customer IDs, tenant IDs, emails, phone numbers, paths containing secrets, or raw command output in these files or in metric labels.

Required deployment labels are the low-cardinality Codestra dimensions: `codestra_business`, `application`, `service`, `environment`, `server`, `region`, `deployment`, and immutable `version`.
