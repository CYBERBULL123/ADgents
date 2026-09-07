# Agent OS (Developer Guide)

## Summary

Agent OS is ADGents' lightweight runtime kernel that manages autonomous agent executions ("Pods"). It provides:

- Pod lifecycle management (create, suspend, resume, stop)  
- Hierarchical tracing (Traces & Spans) for observability and auditing  
- Token/cost accounting per-run  
- Integrated SRE self-healing interventions for automated recovery  
- Plugin integration (skills/tools) registration and lifecycle

This page documents the architecture, data model, developer APIs, and extension points you will use when working on or extending the kernel.

## Quick file map

- `core/agent.py` — ReAct engine, agent lifecycle, and `Agent.run()` orchestration
- `core/trace_db.py` — SQLite schema and CRUD helpers for `pods`, `traces`, `spans`, and `healing_interventions`
- `core/sre_supervisor.py` — Diagnosis and healing logic (applies memory patches, param overrides, state resets)
- `core/plugin_manager.py` — Dynamic plugin discovery and skill registration
- `server.py` — FastAPI endpoints that expose pod controls and observability APIs

## Design overview

Agent OS treats each autonomous run as a `Pod`. A `Pod` has one or more `Traces`; each `Trace` contains ordered `Spans` that represent discrete runtime events (LLM calls, skill invocations, operator interventions, SRE diagnostics).

Key invariants:

- Spans are append-only records used to reconstruct the agent's execution path.  
- Healing interventions are recorded separately and reference the span that triggered the intervention.  
- The Agent runtime polls the kernel DB for `pod.status` to support operator-driven suspend/resume semantics.

## State machine (Pod)

States: `running` → `suspended` ↔ `running`; `running` → `healing` → `running | failed | completed`

- `running`: normal execution.  
- `suspended`: Agent run is paused by operator; `Agent.run()` blocks and polls until state changes.  
- `healing`: SRE supervisor is diagnosing/applying patches.  
- `completed`: normal completion.  
- `failed`: unrecoverable failure.

## Database schema (excerpts)

The kernel DB is `data/db/agent_os.db`. Key tables (see `core/trace_db.py` for full DDL):

pods (columns):

```sql
CREATE TABLE pods (
	id TEXT PRIMARY KEY,
	name TEXT NOT NULL,
	status TEXT NOT NULL DEFAULT 'running',
	agent_id TEXT NOT NULL,
	task_text TEXT NOT NULL,
	tokens_used INTEGER DEFAULT 0,
	cost REAL DEFAULT 0.0,
	created_at TEXT NOT NULL,
	updated_at TEXT NOT NULL
)
```

traces (columns):

```sql
CREATE TABLE traces (
	id TEXT PRIMARY KEY,
	pod_id TEXT,
	name TEXT NOT NULL,
	status TEXT NOT NULL DEFAULT 'running',
	started_at TEXT NOT NULL,
	completed_at TEXT,
	total_tokens INTEGER DEFAULT 0,
	total_cost REAL DEFAULT 0.0
)
```

spans (columns):

```sql
CREATE TABLE spans (
	id TEXT PRIMARY KEY,
	trace_id TEXT NOT NULL,
	parent_span_id TEXT,
	name TEXT NOT NULL,
	span_type TEXT NOT NULL,
	input TEXT,
	output TEXT,
	status TEXT NOT NULL DEFAULT 'pending',
	started_at TEXT NOT NULL,
	completed_at TEXT,
	tokens_input INTEGER DEFAULT 0,
	tokens_output INTEGER DEFAULT 0,
	cost REAL DEFAULT 0.0,
	error TEXT
)
```

healing_interventions (columns):

```sql
CREATE TABLE healing_interventions (
	id TEXT PRIMARY KEY,
	pod_id TEXT NOT NULL,
	span_id TEXT NOT NULL,
	error_message TEXT NOT NULL,
	diagnosis TEXT,
	patch_type TEXT,
	patch_content TEXT,
	created_at TEXT NOT NULL
)
```

## Span types and payloads

- `thought`: LLM-generated reasoning or internal state notes.  
- `llm`: a single LLM completion request/response. `input` and `output` may contain token counts.  
- `action`: a skill/tool invocation. `input` is the tool arguments; `output` is tool result (JSON or string).  
- `observation`: human-readable result summary after action.  
- `SRE_diagnosis` / `SRE_patch`: SRE findings and applied patches.

When writing code that updates spans, prefer `core/trace_db.create_span()` and `update_span()` helpers to ensure serialization and timestamping are consistent.

## Agent runtime: `Agent.run()` (developer notes)

