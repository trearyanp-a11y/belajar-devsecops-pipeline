"""Run the deployment script against controlled external command boundaries."""

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipIf(os.name == "nt", "Deployment runs on Linux")
class DeploymentTests(unittest.TestCase):
    """Exercise checksum, HTTP, revision, and manifest behavior without a cluster."""

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.revision = "a" * 40
        self.artifact = self.root / "artifact"
        self.artifact.mkdir()
        data = b"scanned image fixture"
        (self.artifact / "image.tar").write_bytes(data)
        (self.artifact / "image.tar.sha256").write_text(
            hashlib.sha256(data).hexdigest() + "  image.tar\n", encoding="utf-8"
        )
        self.source = Path(__file__).resolve().parents[1]
        shutil.copy(self.source / "k8s-deployment.yaml", self.root)
        self.env = os.environ.copy()
        self.env.update(
            PATH=str(self.bin) + os.pathsep + self.env["PATH"],
            TEST_ROOT=str(self.root),
            TEST_REVISION=self.revision,
        )
        self.command(
            "sudo",
            '#!/bin/bash\n'
            'if [[ "$3" == "apply" ]]; then cat > "$TEST_ROOT/applied.yaml"; fi\n',
        )
        self.command(
            "curl",
            '#!/usr/bin/env python3\n'
            'import json, os, sys\n'
            'if os.getenv("HTTP_FAILURE"): sys.exit(22)\n'
            'payload = {"status":"ok","service":"flask-auth-app","database":"ready"} '
            'if sys.argv[-1].endswith("/health") else '
            '{"revision":os.getenv("OLD_REVISION",os.environ["TEST_REVISION"])}\n'
            'print(json.dumps(payload))\n',
        )

    def tearDown(self):
        self.directory.cleanup()

    def command(self, name, text):
        """Only emulate commands that would contact the VM or HTTP service."""
        path = self.bin / name
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)

    def run_deploy(self):
        """Execute the real shell script, including real checksum and JSON checks."""
        return subprocess.run(
            ["bash", str(self.source / "scripts/deploy.sh"), str(self.artifact), self.revision],
            cwd=self.root, env=self.env, capture_output=True, text=True, check=False,
        )

    def test_verified_image_is_applied_with_the_commit_tag(self):
        """Rebuilding or failing to replace latest would violate the image contract."""
        result = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = (self.root / "applied.yaml").read_text(encoding="utf-8")
        self.assertIn("image: secure-flask-app:" + self.revision, manifest)
        self.assertIn("Deployment verified", result.stdout)

    def test_modified_archive_stops_before_applying_the_manifest(self):
        """A mismatched artifact must never reach Kubernetes apply."""
        (self.artifact / "image.tar").write_bytes(b"modified artifact")
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FAILED", result.stdout)
        self.assertFalse((self.root / "applied.yaml").exists())

    def test_http_failure_cannot_report_deployment_success(self):
        """A failing curl must propagate rather than be replaced by echo."""
        self.env["HTTP_FAILURE"] = "1"
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.root / "applied.yaml").exists())
        self.assertNotIn("Deployment verified", result.stdout)

    def test_old_revision_cannot_report_deployment_success(self):
        """An HTTP 200 from an old application is not proof of a new deployment."""
        self.env["OLD_REVISION"] = "b" * 40
        result = self.run_deploy()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(self.env["OLD_REVISION"], result.stderr)
        self.assertNotIn("Deployment verified", result.stdout)


if __name__ == "__main__":
    unittest.main()
