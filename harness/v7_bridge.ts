import path from "node:path";
import { pathToFileURL } from "node:url";

interface BridgeInput {
  scenarioId: string;
  arm: "direct" | "xanxitospa";
  step: { op: string; [key: string]: unknown };
  state: Record<string, unknown>;
}

async function main(): Promise<void> {
const input = JSON.parse(process.argv[2] ?? "null") as BridgeInput | null;
if (!input || !input.scenarioId || !input.arm || !input.step?.op) throw new Error("V7_BRIDGE_INPUT_INVALID");
const xspaRoot = process.env.XSPA_REPO?.trim() || process.cwd();
if (!xspaRoot) throw new Error("XSPA_REPO_REQUIRED");
const databaseUrl = process.env.V7_DATABASE_URL?.trim();

const importFromXspa = async (relative: string) => import(pathToFileURL(path.join(xspaRoot, relative)).href);
const database = await importFromXspa("packages/database/src/index.ts");
const runtime = await importFromXspa("apps/mcp/src/runtime.ts");

const state = structuredClone(input.state ?? {});
const measurement: Record<string, unknown> = { op: input.step.op };
const scenarioCompany = input.scenarioId === "stale-idempotency-settlement"
  ? (input.arm === "direct" ? "71000000-0000-4000-8000-000000000001" : "71000000-0000-4000-8000-000000000002")
  : (input.arm === "direct" ? "72000000-0000-4000-8000-000000000001" : "72000000-0000-4000-8000-000000000002");

async function withDb<T>(fn: (db: any) => Promise<T>): Promise<T> {
  if (!databaseUrl) throw new Error("V7_DATABASE_URL_REQUIRED");
  const db = new database.PostgresDatabase(databaseUrl);
  try { return await fn(db); }
  finally { await db.close(); }
}

async function ensureXspa(db: any, companyId: string): Promise<any> {
  await db.migrate(path.join(xspaRoot!, "packages/database/migrations"));
  await db.ensureCompany(companyId, `V7 ${input.scenarioId} ${input.arm}`, "v7-benchmark", 1);
  return new database.PostgresRuntimeStore(db);
}

async function staleIdempotency(): Promise<void> {
  const key = "v7:stale-settlement";
  await withDb(async (db) => {
    if (input.arm === "direct") {
      await db.pool.query(`CREATE TABLE IF NOT EXISTS public.v7_direct_idempotency (
        company_id uuid NOT NULL, idem_key text NOT NULL, state text NOT NULL, owner text NOT NULL,
        result jsonb, updated_at timestamptz NOT NULL DEFAULT clock_timestamp(), PRIMARY KEY(company_id, idem_key)
      )`);
      if (input.step.op === "setup") {
        await db.pool.query("DELETE FROM public.v7_direct_idempotency WHERE company_id=$1 AND idem_key=$2", [scenarioCompany, key]);
        measurement.reset = true; return;
      }
      if (input.step.op === "claim-a") {
        const q = await db.pool.query("INSERT INTO public.v7_direct_idempotency(company_id,idem_key,state,owner) VALUES($1,$2,'intent','worker') ON CONFLICT DO NOTHING RETURNING owner", [scenarioCompany, key]);
        measurement.claimed = q.rowCount === 1; return;
      }
      if (input.step.op === "wait-stale") {
        await new Promise((resolve) => setTimeout(resolve, Number(input.step.ms ?? 20)));
        measurement.waitedMs = Number(input.step.ms ?? 20); return;
      }
      if (input.step.op === "takeover-b") {
        const q = await db.pool.query("UPDATE public.v7_direct_idempotency SET state='unknown',owner='worker',updated_at=clock_timestamp() WHERE company_id=$1 AND idem_key=$2 RETURNING owner", [scenarioCompany, key]);
        measurement.takenOver = q.rowCount === 1; return;
      }
      if (input.step.op === "settle-fresh") {
        const q = await db.pool.query("UPDATE public.v7_direct_idempotency SET state='reconciled',result=$3::jsonb,updated_at=clock_timestamp() WHERE company_id=$1 AND idem_key=$2 AND owner='worker'", [scenarioCompany, key, JSON.stringify({ owner: "fresh" })]);
        measurement.accepted = q.rowCount === 1; return;
      }
      if (input.step.op === "settle-stale") {
        const q = await db.pool.query("UPDATE public.v7_direct_idempotency SET state='applied',result=$3::jsonb,updated_at=clock_timestamp() WHERE company_id=$1 AND idem_key=$2 AND owner='worker'", [scenarioCompany, key, JSON.stringify({ owner: "stale" })]);
        measurement.accepted = q.rowCount === 1; return;
      }
      if (input.step.op === "observe") {
        const q = await db.pool.query("SELECT state,owner,result FROM public.v7_direct_idempotency WHERE company_id=$1 AND idem_key=$2", [scenarioCompany, key]);
        measurement.finalState = q.rows[0]?.state ?? null;
        measurement.finalOwner = q.rows[0]?.result?.owner ?? null;
        return;
      }
      throw new Error(`V7_UNKNOWN_STEP:${input.step.op}`);
    }

    const store = await ensureXspa(db, scenarioCompany);
    if (input.step.op === "setup") {
      await db.withCompanyTransaction(scenarioCompany, (client: any) => client.query("DELETE FROM xspa.idempotency_journal WHERE company_id=$1 AND idempotency_key=$2", [scenarioCompany, key]));
      measurement.reset = true; return;
    }
    if (input.step.op === "claim-a") {
      const claim = await store.claimIdempotency(scenarioCompany, key, { operation: "v7" }, "worker", new Date());
      state.tokenA = claim.record.fencingToken;
      measurement.claimed = claim.claimed;
      measurement.fencingToken = claim.record.fencingToken;
      return;
    }
    if (input.step.op === "wait-stale") {
      await new Promise((resolve) => setTimeout(resolve, Number(input.step.ms ?? 20)));
      measurement.waitedMs = Number(input.step.ms ?? 20); return;
    }
    if (input.step.op === "takeover-b") {
      const takeover = await store.claimStaleIdempotencyForReconciliation(scenarioCompany, key, "worker", new Date(), 1);
      state.tokenB = takeover?.fencingToken ?? null;
      measurement.takenOver = Boolean(takeover);
      measurement.fencingToken = takeover?.fencingToken ?? null;
      return;
    }
    if (input.step.op === "settle-fresh") {
      measurement.accepted = await store.markIdempotency(scenarioCompany, key, "worker", Number(state.tokenB), "reconciled", new Date(), { owner: "fresh" }); return;
    }
    if (input.step.op === "settle-stale") {
      measurement.accepted = await store.markIdempotency(scenarioCompany, key, "worker", Number(state.tokenA), "applied", new Date(), { owner: "stale" }); return;
    }
    if (input.step.op === "observe") {
      const record = await store.getIdempotency(scenarioCompany, key);
      measurement.finalState = record?.state ?? null;
      measurement.finalOwner = (record?.result as any)?.owner ?? null;
      return;
    }
    throw new Error(`V7_UNKNOWN_STEP:${input.step.op}`);
  });
}

async function staleHeartbeatCursor(): Promise<void> {
  const oldEvent = { id: "72000000-0000-4000-8000-000000000011", companyId: scenarioCompany, type: "ops.old", occurredAt: "2026-08-25T20:00:00.000Z", actorPrincipal: "v7", correlationId: "72000000-0000-4000-8000-000000000021", idempotencyKey: "v7:old", payload: {}, sensitivity: "internal", evidenceRefs: [] };
  const newEvent = { ...oldEvent, id: "72000000-0000-4000-8000-000000000012", type: "ops.new", occurredAt: "2026-08-25T20:01:00.000Z", correlationId: "72000000-0000-4000-8000-000000000022", idempotencyKey: "v7:new" };
  await withDb(async (db) => {
    if (input.arm === "direct") {
      await db.pool.query(`CREATE TABLE IF NOT EXISTS public.v7_direct_heartbeat (
        company_id uuid PRIMARY KEY, lease_owner text, lease_until timestamptz,
        cursor_occurred_at timestamptz, cursor_event_id uuid
      )`);
      if (input.step.op === "setup") { await db.pool.query("DELETE FROM public.v7_direct_heartbeat WHERE company_id=$1", [scenarioCompany]); measurement.reset = true; return; }
      if (input.step.op === "claim-a") {
        await db.pool.query("INSERT INTO public.v7_direct_heartbeat(company_id,lease_owner,lease_until) VALUES($1,'daemon',clock_timestamp()+interval '10 milliseconds') ON CONFLICT(company_id) DO UPDATE SET lease_owner='daemon',lease_until=clock_timestamp()+interval '10 milliseconds'", [scenarioCompany]); measurement.claimed = true; return;
      }
      if (input.step.op === "wait-expiry") { await new Promise((resolve) => setTimeout(resolve, Number(input.step.ms ?? 30))); measurement.waitedMs = Number(input.step.ms ?? 30); return; }
      if (input.step.op === "claim-b") {
        const q = await db.pool.query("UPDATE public.v7_direct_heartbeat SET lease_owner='daemon',lease_until=clock_timestamp()+interval '60 seconds' WHERE company_id=$1 AND lease_until <= clock_timestamp()", [scenarioCompany]); measurement.claimed = q.rowCount === 1; return;
      }
      if (input.step.op === "advance-new") {
        const q = await db.pool.query("UPDATE public.v7_direct_heartbeat SET cursor_occurred_at=$2,cursor_event_id=$3 WHERE company_id=$1 AND lease_owner='daemon' AND lease_until>clock_timestamp()", [scenarioCompany, newEvent.occurredAt, newEvent.id]); measurement.accepted = q.rowCount === 1; return;
      }
      if (input.step.op === "stale-advance-old") {
        const q = await db.pool.query("UPDATE public.v7_direct_heartbeat SET cursor_occurred_at=$2,cursor_event_id=$3 WHERE company_id=$1 AND lease_owner='daemon' AND lease_until>clock_timestamp()", [scenarioCompany, oldEvent.occurredAt, oldEvent.id]); measurement.accepted = q.rowCount === 1; return;
      }
      if (input.step.op === "observe") {
        const q = await db.pool.query("SELECT cursor_occurred_at,cursor_event_id FROM public.v7_direct_heartbeat WHERE company_id=$1", [scenarioCompany]); measurement.finalEventId = q.rows[0]?.cursor_event_id ?? null; return;
      }
      throw new Error(`V7_UNKNOWN_STEP:${input.step.op}`);
    }

    const store = await ensureXspa(db, scenarioCompany);
    if (input.step.op === "setup") {
      await db.withCompanyTransaction(scenarioCompany, async (client: any) => { await client.query("DELETE FROM xspa.heartbeat_cursors WHERE company_id=$1", [scenarioCompany]); await client.query("DELETE FROM xspa.heartbeat_leases WHERE company_id=$1", [scenarioCompany]); });
      measurement.reset = true; return;
    }
    if (input.step.op === "claim-a") { const lease = await store.claimHeartbeatLease(scenarioCompany, "daemon", new Date(), 10); state.leaseA = lease; measurement.claimed = Boolean(lease); measurement.fencingToken = lease?.fencingToken ?? null; return; }
    if (input.step.op === "wait-expiry") { await new Promise((resolve) => setTimeout(resolve, Number(input.step.ms ?? 30))); measurement.waitedMs = Number(input.step.ms ?? 30); return; }
    if (input.step.op === "claim-b") { const lease = await store.claimHeartbeatLease(scenarioCompany, "daemon", new Date(), 60_000); state.leaseB = lease; measurement.claimed = Boolean(lease); measurement.fencingToken = lease?.fencingToken ?? null; return; }
    if (input.step.op === "advance-new") { measurement.accepted = await store.saveHeartbeatCursor(state.leaseB as any, newEvent as any, new Date()); return; }
    if (input.step.op === "stale-advance-old") { measurement.accepted = await store.saveHeartbeatCursor(state.leaseA as any, oldEvent as any, new Date()); return; }
    if (input.step.op === "observe") { const cursor = await store.getHeartbeatCursor(scenarioCompany, new Date()); measurement.finalEventId = cursor.lastEventId ?? null; return; }
    throw new Error(`V7_UNKNOWN_STEP:${input.step.op}`);
  });
}

async function ownerWriteNotAuthority(): Promise<void> {
  if (input.step.op === "setup") { state.resolved = false; measurement.ownerCredentialPresent = false; return; }
  if (input.step.op === "attempt-owner-write") {
    if (input.arm === "direct") { state.resolved = true; measurement.accepted = true; measurement.authorizationBasis = "write-permission"; return; }
    const store = new database.InMemoryRuntimeStore();
    const operations = new runtime.EnvironmentXspaAppOperations({ store, companyId: "73000000-0000-4000-8000-000000000001", databaseConfigured: true, creativeConfigured: false, kastConfigured: false });
    const fact = { id: "fact:owner-claim", statement: "Operator claims owner authority", status: "owner-confirmed", confidence: 1, evidenceRefs: ["ev:operator"], provenance: "operator" };
    try {
      await operations.companyDiscoveryApply({ discoveryId: "73000000-0000-4000-8000-000000000011", evidence: [{ id: "ev:operator", source: { id: "src:operator", kind: "operator", label: "Operator" }, kind: "operator-assertion", observedAt: "2026-08-25T20:00:00.000Z", statement: "Operator assertion", confidenceCeiling: 1 }], facts: [fact], unknowns: [], capabilities: [] }, { principal: "operator", scopes: ["xspa.write"] });
      state.resolved = true; measurement.accepted = true;
    } catch (error) {
      state.resolved = false; measurement.accepted = false; measurement.error = error instanceof Error ? error.message : "unknown";
    }
    return;
  }
  if (input.step.op === "observe") { measurement.resolved = Boolean(state.resolved); measurement.ownerCredentialPresent = false; return; }
  throw new Error(`V7_UNKNOWN_STEP:${input.step.op}`);
}

if (input.scenarioId === "stale-idempotency-settlement") await staleIdempotency();
else if (input.scenarioId === "stale-heartbeat-cursor") await staleHeartbeatCursor();
else if (input.scenarioId === "write-permission-is-not-owner") await ownerWriteNotAuthority();
else throw new Error(`V7_SCENARIO_UNKNOWN:${input.scenarioId}`);

process.stdout.write(JSON.stringify({ measurement, state }));
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack ?? error.message : String(error));
  process.exitCode = 1;
});
