# Protocol v2 — hard capability isolation

## Common controls

- Same TheAgentCompany 1.0.0 task image and task text.
- Same `gpt-5.6-sol` agent model with `model_reasoning_effort=max`.
- Same benchmark services and local environment/evaluator model.
- Fresh task state before each arm.
- Evaluator/checkpoint/grader implementation unavailable to the agent while solving.
- No internet answer lookup and no reuse of opposite-arm artifacts.
- Official raw evaluator scores are retained exactly; defects are annotations, not manual score overrides.

## DIRECT arm

Codex runs with Apps/MCP/plugins/remote-plugin/browser/computer-use disabled. It can use only the local task container shell/filesystem and the benchmark services required by the task.

## XANXITOSPA arm

Same model/container/service access as DIRECT. After reading `task.md`, it may perform a bounded task-aware read-only preflight through `@Xanxito` to downstream `xanxitospa`. Allowed calls are discovery/read operations such as `xspa_status`, `xspa_company_status`, `xspa_skills_search`, `xspa_skill_get`, and related read-only company/skill guidance.

Forbidden in the benchmark arm: HostOps, browser/computer-use, memory/SDD/review assistance, other downstream MCPs, external connectors, and MCP writes. A run that crosses that gate is invalid and excluded.

## Non-standard infrastructure recovery

Infrastructure recovery is allowed only to restore the intended official baseline, never to inject task answers. The canonical ledger documents the observed GitLab Docker-name/storage failure and Plane backup/DNS/startup races. Both arms must begin from equivalent recovered state.

## Reporting

- v1 is pilot/debug evidence only.
- v2 is the capability-isolated comparison.
- Broken graders remain in the raw score and are separately tagged.
- Safety-excluded tasks do not enter the denominator.
- Visual evaluator incompatibility with the fixed text-only environment model is execution-only/unscorable rather than silently scored as failure.
