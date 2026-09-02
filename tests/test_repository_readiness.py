from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class RepositoryReadinessTests(unittest.TestCase):
    def test_validator_passes(self) -> None:
        subprocess.run(
            ["python3", "scripts/validate_repository_readiness.py"],
            cwd=ROOT,
            check=True,
        )

    def test_release_job_is_structurally_pinned(self) -> None:
        workflow = yaml.safe_load(
            (ROOT / ".github/workflows/release-image.yml").read_text()
        )
        job = workflow["jobs"]["release"]
        self.assertEqual(
            job["uses"],
            "appolon1908-hue/Codestra-Telemetry/.github/workflows/"
            "reusable-release-image.yml@"
            "9a6aebb849bbc068105c10d9d1dfd39ebf6f78bd",
        )
        self.assertEqual(job["with"]["image_id"], "node-exporter")

    def test_build_args_equal_runtime_base_lock(self) -> None:
        manifest = json.loads(
            (ROOT / "codestra/release/image-build.v1.json").read_text()
        )
        lock = json.loads(
            (ROOT / "codestra/release/runtime-base.lock.json").read_text()
        )
        self.assertEqual(manifest["buildArgs"]["GO_BUILDER_IMAGE"], lock["builderImage"])
        self.assertEqual(
            manifest["buildArgs"]["NODE_EXPORTER_BASE_IMAGE"],
            lock["runtimeBaseImage"],
        )
        self.assertEqual(lock["binaryRevisionReadback"], lock["upstreamTagCommit"])
        self.assertTrue(lock["buildFrontendImage"].startswith("docker.io/docker/dockerfile@sha256:"))

    def test_docker_context_is_allowlisted(self) -> None:
        dockerignore = (ROOT / "codestra/.dockerignore").read_text().splitlines()
        self.assertEqual(dockerignore[0], "**")
        self.assertIn("!deploy/Dockerfile", dockerignore)
        self.assertIn("!deploy/healthcheck.go", dockerignore)
        self.assertIn("!web-config.yml", dockerignore)


if __name__ == "__main__":
    unittest.main()
