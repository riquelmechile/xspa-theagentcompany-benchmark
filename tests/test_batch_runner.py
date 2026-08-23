import json
import tempfile
import unittest
from pathlib import Path

from harness import batch_runner as br


class BatchRunnerTests(unittest.TestCase):
    def test_remaining_tasks_are_frozen_in_manifest_order(self):
        self.assertEqual(len(br.REMAINING_TASKS), 16)
        self.assertEqual(br.REMAINING_TASKS[0], "admin-arrange-meeting-rooms")
        self.assertEqual(br.REMAINING_TASKS[-1], "bm-classify-nationality")
        self.assertEqual(br.REMAINING_TASKS[7], "sde-check-and-run-unit-test")

    def test_direct_codex_args_fail_closed_and_ignore_user_config(self):
        args = br.codex_args("direct", "test prompt")
        joined = " ".join(args)
        self.assertIn("--ignore-user-config", args)
        self.assertIn("--ephemeral", args)
        self.assertIn("gpt-5.6-sol", args)
        self.assertIn('model_reasoning_effort="max"', args)
        for feature in ("apps", "plugins", "remote_plugin", "browser_use", "computer_use"):
            self.assertIn(feature, args)
        self.assertNotIn("dangerously-bypass-approvals-and-sandbox", joined)

    def test_xspa_codex_args_keep_apps_but_disable_other_capabilities(self):
        args = br.codex_args("xanxitospa", "test prompt")
        disabled = [args[i + 1] for i, value in enumerate(args[:-1]) if value == "--disable"]
        self.assertNotIn("apps", disabled)
        self.assertIn("plugins", disabled)
        self.assertIn("remote_plugin", disabled)
        self.assertIn("browser_use", disabled)
        self.assertIn("computer_use", disabled)

    def test_direct_trajectory_rejects_any_mcp_call(self):
        lines = [
            json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "cat task.md"}}),
            json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "codex_apps", "tool": "xanxito.mcp_read", "arguments": {}}}),
        ]
        with self.assertRaises(br.IsolationError):
            br.validate_trajectory("direct", "\n".join(lines))

    def test_xspa_trajectory_accepts_bounded_read_only_preflight(self):
        lines = [
            json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "cat task.md"}}),
            json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "codex_apps", "tool": "xanxito.mcp_server_tools", "arguments": {"name": "xanxitospa"}}}),
            json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "codex_apps", "tool": "xanxito.mcp_read", "arguments": {"server": "xanxitospa", "tool": "xspa_skills_search", "arguments": {"query": "testing"}}}}),
            json.dumps({"type": "item.completed", "item": {"type": "command_execution", "command": "curl http://127.0.0.1:8929"}}),
        ]
        report = br.validate_trajectory("xanxitospa", "\n".join(lines))
        self.assertEqual(report["mcp_calls"], 2)
        self.assertTrue(report["required_preflight_seen"])

    def test_xspa_trajectory_rejects_hostops_or_other_downstream(self):
        bad_hostops = json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "codex_apps", "tool": "xanxito.host_exec", "arguments": {}}})
        with self.assertRaises(br.IsolationError):
            br.validate_trajectory("xanxitospa", bad_hostops)
        bad_server = "\n".join([
            json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "codex_apps", "tool": "xanxito.mcp_server_tools", "arguments": {"name": "xanxitospa"}}}),
            json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "codex_apps", "tool": "xanxito.mcp_read", "arguments": {"server": "controlmcp", "tool": "anything", "arguments": {}}}}),
        ])
        with self.assertRaises(br.IsolationError):
            br.validate_trajectory("xanxitospa", bad_server)

    def test_prepare_arm_dir_refuses_existing_clean_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "trajectory.jsonl").write_text("x")
            (p / "eval.json").write_text("{}")
            with self.assertRaises(br.EvidenceExistsError):
                br.prepare_arm_dir(p)


if __name__ == "__main__":
    unittest.main()