- Creates/updates a `Pod` record via `create_pod()` / `update_pod()`.  
- Creates a root `Trace` and a root `span` for the run.  
- Executes a ReAct loop: call LLM (`llm.complete()`), inspect response for tool calls, execute skills via `SkillRegistry.execute()`.  
- For each LLM call and skill execution, a `span` is created and updated with status, tokens, cost, output.  
- On LLM/skill errors, sets `pod.status='healing'` and invokes `SRE_SUPERVISOR.diagnose_and_heal()` which returns a patch record; the agent applies the patch if appropriate.

Common integration points:

- `create_span(span_id, trace_id, name, span_type, parent_span_id, input_data)` — create a span.  
- `update_span(span_id, status=..., output=..., tokens_input=..., tokens_output=..., cost=...)` — finalize a span.  
- `update_pod(pod_id, status='healing')` — mark pod for SRE actions.

Example: how `Agent.run()` checks pod suspension (pseudocode):

```py
pod = get_pod(pod_id)
if pod and pod['status'] == 'suspended':
		# agent will poll until pod.status != 'suspended' or becomes failed
		while get_pod(pod_id)['status'] == 'suspended':
				time.sleep(1)
```

## SRE supervisor (healing) behaviors

The SRE supervisor can apply three primary patch types:

- `memory_append`: Add context or instructions to working memory to influence the next LLM iteration.  
- `param_override`: Replace or override parameters when retrying a failed skill (e.g., change search limit, timeout, or prompt parameters).  
- `state_reset`: Suggest clearing working memory or restarting the pod when state is inconsistent.

Every applied or attempted intervention is persisted using `create_healing_intervention(...)` and referenced in spans for audit.

## Server API (developer reference)

Relevant endpoints (see `server.py` for full handlers):

- `GET  /api/pods` — list pods, optional query `?status=running`  
- `GET  /api/pods/{pod_id}` — get pod + healing interventions  
- `POST /api/pods/{pod_id}/suspend` — set pod status to `suspended`  
- `POST /api/pods/{pod_id}/resume` — set pod status back to `running`  
- `POST /api/pods/{pod_id}/stop` — set pod status to `failed`

Example curl to suspend:

```bash
curl -X POST http://localhost:8000/api/pods/<pod_id>/suspend
```

Note: these routes are currently unauthenticated in the reference implementation—add auth middleware before exposing to untrusted networks.

## Concurrency and SQLite

- The kernel uses a single SQLite file. SQLite is reliable for small-scale parallelism but can raise `sqlite3.OperationalError: database is locked` under heavy concurrent writes.  
- Recommendations:
	- Keep DB writes short and batched where possible.  
	- Use `PRAGMA journal_mode=WAL` for better concurrency.  
	- For high-scale setups, migrate `agent_os` to a client/server DB (Postgres) or run a dedicated DB service.

## Plugin/Skill manager notes

- `core/plugin_manager.py` dynamically imports plugin modules from `core/plugins` and instantiates classes subclassing `BasePlugin`.  
- Each plugin exposes skills registered into the global `SKILL_REGISTRY`.  
- Risks: dynamic imports instantiate arbitrary code. For production:
	- Require signed plugin manifests or an allowlist.  
	- Run untrusted plugins in isolated processes or sandboxes.

## Recommended developer tasks & tests

- Add unit tests for `core/trace_db` functions (create/get/update/delete).  
- Add integration tests that run `Agent.run()` with a mock LLM returning deterministic tool-calls and verify spans/healing interventions are created.  
- Add a test to validate `update_*` helpers only accept allowed columns to prevent SQL injection via column names.  
- Add CI checks for `PRAGMA journal_mode` or DB migration scripts if moving to Postgres.

## Extension points

- SRE policy: `core/sre_supervisor.py` can be extended with more heuristics (rate-limits, adaptive backoff, prompt rewriting).  
- Observability: export spans to OTLP/Jaeger by adding an exporter in `update_span()` hooks.  
- Plugin lifecycle: add plugin registration hooks (on_connect/on_disconnect) and config validation.

## Troubleshooting

- Symptom: `Agent.run()` blocks and never resumes — check `pods.status` in `data/db/agent_os.db`.  
- Symptom: frequent `database is locked` — enable WAL, reduce concurrent writers, or move to Postgres.  
- Symptom: tool failures not retried — check `SRE_SUPERVISOR.diagnose_and_heal()` behavior and whether `patch_type` returned is applied by the agent.

## Reference code locations

- Agent runtime: [core/agent.py](core/agent.py)  
- Kernel DB: [core/trace_db.py](core/trace_db.py)  
- SRE logic: [core/sre_supervisor.py](core/sre_supervisor.py)  
- Plugin manager: [core/plugin_manager.py](core/plugin_manager.py)  
- API surface: [server.py](server.py)

---