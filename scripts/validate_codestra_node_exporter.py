#!/usr/bin/env python3
"""Fail-closed validation for the Codestra Node Exporter overlay."""

from __future__ import annotations

import argparse
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

# Linux publishes node_boot_time_seconds through the stat collector. The
# platform-specific boottime collector is not a valid Linux command-line flag.
EXPECTED_COLLECTORS = {
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


IMAGE_REPOSITORY_RE = re.compile(
    r"^(?:[a-z0-9.-]+(?::[0-9]+)?/)?"
    r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*$"
)
IMAGE_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_env_file(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw in enumerate(require_file(path).splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            fail(f"invalid environment assignment at {path}:{line_number}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in values:
            fail(f"empty or duplicate environment key at {path}:{line_number}")
        values[key] = value.strip()
    return values


def validate_deployment_environment(path: pathlib.Path) -> None:
    values = parse_env_file(path)
    repository = values.get("CODESTRA_NODE_EXPORTER_IMAGE_REPOSITORY", "")
    digest = values.get("CODESTRA_NODE_EXPORTER_IMAGE_DIGEST", "")
    if not IMAGE_REPOSITORY_RE.fullmatch(repository) or "@" in repository or ":latest" in repository:
        fail("CODESTRA_NODE_EXPORTER_IMAGE_REPOSITORY must be a repository-only reference")
    if not IMAGE_DIGEST_RE.fullmatch(digest) or set(digest) == {"0"}:
        fail(
            "CODESTRA_NODE_EXPORTER_IMAGE_DIGEST must be a real, non-placeholder "
            "64-character lowercase hexadecimal digest"
        )


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
    expected_identity = {
        "schemaVersion": "1.0",
        "component": "node-exporter",
        "canonicalHostname": "node.codestra.media",
        "exposure": "internal_private",
        "status": "CONFIG_PREPARED_NOT_DEPLOYED",
        "businessScope": ["platform"],
    }
    for key, expected in expected_identity.items():
        if runtime.get(key) != expected:
            fail(f"runtime identity mismatch for {key}")

    if set(runtime.get("nativeCollectors", [])) != EXPECTED_COLLECTORS:
        fail("runtime collector allowlist does not match the locked Linux collector set")
    notes = runtime.get("collectorNotes", {})
    if notes.get("bootTimeMetricSource") != "stat":
        fail("boot time metric must be sourced from the Linux stat collector")
    if notes.get("linuxBoottimeCollectorFlagAllowed") is not False:
        fail("unsupported Linux boottime collector flag must remain prohibited")

    boundaries = runtime.get("collectorBoundaries", {})
    false_boundaries = (
        "systemdDbusCollector",
        "hostNetwork",
        "hostPidNamespace",
        "privilegedMode",
        "dockerSocket",
        "containerMetrics",
        "applicationMetrics",
        "textfileExecutesScripts",
    )
    if boundaries.get("disableDefaults") is not True:
        fail("default collectors must remain disabled")
    for field in false_boundaries:
        if boundaries.get(field) is not False:
            fail(f"Node Exporter boundary must remain false: {field}")

    transport = runtime.get("transport", {})
    if transport != {
        "tls": True,
        "minimumVersion": "TLS13",
        "prometheusClientCertificateRequired": True,
        "basicAuthentication": False,
        "anonymousPlainHttp": False,
        "nativeHostPortPublished": False,
        "privatePort": 9100,
    }:
        fail("Node Exporter transport contract mismatch")

    activation = runtime.get("activation", {})
    if not activation or any(value is not False for value in activation.values()):
        fail("all activation gates must remain false in repository-first mode")


def validate_web_config() -> None:
    config = load_yaml(WEB_CONFIG)
    if config.get("tls_server_config") != {
        "cert_file": "/run/secrets/node_exporter_server_cert",
        "key_file": "/run/secrets/node_exporter_server_key",
        "client_auth_type": "RequireAndVerifyClientCert",
        "client_ca_file": "/run/secrets/prometheus_client_ca",
        "min_version": "TLS13",
    }:
        fail("TLS/mTLS web configuration mismatch")
    http = config.get("http_server_config", {})
    if http.get("http2") is not True:
        fail("HTTP/2 over TLS must be enabled")
    headers = http.get("headers", {})
    # exporter-toolkit rejects Cache-Control in http_server_config.headers.
    # Keep all supported browser-hardening headers mandatory and fail closed if
    # the unsupported override is reintroduced. The endpoint remains private,
    # mTLS-only, and carries scrape data rather than browser application data.
    for header in (
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Content-Security-Policy",
    ):
        if not headers.get(header):
            fail(f"missing security header {header}")
    if "Cache-Control" in headers:
        fail("exporter-toolkit does not support a configured Cache-Control header")


def validate_compose() -> None:
    compose = load_yaml(COMPOSE)
    services = compose.get("services", {})
    if set(services) != {"node-exporter"}:
        fail("Compose candidate must contain exactly node-exporter")
    service = services["node-exporter"]
    command = [str(item) for item in service.get("command", [])]
    if "--collector.disable-defaults" not in command:
        fail("default collectors must be disabled")
    if "--collector.boottime" in command:
        fail("unsupported Linux collector flag --collector.boottime is prohibited")
    collectors = {
        item.removeprefix("--collector.")
        for item in command
        if item.startswith("--collector.")
        and "=" not in item
        and item != "--collector.disable-defaults"
    }
    if collectors != EXPECTED_COLLECTORS:
        fail(f"collector allowlist mismatch: {sorted(collectors)}")

    for flag in (
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
    ):
        if flag not in command:
            fail(f"missing required command flag {flag}")
    for prefix in (
        "--collector.diskstats.device-exclude=",
        "--collector.filesystem.mount-points-exclude=",
        "--collector.filesystem.fs-types-exclude=",
        "--collector.netdev.device-exclude=",
    ):
        if not any(item.startswith(prefix) for item in command):
            fail(f"missing bounded exclusion {prefix}")

    if service.get("user") != "10001:10001":
        fail("runtime UID/GID must be 10001:10001")
    if service.get("read_only") is not True:
        fail("root filesystem must be read-only")
    if service.get("privileged") is True:
        fail("privileged mode is prohibited")
    if service.get("network_mode") == "host" or service.get("pid") == "host":
        fail("host network and host PID namespace are prohibited")
    if service.get("ports"):
        fail("host port publication is prohibited")
    if set(map(str, service.get("expose", []))) != {"9100"}:
        fail("only private port 9100 may be exposed")
    if set(service.get("networks", [])) != {"codestra-observability"}:
        fail("only the observability network is allowed")
    if service.get("cap_drop") != ["ALL"]:
        fail("all Linux capabilities must be dropped")
    if "no-new-privileges:true" not in service.get("security_opt", []):
        fail("no-new-privileges is required")
    if set(service.get("secrets", [])) != {
        "node_exporter_server_cert",
        "node_exporter_server_key",
        "prometheus_client_ca",
    }:
        fail("mTLS secret-file contract is incomplete")
    if service.get("healthcheck", {}).get("test") != ["CMD", "/node-exporter-healthcheck"]:
        fail("native health probe is required")

    bind_targets = {
        item.get("target")
        for item in service.get("volumes", [])
        if isinstance(item, dict) and item.get("type") == "bind"
    }
    if bind_targets != {
        "/host/proc",
        "/host/sys",
        "/host/root",
        "/var/lib/node_exporter/textfile_collector",
    }:
        fail("host bind target allowlist mismatch")
    for item in service.get("volumes", []):
        if isinstance(item, dict) and item.get("type") == "bind" and item.get("read_only") is not True:
            fail(f"host bind must be read-only: {item.get('target')}")

    image = str(service.get("image", ""))
    expected_image = (
        "${CODESTRA_NODE_EXPORTER_IMAGE_REPOSITORY:?set a repository-only "
        "Codestra Node Exporter image name}@sha256:"
        "${CODESTRA_NODE_EXPORTER_IMAGE_DIGEST:?set exactly 64 lowercase "
        "hexadecimal digest characters}"
    )
    if image != expected_image:
        fail("final image must be structurally assembled as repository@sha256:digest")
    if set(service.get("build", {}).get("args", {})) != {
        "GO_BUILDER_IMAGE",
        "NODE_EXPORTER_BASE_IMAGE",
    }:
        fail("builder and upstream base image must both be pinned")
    limits = service.get("deploy", {}).get("resources", {}).get("limits", {})
    if not {"cpus", "memory", "pids"}.issubset(limits):
        fail("resource limits are incomplete")

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
        "--collector.boottime",
    ):
        if forbidden in serialized:
            fail(f"forbidden runtime content: {forbidden}")


def parse_labels(raw: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    if raw:
        for match in re.finditer(r'(\w+)="((?:\\.|[^"\\])*)"(?:,|$)', raw):
            labels[match.group(1)] = match.group(2)
    return labels


def validate_textfile_contract() -> None:
    contract = load_json(TEXTFILE_CONTRACT)
    if contract.get("schemaVersion") != "1.0":
        fail("textfile contract schema version mismatch")
    if contract.get("status") != "CONTRACT_PREPARED_NOT_ACTIVATED":
        fail("textfile contract must remain inactive")
    policy = contract.get("writePolicy", {})
    if policy.get("atomicRename") is not True:
        fail("atomic rename is required")
    for field in ("sampleTimestampsAllowed", "symlinksAllowed", "worldWritableFilesAllowed"):
        if policy.get(field) is not False:
            fail(f"unsafe textfile write policy: {field}")

    metrics = contract.get("metrics", [])
    by_name = {item.get("name"): item for item in metrics}
    if set(by_name) != EXPECTED_METRICS or len(by_name) != len(metrics):
        fail("textfile metric catalogue mismatch")
    if not FORBIDDEN_LABELS.issubset(set(contract.get("forbiddenLabelNames", []))):
        fail("unsafe labels are not fully prohibited")
    for name, metric in by_name.items():
        if metric.get("type") != "gauge":
            fail(f"metric must be gauge: {name}")
        labels = metric.get("labels", [])
        if len(labels) != len(set(labels)) or set(labels) & FORBIDDEN_LABELS:
            fail(f"unsafe labels for {name}")
        if not isinstance(metric.get("maximumSeries"), int) or metric["maximumSeries"] <= 0:
            fail(f"invalid maximumSeries for {name}")

    example = require_file(TEXTFILE_EXAMPLE)
    if len(example.encode("utf-8")) > policy.get("maximumFileBytes", 0):
        fail("textfile example exceeds maximum size")
    samples: list[str] = []
    pattern = re.compile(
        r"^(?P<name>[a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{(?P<labels>[^}]*)\})?\s+"
        r"(?P<value>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|NaN|[+-]Inf)"
        r"(?:\s+(?P<timestamp>\d+))?$"
    )
    for line_number, raw in enumerate(example.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = pattern.fullmatch(line)
        if not match:
            fail(f"invalid Prometheus sample on line {line_number}")
        name = match.group("name")
        if name not in by_name or match.group("timestamp") is not None:
            fail(f"unapproved or timestamped sample {name}")
        labels = parse_labels(match.group("labels") or "")
        if set(labels) != set(by_name[name].get("labels", [])):
            fail(f"example label mismatch for {name}")
        samples.append(name)
    if set(samples) != EXPECTED_METRICS:
        fail("textfile example does not cover the full catalogue")
    if len(samples) > policy.get("maximumSeriesPerFile", 0):
        fail("textfile example exceeds series budget")


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
            fail(f"Dockerfile is missing {fragment}")
    if ":latest" in dockerfile:
        fail("latest image tags are prohibited")

    healthcheck = require_file(HEALTHCHECK)
    if "127.0.0.1:9100" not in healthcheck:
        fail("healthcheck must use the local native listener")
    if "os/exec" in healthcheck or "exec.Command" in healthcheck:
        fail("healthcheck may not spawn subprocesses")

    env_text = require_file(ENV_EXAMPLE)
    for fragment in (
        "CODESTRA_NODE_EXPORTER_DEPLOYMENT_ID=",
        "GO_BUILDER_IMAGE=",
        "NODE_EXPORTER_BASE_IMAGE=",
        "CODESTRA_NODE_EXPORTER_IMAGE_REPOSITORY=",
        "CODESTRA_NODE_EXPORTER_IMAGE_DIGEST=",
        "NODE_EXPORTER_TEXTFILE_PATH=",
        "NODE_EXPORTER_SERVER_CERT_SECRET_NAME=",
        "NODE_EXPORTER_SERVER_KEY_SECRET_NAME=",
        "PROMETHEUS_CLIENT_CA_SECRET_NAME=",
    ):
        if fragment not in env_text:
            fail(f"runtime example omits {fragment}")

    require_file(TEXTFILE_README)
    require_file(OPERATING_MODEL)
    signatures = (
        "-----BEGIN PRIVATE KEY-----",
        "-----BEGIN OPENSSH PRIVATE KEY-----",
        "AKIA",
    )
    for path in CODESTRA.rglob("*"):
        if not path.is_file() or path.suffix == ".pyc" or "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for signature in signatures:
            if signature in text:
                fail(f"secret-shaped material found in {path.relative_to(ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=pathlib.Path)
    args = parser.parse_args()
    validate_runtime()
    validate_web_config()
    validate_compose()
    validate_textfile_contract()
    validate_packaging_docs_and_secrets()
    if args.env_file is not None:
        validate_deployment_environment(args.env_file)
    print("Codestra Node Exporter corporate configuration validation PASS")


if __name__ == "__main__":
    main()
