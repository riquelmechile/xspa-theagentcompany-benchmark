import json
import tempfile
import unittest
from pathlib import Path

from harness import chatgpt_host_runner as hr
from harness import batch_runner as br


class ChatGPTHostRunnerTests(unittest.TestCase):
    def test_module_never_spawns_a_model_or_codex(self):
        source = Path(hr.__file__).read_text(encoding="utf-8").lower()
        self.assertNotIn("codex", source)
        self.assertNotIn("openai_api_key", source)
        self.assertNotIn("model_reasoning_effort", source)
        self.assertNotIn("node:24-bookworm", source)
        self.assertNotIn("scenarios.json", source)

    def test_hosted_dataset_uses_distinct_arm_directories(self):
        self.assertNotEqual(hr.HOST_ARM_DIRS["direct"], br.ARM_DIRS["direct"])
        self.assertNotEqual(hr.HOST_ARM_DIRS["xanxitospa"], br.ARM_DIRS["xanxitospa"])

    def test_npc_running_matches_shell_or_python_child(self):
        top = """UID PID PPID C STIME TTY TIME CMD
root 1 0 0 18:31 ? 00:00:00 /bin/sh -c python_default /npc/run_one_npc.py --agent_name=\"Sarah Johnson\"
root 2 1 0 18:31 ? 00:00:00 python_default /npc/run_one_npc.py --agent_name=Emma Lewis
"""
        self.assertTrue(hr.npc_is_running(top, "Sarah Johnson"))
        self.assertTrue(hr.npc_is_running(top, "Emma Lewis"))
        self.assertFalse(hr.npc_is_running(top, "Priya Sharma"))

    def test_parse_launched_npcs_uses_init_log_only(self):
        log = "Resetting services...\nLaunching Priya Sharma\ncmd\nLaunching Sophia Rodriguez\ncmd\nLaunching Zhang Wei\n"
        self.assertEqual(hr.parse_launched_npcs(log), ["Priya Sharma", "Sophia Rodriguez", "Zhang Wei"])

    def test_task_container_uses_official_hostname_with_loopback_mapping(self):
        source = Path(hr.__file__).read_text(encoding="utf-8")
        self.assertIn("SERVER_HOSTNAME=the-agent-company.com", source)
        self.assertIn("--add-host", source)
        self.assertIn("the-agent-company.com:127.0.0.1", source)

    def test_direct_audit_rejects_mcp(self):
        events = [hr.mcp_event("xanxito.mcp_read", {"server": "xanxitospa", "tool": "xspa_status", "arguments": {}})]
        text = "\n".join(json.dumps(e) for e in events)
        with self.assertRaises(br.IsolationError):
            br.validate_trajectory("direct", text)

    def test_xspa_audit_accepts_discovery_and_read_only_read(self):
        events = [
            hr.command_event("cat /workspace/task.md", "task", 0),
            hr.mcp_event("xanxito.mcp_server_tools", {"name": "xanxitospa"}),
            hr.mcp_event("xanxito.mcp_read", {"server": "xanxitospa", "tool": "xspa_status", "arguments": {}}),
        ]
        text = "\n".join(json.dumps(e) for e in events)
        gate = br.validate_trajectory("xanxitospa", text)
        self.assertTrue(gate["required_preflight_seen"])
        self.assertEqual(gate["mcp_calls"], 2)

    def test_xspa_audit_rejects_execution_before_preflight(self):
        events = [
            hr.command_event("cat /workspace/task.md", "task", 0),
            hr.command_event("curl http://127.0.0.1:3000", "oops", 0),
            hr.mcp_event("xanxito.mcp_server_tools", {"name": "xanxitospa"}),
            hr.mcp_event("xanxito.mcp_read", {"server": "xanxitospa", "tool": "xspa_status", "arguments": {}}),
        ]
        text = "\n".join(json.dumps(e) for e in events)
        with self.assertRaises(br.IsolationError):
            br.validate_trajectory("xanxitospa", text)

    def test_command_event_is_codex_trajectory_compatible(self):
        event = hr.command_event("python -V", "Python 3.12", 0)
        self.assertEqual(event["type"], "item.completed")
        item = event["item"]
        self.assertEqual(item["type"], "command_execution")
        self.assertEqual(item["status"], "completed")
        self.assertEqual(item["exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
