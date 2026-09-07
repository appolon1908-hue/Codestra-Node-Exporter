"""Real renderer regressions using disposable status files, not host evidence."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "codestra/runtime-v1/render_codestra_textfile_metrics.sh"
METRIC = 'codestra_node_backup_last_success_timestamp_seconds{backup_scope="database"}'


class ScalarInputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.status = self.root / "status"
        self.status.mkdir()
        self.output = self.root / "output"
        self.env = dict(os.environ, NODE_TEXTFILE_DIR=str(self.output),
                        CODESTRA_STATUS_DIR=str(self.status), NODE_EXPORTER_GID=str(os.getegid()),
                        CODESTRA_APPLICATION="fixture", CODESTRA_SERVICE="host",
                        CODESTRA_DEPLOYMENT="test", CODESTRA_VERSION="test",
                        CODESTRA_GIT_SHA="a" * 40)
        self.input = self.status / "backup-database.last_success"

    def render(self) -> str:
        subprocess.run(["bash", str(SCRIPT)], env=self.env, check=True,
                       capture_output=True, text=True, timeout=5)
        return (self.output / "codestra_node.prom").read_text()

    def test_accepts_single_scalar_with_optional_final_newline(self) -> None:
        for value in (b"1788780000", b"1788780000\n"):
            with self.subTest(value=value):
                self.input.write_bytes(value)
                self.assertIn(METRIC + " 1788780000\n", self.render())

    def test_rejects_malformed_complete_files(self) -> None:
        for value in (b"", b"1788780000\n0\n", b"1788780000\n\n",
                      b"1788780000\x00\n", b"1788780000\r\n", b" 1788780000\n",
                      b"1788780000 \n", b"1788780000000\n", b"1788780000\n" + b"x" * 100000):
            with self.subTest(value=value[:30]):
                self.input.write_bytes(value)
                self.assertNotIn(METRIC, self.render())

    def test_rejects_non_regular_and_symlink_inputs(self) -> None:
        target = self.status / "real"
        target.write_text("1788780000\n")
        self.input.symlink_to(target)
        self.assertNotIn(METRIC, self.render())
        self.input.unlink()
        os.mkfifo(self.input)
        self.assertNotIn(METRIC, self.render())
        self.input.unlink()
        self.input.mkdir()
        self.assertNotIn(METRIC, self.render())

    def test_no_stale_success_and_readable_atomic_output(self) -> None:
        self.input.write_text("1788780000\n")
        self.assertIn(METRIC, self.render())
        self.input.write_text("1788780000\ninvalid\n")
        self.assertNotIn(METRIC, self.render())
        result = self.output / "codestra_node.prom"
        self.assertEqual(result.stat().st_mode & 0o777, 0o640)
        self.assertEqual(result.stat().st_gid, os.getegid())
        self.assertEqual(list(self.output.glob('.codestra_node.prom.*')), [])

    def test_drift_requires_one_complete_boolean(self) -> None:
        drift = self.status / "configuration-drift.state"
        metric = 'codestra_node_configuration_drift{'
        for value in (b"0\n", b"1"):
            drift.write_bytes(value)
            self.assertIn(metric, self.render())
        for value in (b"0\n1\n", b"1\x00", b"2", b"-1"):
            drift.write_bytes(value)
            self.assertNotIn(metric, self.render())


if __name__ == '__main__':
    unittest.main()
