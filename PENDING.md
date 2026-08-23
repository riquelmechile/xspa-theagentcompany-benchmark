# Pending work

## Frozen 24-task manifest

1. `admin-arrange-meeting-rooms` — **PILOT ONLY — rerun under v2 hard isolation**
2. `admin-employee-info-reconciliation` — **PILOT ONLY — rerun under v2 hard isolation**
3. `admin-get-best-vendor-quote` — **PILOT ONLY — rerun under v2 hard isolation**
4. `ds-answer-numerical-data-question` — **PILOT ONLY — rerun under v2 hard isolation**
5. `ds-coffee-shop-database-management` — **PILOT ONLY — rerun under v2 hard isolation**
6. `ds-visualize-data-in-pie-and-bar-chart` — **PILOT ONLY — rerun under v2 hard isolation** — fixed Qwen evaluator is text-only; treat as execution-only/unscorable unless evaluator capability changes
7. `finance-budget-variance` — **PILOT ONLY — rerun under v2 hard isolation**
8. `finance-invoice-matching` — **DONE v2**
9. `finance-find-signatories` — **DONE v2**
10. `hr-check-attendance-multiple-days-department-with-chat` — **DONE v2**
11. `hr-resume-screening` — **SAFETY EXCLUDED**
12. `hr-salary-analysis` — **DONE v2**
13. `pm-ask-for-issue-and-create-in-gitlab` — **DONE v2**
14. `pm-copy-plane-issues-to-gitlab` — **DONE v2**
15. `pm-check-backlog-update-issues` — **DONE v2**
16. `sde-check-and-run-unit-test` — **PENDING v2**
17. `sde-debug-crashed-server` — **PENDING v2**
18. `sde-add-one-gitlab-pipeline` — **PENDING v2**
19. `qa-escalate-emergency` — **PENDING v2**
20. `qa-update-issue-status-according-to-colleagues` — **PENDING v2**
21. `research-answer-questions-on-paper` — **PENDING v2**
22. `research-reproduce-figures` — **PENDING v2**
23. `ml-grade-exam` — **PENDING v2**
24. `bm-classify-nationality` — **PENDING v2**

## Counts

- Clean v2 completed/scored pairs: **7**.
- Safety-excluded: **1** (`hr-resume-screening`).
- Remaining tasks requiring a clean v2 run or execution-only handling: **16**.
- Of those remaining, **7** have only old pilot results and therefore still require hard-isolation reruns.

## Before continuing

1. Stabilize the benchmark reset path so GitLab/Plane can be freshly restored without manual recovery races.
2. Keep raw trajectories local; update the SHA-256 evidence manifest after each new pair.
3. Continue in the frozen order; do not cherry-pick tasks.
4. Recompute the v2 aggregate only from clean capability-isolated pairs.
5. Do not combine the v1 pilot totals with v2.
