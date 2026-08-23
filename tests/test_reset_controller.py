import hashlib
import tempfile
import unittest
from pathlib import Path

from harness.reset_controller import (
    OFFICIAL_GITLAB_IMAGE,
    ResetError,
    assert_fingerprints_equal,
    gitlab_project_fingerprint,
    plan_gitlab_cleanup,
    plane_structural_fingerprint,
    validate_backup_set,
)


class ResetControllerTests(unittest.TestCase):
    def test_validate_backup_set_requires_all_three_official_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "pgdata.tar.gz").write_bytes(b"x" * 2048)
            (root / "redisdata.tar.gz").write_bytes(b"y" * 2048)
            with self.assertRaises(ResetError):
                validate_backup_set(root)

    def test_validate_backup_set_returns_sha256_for_valid_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            expected = {}
            for name, payload in {
                "pgdata.tar.gz": b"p" * 2048,
                "redisdata.tar.gz": b"r" * 2048,
                "uploads.tar.gz": b"u" * 2048,
            }.items():
                (root / name).write_bytes(payload)
                expected[name] = hashlib.sha256(payload).hexdigest()
            self.assertEqual(validate_backup_set(root), expected)

    def test_gitlab_cleanup_removes_only_official_conflicting_recovery_containers(self):
        containers = [
            {
                "Names": "gitlab",
                "Image": OFFICIAL_GITLAB_IMAGE,
                "Ports": "0.0.0.0:8929->8929/tcp",
                "Labels": "com.docker.compose.service=gitlab,com.docker.compose.project=theagentcompany",
            },
            {
                "Names": "gitlab-benchmark-recovery5",
                "Image": OFFICIAL_GITLAB_IMAGE,
                "Ports": "0.0.0.0:8930->443/tcp, 0.0.0.0:2424->22/tcp",
                "Labels": "",
            },
            {"Names": "unrelated", "Image": "postgres:16", "Ports": "5432/tcp", "Labels": ""},
        ]
        self.assertEqual(plan_gitlab_cleanup(containers), ["gitlab-benchmark-recovery5"])

    def test_gitlab_cleanup_preserves_compose_owned_alternate_runtime_name(self):
        containers = [
            {
                "Names": "gitlab-benchmark-canonical",
                "Image": OFFICIAL_GITLAB_IMAGE,
                "Ports": "0.0.0.0:8929->8929/tcp, 0.0.0.0:2424->22/tcp",
                "Labels": "com.docker.compose.service=gitlab,com.docker.compose.project=theagentcompany",
            }
        ]
        self.assertEqual(plan_gitlab_cleanup(containers), [])

    def test_gitlab_cleanup_removes_unmanaged_canonical_name(self):
        containers = [
            {
                "Names": "gitlab",
                "Image": OFFICIAL_GITLAB_IMAGE,
                "Ports": "0.0.0.0:8929->8929/tcp",
                "Labels": "",
            }
        ]
        self.assertEqual(plan_gitlab_cleanup(containers), ["gitlab"])

    def test_gitlab_cleanup_fails_closed_on_nonofficial_port_conflict(self):
        containers = [
            {"Names": "mystery", "Image": "example/not-gitlab:latest", "Ports": "0.0.0.0:8929->80/tcp", "Labels": ""},
        ]
        with self.assertRaises(ResetError):
            plan_gitlab_cleanup(containers)

    def test_gitlab_project_fingerprint_is_order_independent(self):
        a = gitlab_project_fingerprint(["root/janusgraph", "root/openhands"], OFFICIAL_GITLAB_IMAGE)
        b = gitlab_project_fingerprint(["root/openhands", "root/janusgraph"], OFFICIAL_GITLAB_IMAGE)
        self.assertEqual(a, b)

    def test_plane_fingerprint_is_order_independent(self):
        hashes_a = {"pgdata.tar.gz": "a", "redisdata.tar.gz": "b", "uploads.tar.gz": "c"}
        hashes_b = {"uploads.tar.gz": "c", "pgdata.tar.gz": "a", "redisdata.tar.gz": "b"}
        counts_a = {"workspaces_tac": 1, "projects_tac": 10, "issues_tac": 31}
        counts_b = {"issues_tac": 31, "projects_tac": 10, "workspaces_tac": 1}
        self.assertEqual(
            plane_structural_fingerprint(counts_a, hashes_a),
            plane_structural_fingerprint(counts_b, hashes_b),
        )

    def test_fingerprint_mismatch_fails_closed(self):
        with self.assertRaises(ResetError):
            assert_fingerprints_equal({"gitlab": "a", "plane": "b"}, {"gitlab": "a", "plane": "c"})


if __name__ == "__main__":
    unittest.main()
