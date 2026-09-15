#!/usr/bin/env bash
set -euo pipefail

: "${NODE_TEXTFILE_DIR:?set NODE_TEXTFILE_DIR}"
: "${CODESTRA_BUSINESS:?set an approved Codestra business slug}"
: "${CODESTRA_APPLICATION:?set application}"
: "${CODESTRA_SERVICE:?set service}"
: "${CODESTRA_ENVIRONMENT:?set environment}"
: "${CODESTRA_SERVER:?set stable server name}"
: "${CODESTRA_REGION:?set region}"
: "${CODESTRA_DEPLOYMENT:?set immutable deployment identifier}"
: "${CODESTRA_VERSION:?set immutable application version}"

STATUS_DIR="${CODESTRA_STATUS_DIR:-/run/codestra/status}"
OUTPUT="${NODE_TEXTFILE_DIR}/codestra_host.prom"
mkdir -p "${NODE_TEXTFILE_DIR}"
umask 027
TMP="$(mktemp "${NODE_TEXTFILE_DIR}/.codestra_host.prom.XXXXXX")"
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
  local file=$1
  [[ -f ${file} ]] || return 1
  local value
  IFS= read -r value < "${file}" || true
  printf '%s' "${value}"
}

emit_timestamp() {
  local metric=$1 class=$2 file=$3 label_name=${4:-class} value
  if value=$(read_scalar "${file}") && is_epoch "${value}"; then
    printf '%s{%s="%s"} %s\n' "${metric}" "${label_name}" "$(label_escape "${class}")" "${value}" >> "${TMP}"
    printf 'codestra_status_file_present{class="%s"} 1\n' "$(label_escape "${class}")" >> "${TMP}"
  else
    printf 'codestra_status_file_present{class="%s"} 0\n' "$(label_escape "${class}")" >> "${TMP}"
  fi
}

emit_certificate_timestamp() {
  local metric=$1 class=$2 file=$3 purpose=$4 value
  if value=$(read_scalar "${file}") && is_epoch "${value}"; then
    printf '%s{certificate="%s",purpose="%s"} %s\n' "${metric}" "$(label_escape "${class}")" "$(label_escape "${purpose}")" "${value}" >> "${TMP}"
    printf 'codestra_status_file_present{class="%s"} 1\n' "$(label_escape "${class}")" >> "${TMP}"
  else
    printf 'codestra_status_file_present{class="%s"} 0\n' "$(label_escape "${class}")" >> "${TMP}"
  fi
}

cat >> "${TMP}" <<EOF
# HELP codestra_deployment_info Immutable deployment identity for the monitored service.
# TYPE codestra_deployment_info gauge
codestra_deployment_info{codestra_business="$(label_escape "${CODESTRA_BUSINESS}")",application="$(label_escape "${CODESTRA_APPLICATION}")",service="$(label_escape "${CODESTRA_SERVICE}")",environment="$(label_escape "${CODESTRA_ENVIRONMENT}")",server="$(label_escape "${CODESTRA_SERVER}")",region="$(label_escape "${CODESTRA_REGION}")",deployment="$(label_escape "${CODESTRA_DEPLOYMENT}")",version="$(label_escape "${CODESTRA_VERSION}")"} 1
# HELP codestra_status_file_present Whether a controlled operational status file exists and is valid.
# TYPE codestra_status_file_present gauge
# HELP codestra_node_backup_last_success_timestamp_seconds Last successful backup timestamp by protected backup scope.
# TYPE codestra_node_backup_last_success_timestamp_seconds gauge
# HELP codestra_node_restore_validation_last_success_timestamp_seconds Last successful restore-validation timestamp.
# TYPE codestra_node_restore_validation_last_success_timestamp_seconds gauge
# HELP codestra_node_certificate_not_after_timestamp_seconds Certificate expiry timestamp by bounded certificate class.
# TYPE codestra_node_certificate_not_after_timestamp_seconds gauge
# HELP codestra_node_configuration_drift Whether reviewed configuration differs from the deployed authority.
# TYPE codestra_node_configuration_drift gauge
EOF

emit_timestamp codestra_node_backup_last_success_timestamp_seconds database "${STATUS_DIR}/backup-database.last_success" backup_scope
emit_timestamp codestra_node_backup_last_success_timestamp_seconds object-storage "${STATUS_DIR}/backup-object-storage.last_success" backup_scope
emit_timestamp codestra_node_backup_last_success_timestamp_seconds configuration "${STATUS_DIR}/backup-configuration.last_success" backup_scope
emit_timestamp codestra_node_restore_validation_last_success_timestamp_seconds restore-validation "${STATUS_DIR}/restore-validation.last_success" restore_scope
emit_certificate_timestamp codestra_node_certificate_not_after_timestamp_seconds edge-tls "${STATUS_DIR}/certificate-edge.expiry" tls-serving
emit_certificate_timestamp codestra_node_certificate_not_after_timestamp_seconds internal-pki "${STATUS_DIR}/certificate-internal-pki.expiry" client-auth

if drift=$(read_scalar "${STATUS_DIR}/configuration-drift.state") && [[ ${drift} =~ ^[01]$ ]]; then
  printf 'codestra_node_configuration_drift{authority="reviewed-config",resource="host-configuration"} %s\n' "${drift}" >> "${TMP}"
  printf 'codestra_status_file_present{class="configuration-drift"} 1\n' >> "${TMP}"
else
  printf 'codestra_status_file_present{class="configuration-drift"} 0\n' >> "${TMP}"
fi

chmod 0644 "${TMP}"
mv -f "${TMP}" "${OUTPUT}"
trap - EXIT
