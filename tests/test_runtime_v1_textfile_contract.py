from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RuntimeV1TextfileContractTests(unittest.TestCase):
    def test_legacy_unauthenticated_compose_is_absent(self) -> None:
        self.assertFalse((ROOT / "codestra/runtime-v1/compose.yaml").exists())
        candidate = (ROOT / "codestra/deploy/compose.candidate.yaml").read_text()
        self.assertIn("--web.config.file=/etc/node_exporter/web.yml", candidate)
        self.assertIn("prometheus_client_ca", candidate)

    def test_renderer_uses_only_canonical_metric_names_and_exporter_group(self) -> None:
        contract = json.loads(
            (ROOT / "codestra/textfile/metric-contract.v1.json").read_text()
        )
        allowed = {metric["name"] for metric in contract["metrics"]}
        renderer = (
            ROOT / "codestra/runtime-v1/render_codestra_textfile_metrics.sh"
        ).read_text()
        required = {
            "codestra_node_textfile_contract_info",
            "codestra_node_deployment_info",
            "codestra_node_backup_last_success_timestamp_seconds",
            "codestra_node_restore_validation_last_success_timestamp_seconds",
            "codestra_node_certificate_not_after_timestamp_seconds",
            "codestra_node_configuration_drift",
        }
        self.assertTrue(required <= allowed)
        for metric in required:
            self.assertIn(metric, renderer)
        for legacy in (
            "codestra_deployment_info",
            "codestra_backup_last_success_timestamp_seconds",
            "codestra_status_file_present",
        ):
            self.assertNotIn(legacy, renderer)
        self.assertIn('chown "0:${NODE_EXPORTER_GID}"', renderer)
        self.assertIn('chmod 0640 "${TMP}"', renderer)


if __name__ == "__main__":
    unittest.main()
