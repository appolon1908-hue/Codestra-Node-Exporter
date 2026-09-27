#!/usr/bin/env python3
"""Validate immutable image and private-listener inputs for Node Exporter."""

from __future__ import annotations

import argparse
import ipaddress
import os
import pathlib
import re
import sys
from collections.abc import Mapping

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy" / "compose.yaml"
APPROVED_LISTENER_NETWORKS = (
    ipaddress.ip_network("10.40.0.0/24"),
)
REPOSITORY_RE = re.compile(
    r"^(?:[a-z0-9.-]+(?::[0-9]+)?/)?"
    r"[a-z0-9]+(?:[._-][a-z0-9]+)*(?:/[a-z0-9]+(?:[._-][a-z0-9]+)*)*$"
)
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_IMAGE_TEMPLATE = (
    "image: ${NODE_EXPORTER_IMAGE_REPOSITORY:?NODE_EXPORTER_IMAGE_REPOSITORY is required}"
    "@sha256:${NODE_EXPORTER_IMAGE_DIGEST:?NODE_EXPORTER_IMAGE_DIGEST must be a "
    "64-character lowercase hexadecimal digest}"
)


def fail(message: str) -> None:
    print(f"NODE_EXPORTER_RUNTIME_POLICY_ERROR={message}", file=sys.stderr)
    raise SystemExit(1)


def parse_env_file(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        fail(f"cannot read environment file {path}: {exc}")
    for line_number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            fail(f"invalid assignment at {path}:{line_number}")
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in values:
            fail(f"empty or duplicate key at {path}:{line_number}")
        values[key] = value.strip()
    return values


def validate_compose_template() -> None:
    try:
        text = COMPOSE.read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"cannot read {COMPOSE}: {exc}")
    if EXPECTED_IMAGE_TEMPLATE not in text:
        fail("Compose image must be structurally assembled as repository@sha256:digest")
    if "${NODE_EXPORTER_IMAGE:" in text or ":latest" in text:
        fail("Compose contains a legacy or mutable image input")
    if "--web.listen-address=${NODE_EXPORTER_LISTEN_IP:" not in text:
        fail("Compose must require an explicit validated listener address")


def validate_values(values: Mapping[str, str]) -> tuple[str, str]:
    repository = values.get("NODE_EXPORTER_IMAGE_REPOSITORY", "").strip()
    digest = values.get("NODE_EXPORTER_IMAGE_DIGEST", "").strip()
    listen_ip = values.get("NODE_EXPORTER_LISTEN_IP", "").strip()
    port = values.get("NODE_EXPORTER_PORT", "9100").strip()

    if not REPOSITORY_RE.fullmatch(repository):
        fail("NODE_EXPORTER_IMAGE_REPOSITORY must be a repository-only reference")
    if "@" in repository or repository.endswith(":latest"):
        fail("NODE_EXPORTER_IMAGE_REPOSITORY may not contain a tag or digest")
    if not DIGEST_RE.fullmatch(digest):
        fail("NODE_EXPORTER_IMAGE_DIGEST must be exactly 64 lowercase hexadecimal characters")

    try:
        address = ipaddress.ip_address(listen_ip)
    except ValueError as exc:
        fail(f"NODE_EXPORTER_LISTEN_IP must be an IP address: {exc}")
    if address.version != 4:
        fail("NODE_EXPORTER_LISTEN_IP must be an approved private IPv4 address")
    if address.is_unspecified or address.is_loopback or address.is_link_local:
        fail("NODE_EXPORTER_LISTEN_IP may not be wildcard, loopback, or link-local")
    if not any(address in network for network in APPROVED_LISTENER_NETWORKS):
        fail(
            "NODE_EXPORTER_LISTEN_IP is outside the approved Codestra private network "
            + ", ".join(str(network) for network in APPROVED_LISTENER_NETWORKS)
        )
    if port != "9100":
        fail("NODE_EXPORTER_PORT must remain 9100")

    return f"{repository}@sha256:{digest}", f"{address}:{port}"


def prove_policy() -> None:
    valid = {
        "NODE_EXPORTER_IMAGE_REPOSITORY": "quay.io/prometheus/node-exporter",
        "NODE_EXPORTER_IMAGE_DIGEST": "0" * 64,
        "NODE_EXPORTER_LISTEN_IP": "10.40.0.1",
        "NODE_EXPORTER_PORT": "9100",
    }
    validate_values(valid)
    unsafe = (
        {**valid, "NODE_EXPORTER_IMAGE_REPOSITORY": "quay.io/prometheus/node-exporter:latest"},
        {**valid, "NODE_EXPORTER_IMAGE_DIGEST": "latest"},
        {**valid, "NODE_EXPORTER_IMAGE_DIGEST": "A" * 64},
        {**valid, "NODE_EXPORTER_LISTEN_IP": "0.0.0.0"},
        {**valid, "NODE_EXPORTER_LISTEN_IP": "::"},
        {**valid, "NODE_EXPORTER_LISTEN_IP": "127.0.0.1"},
        {**valid, "NODE_EXPORTER_LISTEN_IP": "8.8.8.8"},
        {**valid, "NODE_EXPORTER_LISTEN_IP": "10.41.0.1"},
        {**valid, "NODE_EXPORTER_PORT": "80"},
    )
    for sample in unsafe:
        try:
            validate_values(sample)
        except SystemExit:
            continue
        fail(f"runtime policy negative test unexpectedly passed: {sample}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=pathlib.Path)
    args = parser.parse_args()
    validate_compose_template()
    prove_policy()
    values: Mapping[str, str] = parse_env_file(args.env_file) if args.env_file else os.environ
    image, listener = validate_values(values)
    print(f"CODESTRA_NODE_EXPORTER_IMAGE={image}")
    print(f"CODESTRA_NODE_EXPORTER_LISTENER={listener}")
    print("CODESTRA_NODE_EXPORTER_RUNTIME_POLICY_PASS=1")


if __name__ == "__main__":
    main()
