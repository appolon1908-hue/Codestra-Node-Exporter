#!/usr/bin/env python3
"""Fail-closed validation for the Codestra Node Exporter overlay."""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Any

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CODESTRA = ROOT / "codestra"
RUNTIME = CODESTRA / "runtime.v1.json"
WEB_CONFIG = CODESTRA / "web-config.yml"
COMPOSE = CODESTRA / "deploy" / "compose.candidate.yaml"
DOCKERFILE = CODESTRA / "deploy" / "Dockerfile"
HEALTHCHECK = CODESTRA / "deploy" / "healthcheck.go"
ENV_EXAMPLE = CODESTRA / "deploy" / "runtime.env.example"
TEXTFILE_CONTRACT = CODESTRA / "textfile" / "metric-contract.v1.json"
TEXTFILE_EXAMPLE = CODESTRA / "textfile" / "example.prom"
TEXTFILE_README = CODESTRA / "textfile" / "README.md"
OPERATING_MODEL = CODESTRA / "docs" / "OPERATING-MODEL.md"

EXPECTED_COLLECTORS = {
    "boottime",
    "cpu",
    "cpufreq",
    "diskstats",
    "dmi",
    "entropy",
    "filefd",
    "filesystem",
    "hwmon",
    "loadavg",
    "mdadm",
    "meminfo",
    "netclass",
    "netdev",
    "netstat",
    "os",
    "pressure",
    "processes",
    "sockstat",
    "stat",
    "textfile",
    "thermal_zone",
    "time",
    "timex",
    "uname",
    "vmstat",
}
EXPECTED_METRICS = {
    "codestra_node_backup_last_success_timestamp_seconds",
    "codestra_node_backup_last_attempt_timestamp_seconds",
    "codestra_node_backup_last_attempt_success",
    "codestra_node_backup_repository_reachable",
    "codestra_node_restore_validation_last_success_timestamp_seconds",
    "codestra_node_restore_validation_last_attempt_success",
    "codestra_node_restore_validation_duration_seconds",
    "codestra_node_certificate_not_after_timestamp_seconds",
    "codestra_node_deployment_info",
    "codestra_node_configuration_drift",
    "codestra_node_security_updates_pending",
    "codestra_node_reboot_required",
    "codestra_node_dr_archive_last_success_timestamp_seconds",
    "codestra_node_dr_archive_integrity_ok",
    "codestra_node_textfile_contract_info",
}
FORBIDDEN_LABELS = {
    "tenant_id",
    "customer_id",
    "account_id",
    "user_id",
    "email",
    "phone",
    "request_id",
    "correlation_id",
    "trace_id",
    "span_id",
    "message_id",
    "order_id",
    "path",
    "filename",
    "url",
    "query",
    "checksum",
    "token",
    "secret",
    "container_id",
    "process_pid",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def require_file(path: pathlib.Path) -> str:
    if not path.is_file():
        fail(f"missing required file: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def load_json(path: pathlib.Path) -> Any:
    try:
        return json.loads(require_file(path))
    except Exception as exc:
        fail(f"invalid JSON {path.relative_to(ROOT)}: {exc}")


def load_yaml(path: pathlib.Path) -> Any:
    try:
        return yaml.safe_load(require_file(path))
    except Exception as exc:
        fail(f"invalid YAML {path.relative_to(ROOT)}: {exc}")


def validate_runtime() -> None:
    runtime = load_json(RUNTIME)
    if runtime.get("schemaVersion") != "1.0":
        fail("Node Exporter runtime schemaVersion must be 1.0")
    if runtime.get("component") != "node-exporter":
        fail("Node Exporter runtime component mismatch")
    if runtime.get("canonicalHostname") != "node.codestra.media":
        fail("canonical Node Exporter hostname mismatch")
    if runtime.get("exposure") != "internal_private":
        fail("Node Exporter exposure must remain internal_private")
    if runtime.get("status") != "CONFIG_PREPARED_NOT_DEPLOYED":
        fail("Node Exporter runtime must remain CONFIG_PREPARED_NOT_DEPLOYED")
    if runtime.get("businessScope") != ["platform"]:
        fail("Node Exporter target scope must remain platform host infrastructure")
    if set(runtime.get("nativeCollectors", [])) != EXPECTED_COLLECTORS:
        fail("runtime collector allowlist does not match the approved collector set")

    boundaries = runtime.get("collectorBoundaries", {})
    for field in (
        "systemdDbusCollector",
        "hostNetwork",
        "hostPidNamespace",
        "privilegedMode",
        "dockerSocket",
        "containerMetrics",
        "applicationMetrics",
        "textfileExecutesScripts",
    ):
        if boundaries.get(field) is not False:
            fail(f"Node Exporter boundary must remain false: {field}")
    if boundaries.get("disableDefaults") is not True:
        fail("Node Exporter default collectors must remain disabled")

    transport = runtime.get("transport", {})
    if transport.get("tls") is not True or transport.get("minimumVersion") != "TLS13":
        fail("Node Exporter must require TLS 1.3")
    if transport.get("prometheusClientCertificateRequired") is not True:
        fail("Prometheus client certificate must be required")
    if transport.get("basicAuthentication") is not False:
        fail("basic authentication must remain disabled")
    if transport.get("anonymousPlainHttp") is not False:
        fail("anonymous plaintext HTTP must remain disabled")
    if transport.get("nativeHostPortPublished") is not False:
        fail("Node Exporter native port may not be published to the host")

    activation = runtime.get("activation", {})
    if not activation or any(value is not False for value in activation.values()):
        fail("all Node Exporter activation gates must remain false before evidence exists")


def validate_web_config() -> None:
    config = load_yaml(WEB_CONFIG)
    tls = config.get("tls_server_config", {})
    expected = {
        "cert_file": "/run/secrets/node_exporter_server_cert",
        "key_file": "/run/secrets/node_exporter_server_key",
        "client_auth_type": "RequireAndVerifyClientCert",
        "client_ca_file": "/run/secrets/prometheus_client_ca",
        "min_version": "TLS13",
    }
    if tls != expected:
        fail("Node Exporter TLS/mTLS configuration does not match the corporate contract")
    http = config.get("http_server_config", {})
    if http.get("http2") is not True:
        fail("Node Exporter must enable HTTP/2 over TLS")
    headers = http.get("headers", {})
    for header in (
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Content-Security-Policy",
        "Cache-Control",
    ):
        if not headers.get(header):
            fail(f"Node Exporter web config is missing security header {header}")


def validate_compose() -> None:
    compose = load_yaml(COMPOSE)
    services = compose.get("services", {})
    if set(services) != {"node-exporter"}:
        fail("Compose candidate must define exactly the Node Exporter service")
    service = services["node-exporter"]
    command = [str(item) for item in service.get("command", [])]
    if "--collector.disable-defaults" not in command:
        fail("Node Exporter must disable default collectors")
    collectors = {
        item.removeprefix("--collector.")
        for item in command
        if item.startswith("--collector.")
        and "=" not in item
        and item != "--collector.disable-defaults"
    }
    if collectors != EXPECTED_COLLECTORS:
        fail(f"Compose collector allowlist mismatch: {sorted(collectors)}")

    required_flags = (
        "--path.procfs=/host/proc",
        "--path.sysfs=/host/sys",
        "--path.rootfs=/host/root",
        "--path.udev.data=/host/root/run/udev/data",
        "--collector.textfile.directory=/var/lib/node_exporter/textfile_collector",
        "--web.listen-address=0.0.0.0:9100",
        "--web.telemetry-path=/metrics",
        "--web.config.file=/etc/node_exporter/web.yml",
        "--log.level=info",
        "--log.format=json",
    )
    for flag in required_flags:
        if flag not in command:
            fail(f"Node Exporter command is missing {flag}")
    for prefix in (
        "--collector.diskstats.device-exclude=",
        "--collector.filesystem.mount-points-exclude=",
        "--collector.filesystem.fs-types-exclude=",
        "--collector.netdev.device-exclude=",
    ):
        if not any(item.startswith(prefix) for item in command):
            fail(f"Node Exporter command is missing bounded exclusion {prefix}")

    if service.get("user") != "10001:10001":
        fail("Node Exporter must run as UID/GID 10001")
    if service.get("read_only") is not True:
        fail("Node Exporter root filesystem must be read-only")
    if service.get("privileged") is True or service.get("network_mode") == "host":
        fail("Node Exporter may not use privileged or host-network mode")
    if service.get("pid") == "host":
        fail("Node Exporter may not use the host PID namespace")
    if service.get("ports"):
        fail("Node Exporter may not publish a host port")
    if set(map(str, service.get("expose", []))) != {"9100"}:
        fail("Node Exporter must expose only private port 9100")
    if set(service.get("networks", [])) != {"codestra-observability"}:
        fail("Node Exporter must attach only to the observability network")
    if "ALL" not in service.get("cap_drop", []):
        fail("Node Exporter must drop all Linux capabilities")
    if "no-new-privileges:true" not in service.get("security_opt", []):
        fail("Node Exporter must set no-new-privileges")
    if set(service.get("secrets", [])) != {
        "node_exporter_server_cert",
        "node_exporter_server_key",
        "prometheus_client_ca",
    }:
        fail("Node Exporter mTLS secret-file contract is incomplete")
    if service.get("healthcheck", {}).get("test") != ["CMD", "/node-exporter-healthcheck"]:
        fail("Node Exporter must use the native listener probe")

    volumes = service.get("volumes", [])
    bind_targets = {
        item.get("target")
        for item in volumes
        if isinstance(item, dict) and item.get("type") == "bind"
    }
    if bind_targets != {
        "/host/proc",
        "/host/sys",
        "/host/root",
        "/var/lib/node_exporter/textfile_collector",
    }:
        fail("Node Exporter host bind target allowlist mismatch")
    for item in volumes:
        if isinstance(item, dict) and item.get("type") == "bind" and item.get("read_only") is not True:
            fail(f"Node Exporter bind must be read-only: {item.get('target')}")

    image = str(service.get("image", ""))
    if "${CODESTRA_NODE_EXPORTER_IMAGE:" not in image or "sha256" not in image:
        fail("Node Exporter final image must require an immutable digest")
    build_args = service.get("build", {}).get("args", {})
    if set(build_args) != {"GO_BUILDER_IMAGE", "NODE_EXPORTER_BASE_IMAGE"}:
        fail("Node Exporter build must pin builder and upstream images")
    limits = service.get("deploy", {}).get("resources", {}).get("limits", {})
    for field in ("cpus", "memory", "pids"):
        if field not in limits:
            fail(f"Node Exporter runtime is missing resource limit {field}")

    serialized = COMPOSE.read_text(encoding="utf-8")
    for forbidden in (
        "/var/run/docker.sock",
        "/run/docker.sock",
        ":latest",
        "privileged: true",
        "network_mode: host",
        "pid: host",
        "ports:",
        "--collector.systemd",
    ):
        if forbidden in serialized:
            fail(f"Node Exporter runtime contains forbidden content: {forbidden}")


def parse_labels(raw: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    if not raw:
        return labels
    for match in re.finditer(r'(\w+)="((?:\\.|[^"\\])*)"(?:,|$)', raw):
        labels[match.group(1)] = match.group(2)
    return labels


def validate_textfile_contract() -> None:
    contract = load_json(TEXTFILE_CONTRACT)
    if contract.get("schemaVersion") != "1.0":
        fail("textfile contract schemaVersion must be 1.0")
    if contract.get("status") != "CONTRACT_PREPARED_NOT_ACTIVATED":
        fail("textfile contract must remain prepared, not activated")
    policy = contract.get("writePolicy", {})
    if policy.get("atomicRename") is not True:
        fail("textfile producers must use atomic rename")
    if policy.get("sampleTimestampsAllowed") is not False:
        fail("textfile sample timestamps must remain forbidden")
    if policy.get("symlinksAllowed") is not False:
        fail("textfile symlinks must remain forbidden")
    if policy.get("worldWritableFilesAllowed") is not False:
        fail("world-writable textfile metrics must remain forbidden")

    metrics = contract.get("metrics", [])
    by_name = {metric.get("name"): metric for metric in metrics}
    if set(by_name) != EXPECTED_METRICS or len(by_name) != len(metrics):
        fail("textfile metric catalogue mismatch or duplicate metric names")
    if not FORBIDDEN_LABELS.issubset(set(contract.get("forbiddenLabelNames", []))):
        fail("textfile contract does not forbid all unsafe labels")
    for name, metric in by_name.items():
        if metric.get("type") != "gauge":
            fail(f"textfile metric must be a gauge: {name}")
        labels = metric.get("labels", [])
        if len(labels) != len(set(labels)):
            fail(f"duplicate textfile labels for {name}")
        if set(labels) & FORBIDDEN_LABELS:
            fail(f"forbidden textfile labels for {name}")
        if not isinstance(metric.get("maximumSeries"), int) or metric["maximumSeries"] <= 0:
            fail(f"textfile metric requires a positive maximumSeries: {name}")

    example = require_file(TEXTFILE_EXAMPLE)
    if len(example.encode("utf-8")) > policy.get("maximumFileBytes", 0):
        fail("textfile example exceeds the maximum file size")
    sample_names: list[str] = []
    sample_re = re.compile(
        r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{(?P<labels>[^}]*)\})?\s+"
        r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|NaN|[+-]Inf)"
        r"(?:\s+(?P<timestamp>\d+))?$"
    )
    types: dict[str, str] = {}
    for line_number, raw_line in enumerate(example.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("# TYPE "):
            parts = line.split()
            if len(parts) != 4:
                fail(f"invalid TYPE declaration on example line {line_number}")
            types[parts[2]] = parts[3]
            continue
        if line.startswith("#"):
            continue
        match = sample_re.fullmatch(line)
        if not match:
            fail(f"invalid Prometheus sample on example line {line_number}")
        name = match.group("name")
        if name not in by_name:
            fail(f"unapproved metric in textfile example: {name}")
        if match.group("timestamp") is not None:
            fail(f"sample timestamp is forbidden for {name}")
        labels = parse_labels(match.group("labels") or "")
        if set(labels) != set(by_name[name].get("labels", [])):
            fail(f"example labels do not match contract for {name}")
        if set(labels) & FORBIDDEN_LABELS:
            fail(f"forbidden example labels for {name}")
        allowed_values = by_name[name].get("allowedValues")
        if allowed_values is not None and float(match.group("value")) not in {
            float(value) for value in allowed_values
        }:
            fail(f"example value is outside the contract for {name}")
        sample_names.append(name)

    if set(sample_names) != EXPECTED_METRICS:
        fail(f"textfile example is missing metrics: {sorted(EXPECTED_METRICS - set(sample_names))}")
    if len(sample_names) > policy.get("maximumSeriesPerFile", 0):
        fail("textfile example exceeds the series-per-file budget")
    for name in EXPECTED_METRICS:
        if types.get(name) != "gauge":
            fail(f"textfile example must declare gauge type for {name}")


def validate_packaging_docs_and_secrets() -> None:
    dockerfile = require_file(DOCKERFILE)
    for fragment in (
        "ARG GO_BUILDER_IMAGE",
        "ARG NODE_EXPORTER_BASE_IMAGE",
        "CGO_ENABLED=0",
        "-trimpath",
        "/node-exporter-healthcheck",
        "/etc/node_exporter/web.yml",
        "USER 10001:10001",
    ):
        if fragment not in dockerfile:
            fail(f"Node Exporter Dockerfile is missing {fragment}")
    if ":latest" in dockerfile:
        fail("Node Exporter Dockerfile may not use latest tags")

    healthcheck = require_file(HEALTHCHECK)
    if "127.0.0.1:9100" not in healthcheck:
        fail("Node Exporter healthcheck must use the local listener")
    if "os/exec" in healthcheck or "exec.Command" in healthcheck:
        fail("Node Exporter healthcheck may not invoke a shell or subprocess")

    env_text = require_file(ENV_EXAMPLE)
    for fragment in (
        "CODESTRA_NODE_EXPORTER_DEPLOYMENT_ID=",
        "GO_BUILDER_IMAGE=",
        "NODE_EXPORTER_BASE_IMAGE=",
        "CODESTRA_NODE_EXPORTER_IMAGE=",
        "NODE_EXPORTER_TEXTFILE_PATH=",
        "NODE_EXPORTER_SERVER_CERT_SECRET_NAME=",
        "NODE_EXPORTER_SERVER_KEY_SECRET_NAME=",
        "PROMETHEUS_CLIENT_CA_SECRET_NAME=",
    ):
        if fragment not in env_text:
            fail(f"Node Exporter runtime example omits {fragment}")

    require_file(TEXTFILE_README)
    require_file(OPERATING_MODEL)

    dash = chr(45) * 5
    signatures = (
        dash + "BEGIN " + "PRIVATE" + chr(32) + "KEY" + dash,
        dash + "BEGIN " + "OPENSSH" + chr(32) + "PRIVATE" + chr(32) + "KEY" + dash,
        "A" + "K" + "I" + "A",
    )
    for path in CODESTRA.rglob("*"):
        if not path.is_file() or path.suffix == ".pyc" or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for signature in signatures:
            if signature in text:
                fail(f"secret-shaped material found in {path.relative_to(ROOT)}")


def main() -> None:
    validate_runtime()
    validate_web_config()
    validate_compose()
    validate_textfile_contract()
    validate_packaging_docs_and_secrets()
    print("Codestra Node Exporter corporate configuration validation PASS")


if __name__ == "__main__":
    main()
