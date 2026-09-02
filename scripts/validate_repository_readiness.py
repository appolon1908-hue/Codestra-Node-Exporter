#!/usr/bin/env python3
"""Validate repository-only Node Exporter image release readiness."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
IMAGE = re.compile(r"^[a-z0-9./_-]+@sha256:[0-9a-f]{64}$")
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
AUTHORITY_SHA = "9a6aebb849bbc068105c10d9d1dfd39ebf6f78bd"
EXPECTED_RELEASE_AUTHORITY = (
    "appolon1908-hue/Codestra-Telemetry/.github/workflows/"
    f"reusable-release-image.yml@{AUTHORITY_SHA}"
)
REQUIRED = (
    "README.md",
    "REPOSITORY_PROFILE.md",
    "SECURITY.md",
    ".github/CODEOWNERS",
    "docs/BACKUP_RESTORE_ROLLBACK.md",
    "docs/UPGRADE.md",
    "codestra/.dockerignore",
    "codestra/deploy/Dockerfile",
    "codestra/deploy/compose.candidate.yaml",
    "codestra/release/image-build.v1.json",
    "codestra/release/runtime-base.lock.json",
    ".github/workflows/release-image.yml",
    "requirements-validation.txt",
)


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load(relative: str) -> dict:
    try:
        value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        fail(f"cannot load {relative}: {exc}")
    if not isinstance(value, dict):
        fail(f"{relative} must contain an object")
    return value


def validate() -> None:
    missing = [relative for relative in REQUIRED if not (ROOT / relative).is_file()]
    if missing:
        fail(f"missing readiness files: {missing}")

    manifest = load("codestra/release/image-build.v1.json")
    if manifest.get("schemaVersion") != "1.0.0":
        fail("image build schema mismatch")
    if manifest.get("imageId") != "node-exporter":
        fail("image build component mismatch")
    if manifest.get("dockerfile") != "codestra/deploy/Dockerfile":
        fail("image build Dockerfile mismatch")
    if manifest.get("context") != "codestra":
        fail("image build context must remain bounded to codestra/")
    if manifest.get("productionActivation") is not False:
        fail("image build manifest may not activate production")

    lock = load("codestra/release/runtime-base.lock.json")
    if lock.get("artifactModel") != "repository-built-signed-image":
        fail("Node Exporter must use signed image release Model A")
    if lock.get("imageId") != "node-exporter":
        fail("runtime base component mismatch")
    if not IMAGE.fullmatch(str(lock.get("runtimeBaseImage", ""))):
        fail("runtime base image must use an exact digest")
    if not IMAGE.fullmatch(str(lock.get("builderImage", ""))):
        fail("builder image must use an exact digest")
    if not IMAGE.fullmatch(str(lock.get("buildFrontendImage", ""))):
        fail("Dockerfile frontend must use an exact digest")
    if not GIT_SHA.fullmatch(str(lock.get("upstreamTagCommit", ""))):
        fail("upstream tag commit is invalid")
    if lock.get("binaryRevisionReadback") != lock.get("upstreamTagCommit"):
        fail("binary revision must equal the locked upstream tag commit")
    if lock.get("vendoredSourceUsedByImageBuild") is not False:
        fail("runtime build may not misrepresent the vendored source snapshot")
    vendored = load("CODESTRA_UPSTREAM_LOCK.json")
    if lock.get("vendoredSourceSnapshotCommit") != vendored.get("upstream_commit"):
        fail("vendored source snapshot identity mismatch")
    if lock.get("productionActivation") is not False:
        fail("runtime base lock may not activate production")
    if manifest.get("buildArgs") != {
        "GO_BUILDER_IMAGE": lock["builderImage"],
        "NODE_EXPORTER_BASE_IMAGE": lock["runtimeBaseImage"],
    }:
        fail("build arguments do not equal the runtime base lock")

    dockerfile = (ROOT / "codestra/deploy/Dockerfile").read_text(encoding="utf-8")
    if dockerfile.splitlines()[0] != f"# syntax={lock['buildFrontendImage']}":
        fail("Dockerfile frontend does not equal the runtime base lock")
    if "latest" in dockerfile.lower():
        fail("Dockerfile contains a mutable latest reference")
    if set(re.findall(r"(?m)^ARG\s+([A-Z][A-Z0-9_]*_IMAGE)$", dockerfile)) != set(
        manifest["buildArgs"]
    ):
        fail("Dockerfile image arguments do not equal the build manifest")
    for required_copy in (
        "COPY deploy/healthcheck.go ./healthcheck.go",
        "COPY --chown=10001:10001 --chmod=0444 web-config.yml /etc/node_exporter/web.yml",
    ):
        if required_copy not in dockerfile:
            fail(f"bounded Dockerfile input missing: {required_copy}")

    dockerignore = (ROOT / "codestra/.dockerignore").read_text(encoding="utf-8")
    expected_dockerignore = {
        "**",
        "!deploy/",
        "deploy/**",
        "!deploy/Dockerfile",
        "!deploy/healthcheck.go",
        "!web-config.yml",
    }
    if set(dockerignore.splitlines()) != expected_dockerignore:
        fail("Docker build context allowlist drift")

    compose = yaml.safe_load(
        (ROOT / "codestra/deploy/compose.candidate.yaml").read_text(encoding="utf-8")
    )
    service = compose.get("services", {}).get("node-exporter", {})
    if service.get("build", {}).get("context") != "..":
        fail("Compose build context must resolve to codestra/")
    if service.get("build", {}).get("dockerfile") != "deploy/Dockerfile":
        fail("Compose Dockerfile path mismatch")
    if service.get("privileged") is True or service.get("ports"):
        fail("unsafe runtime privilege or port publication")
    if service.get("network_mode") == "host" or service.get("pid") == "host":
        fail("host network and host PID are prohibited")

    release = yaml.safe_load(
        (ROOT / ".github/workflows/release-image.yml").read_text(encoding="utf-8")
    )
    release_job = release.get("jobs", {}).get("release", {})
    if release_job.get("uses") != EXPECTED_RELEASE_AUTHORITY:
        fail("release job does not pin the canonical image workflow authority")
    if release_job.get("with", {}).get("image_id") != "node-exporter":
        fail("release job image identity mismatch")

    for workflow in (ROOT / ".github/workflows").glob("*.yml"):
        source = workflow.read_text(encoding="utf-8")
        for reference in re.findall(r"(?m)^\s*(?:-\s*)?uses:\s*([^\s#]+)", source):
            if reference.startswith("./"):
                continue
            if not re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", reference):
                fail(f"mutable action reference in {workflow.relative_to(ROOT)}: {reference}")


def main() -> None:
    validate()
    print("NODE_EXPORTER_REPOSITORY_READINESS_SOURCE=PASS")
    print("ARTIFACT_MODEL=SIGNED_IMAGE")
    print("PRODUCTION_ACTIVATION=NO")


if __name__ == "__main__":
    main()
