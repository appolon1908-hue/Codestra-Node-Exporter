#!/usr/bin/env bash
set -Eeuo pipefail

: "${NODE_TEXTFILE_DIR:?set NODE_TEXTFILE_DIR}"
: "${CODESTRA_APPLICATION:?set application}"
: "${CODESTRA_SERVICE:?set service}"
: "${CODESTRA_DEPLOYMENT:?set immutable deployment identifier}"
: "${CODESTRA_VERSION:?set immutable application version}"
: "${CODESTRA_GIT_SHA:?set exact 40-character Git SHA}"

STATUS_DIR="${CODESTRA_STATUS_DIR:-/run/codestra/status}"
NODE_EXPORTER_GID="${NODE_EXPORTER_GID:-10001}"
OUTPUT="${NODE_TEXTFILE_DIR}/codestra_node.prom"

[[ ${NODE_EXPORTER_GID} =~ ^[0-9]+$ ]]
[[ ${CODESTRA_GIT_SHA} =~ ^[0-9a-f]{40}$ ]]
[[ ! -L ${NODE_TEXTFILE_DIR} ]]
mkdir -p "${NODE_TEXTFILE_DIR}"
[[ ! -L ${OUTPUT} ]]

umask 027
TMP="$(mktemp "${NODE_TEXTFILE_DIR}/.codestra_node.prom.XXXXXX")"
trap 'rm -f "${TMP}"' EXIT

label_escape() {
  local value=${1-}
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  value=${value//$'\n'/\\n}
  printf '%s' "${value}"
}

is_epoch() {
  [[ ${1-} =~ ^[0-9]{10}$ ]]
}

read_scalar() {
  local file=$1 value
  [[ -f ${file} && ! -L ${file} ]] || return 1
  IFS= read -r value < "${file}" || true
  printf '%s' "${value}"
}

emit_timestamp() {
  local metric=$1 label_name=$2 label_value=$3 file=$4 value
  if value=$(read_scalar "${file}") && is_epoch "${value}"; then
    printf '%s{%s="%s"} %s\n' \
      "${metric}" "${label_name}" "$(label_escape "${label_value}")" "${value}" >> "${TMP}"
  fi
}

cat >> "${TMP}" <<EOF
# HELP codestra_node_textfile_contract_info Active Codestra textfile metric contract version.
# TYPE codestra_node_textfile_contract_info gauge
codestra_node_textfile_contract_info{version="1.0"} 1
# HELP codestra_node_deployment_info Current immutable deployment and source revision information.
# TYPE codestra_node_deployment_info gauge
codestra_node_deployment_info{application="$(label_escape "${CODESTRA_APPLICATION}")",service="$(label_escape "${CODESTRA_SERVICE}")",version="$(label_escape "${CODESTRA_VERSION}")",deployment="$(label_escape "${CODESTRA_DEPLOYMENT}")",git_sha="${CODESTRA_GIT_SHA}"} 1
# HELP codestra_node_backup_last_success_timestamp_seconds Unix timestamp of the last successful backup.
# TYPE codestra_node_backup_last_success_timestamp_seconds gauge
# HELP codestra_node_restore_validation_last_success_timestamp_seconds Unix timestamp of the last successful isolated restore validation.
# TYPE codestra_node_restore_validation_last_success_timestamp_seconds gauge
# HELP codestra_node_certificate_not_after_timestamp_seconds Unix timestamp when an approved host certificate expires.
# TYPE codestra_node_certificate_not_after_timestamp_seconds gauge
# HELP codestra_node_configuration_drift Whether a bounded managed resource differs from its approved authority.
# TYPE codestra_node_configuration_drift gauge
EOF

emit_timestamp codestra_node_backup_last_success_timestamp_seconds backup_scope database \
  "${STATUS_DIR}/backup-database.last_success"
emit_timestamp codestra_node_backup_last_success_timestamp_seconds backup_scope object-storage \
  "${STATUS_DIR}/backup-object-storage.last_success"
emit_timestamp codestra_node_backup_last_success_timestamp_seconds backup_scope configuration \
  "${STATUS_DIR}/backup-configuration.last_success"
emit_timestamp codestra_node_restore_validation_last_success_timestamp_seconds restore_scope isolated \
  "${STATUS_DIR}/restore-validation.last_success"

certificate_value=""
if certificate_value=$(read_scalar "${STATUS_DIR}/certificate-edge.expiry") && is_epoch "${certificate_value}"; then
  printf 'codestra_node_certificate_not_after_timestamp_seconds{certificate="edge-tls",purpose="public-ingress"} %s\n' \
    "${certificate_value}" >> "${TMP}"
fi
if certificate_value=$(read_scalar "${STATUS_DIR}/certificate-internal-pki.expiry") && is_epoch "${certificate_value}"; then
  printf 'codestra_node_certificate_not_after_timestamp_seconds{certificate="internal-pki",purpose="service-mtls"} %s\n' \
    "${certificate_value}" >> "${TMP}"
fi

if drift=$(read_scalar "${STATUS_DIR}/configuration-drift.state") && [[ ${drift} =~ ^[01]$ ]]; then
  printf 'codestra_node_configuration_drift{authority="git",resource="managed-configuration"} %s\n' \
    "${drift}" >> "${TMP}"
fi

if (( $(wc -c < "${TMP}") > 262144 )); then
  echo 'Rendered Node Exporter textfile exceeds the contract limit.' >&2
  exit 1
fi

if (( EUID == 0 )); then
  chown "0:${NODE_EXPORTER_GID}" "${TMP}"
else
  [[ "$(stat -c '%g' "${TMP}")" == "${NODE_EXPORTER_GID}" ]] || {
    echo 'Non-root renderer must run with NODE_EXPORTER_GID equal to its effective group.' >&2
    exit 1
  }
fi
chmod 0640 "${TMP}"
mv -f "${TMP}" "${OUTPUT}"
trap - EXIT
