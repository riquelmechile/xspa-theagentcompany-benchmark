import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from harness.v6_sut import capture_sut_pin, freeze_v6_manifest, validate_frozen_v6_manifest

class V6SutPinTest(unittest.TestCase):
    def repo(self):
        td = tempfile.TemporaryDirectory()
        path = Path(td.name)
        subprocess.run(["git", "init", "-q", str(path)], check=True)
        (path / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n")
        (path / "x.txt").write_text("x\n")
        subprocess.run(["git", "-C", str(path), "add", "."], check=True)
        subprocess.run(["git", "-C", str(path), "-c", "user.name=V6", "-c", "user.email=v6@example.invalid", "commit", "-q", "-m", "fixture"], check=True)
        return td, path

    def test_captures_clean_commit_and_lock_hash(self):
        td, path = self.repo()
        try:
            pin = capture_sut_pin(path)
            self.assertTrue(pin["treeClean"])
            self.assertEqual(len(pin["commitSha"]), 40)
            self.assertEqual(len(pin["packageLockSha256"]), 64)
        finally:
            td.cleanup()

    def test_dirty_tree_is_recorded_and_cannot_be_frozen(self):
        td, path = self.repo()
        try:
            (path / "x.txt").write_text("dirty\n")
            pin = capture_sut_pin(path)
            self.assertFalse(pin["treeClean"])
            with self.assertRaisesRegex(ValueError, "dirty-sut"):
                freeze_v6_manifest({"schemaVersion": 6}, pin, "a" * 40)
        finally:
            td.cleanup()

    def test_manifest_fingerprint_commits_sut_and_runner(self):
        sut = {"commitSha": "b" * 40, "treeClean": True, "packageLockSha256": "c" * 64}
        a = freeze_v6_manifest({"schemaVersion": 6, "scenario": "one"}, sut, "d" * 40)
        b = freeze_v6_manifest({"schemaVersion": 6, "scenario": "one"}, {**sut, "commitSha": "e" * 40}, "d" * 40)
        self.assertNotEqual(a["manifestFingerprint"], b["manifestFingerprint"])

    def test_frozen_manifest_requires_exact_runtime_pins(self):
        sut = {"commitSha": "b" * 40, "treeClean": True, "packageLockSha256": "c" * 64}
        manifest = freeze_v6_manifest({"schemaVersion": 6, "status": "frozen-before-outcomes"}, sut, "d" * 40)
        validate_frozen_v6_manifest(manifest, sut, "d" * 40)
        with self.assertRaisesRegex(ValueError, "runner-drift"):
            validate_frozen_v6_manifest(manifest, sut, "e" * 40)
        with self.assertRaisesRegex(ValueError, "sut-drift"):
            validate_frozen_v6_manifest(manifest, {**sut, "commitSha": "a" * 40}, "d" * 40)

    def test_repository_manifest_is_frozen_and_no_v6_outcomes_exist(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "manifest" / "v6-design.json").read_text())
        self.assertEqual(manifest["status"], "frozen-before-outcomes")
        self.assertEqual(manifest["executionContractSource"], "shared-executor-v2")
        self.assertRegex(manifest["sut"]["commitSha"], r"^[0-9a-f]{40}$")
        self.assertRegex(manifest["sut"]["packageLockSha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(manifest["runnerCommitSha"], r"^[0-9a-f]{40}$")
        self.assertRegex(manifest["manifestFingerprint"], r"^[0-9a-f]{64}$")
        self.assertFalse(any("v6" in path.name.lower() for path in (root / "results").iterdir()))

if __name__ == "__main__": unittest.main()
