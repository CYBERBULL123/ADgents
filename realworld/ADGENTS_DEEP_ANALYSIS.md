# ADgents - Deep Technical Analysis

**Reviewed:** 2026-11-20
**Git snapshot:** `dev` at `534f2e8` (2026-11-13), plus uncommitted working-tree changes
**Assessment type:** Source and history review; not a penetration test or production certification

## Executive Summary

ADgents is a self-hosted agent application built around a custom Python ReAct loop, a FastAPI server, a browser Studio, SQLite-backed records, and direct HTTP adapters for several LLM APIs. It does not currently depend on LangChain or CrewAI. Its product direction is best described as a small, understandable agent host with persona configuration, callable skills, local memory, runtime visibility, and protocol interfaces, not as a feature-for-feature replacement for large agent frameworks.

The source does not support claims of production readiness, cluster readiness, best-in-market memory, broad crew orchestration, or safe arbitrary code execution. The project is marked Beta in `pyproject.toml`. The current worktree now has optional bearer authentication, fail-closed non-loopback API behavior, default-disabled high-risk tools, serialized per-agent execution, bounded retries, and focused regression tests. These are meaningful local-first hardening steps, not production certification.

There is useful functionality in the current tree: autonomous task execution, persisted task and trace data, Markdown workflow skills, an Agent OS operations view, a working subset of A2A 1.0, an MCP implementation, and a functional Studio. The next upgrade should prioritize security boundaries, deterministic task execution, configuration correctness, and regression tests before adding distributed infrastructure.

## Project Scorecard

The ratings below describe the initial reviewed snapshot; see Upgrade Progress for verified changes in the current worktree.

**Overall current-state rating: 5/10.** ADgents is a promising Beta/local-first product with real working features, but correctness, security, and test coverage are not yet strong enough to call it production-ready. **Product direction and potential: 7/10. Current production readiness: 2/10.** Those are separate judgments: the idea and feature set are ahead of the hardening and verification in the current implementation.

Ratings use one scale: 1 means missing or seriously blocked, 5 means usable with material gaps, and 10 means consistently implemented, tested, and operationally mature. The overall score is the simple, equally weighted average of the 11 dimensions below. These are engineering judgments for the reviewed source snapshot, not benchmarks or competitor rankings.

| Dimension | Rating | Why |
|---|---:|---|
| Product focus | 7/10 | A single-agent platform with personas, tools, Studio, and Agent Card interoperability is a clear and achievable direction. Some legacy routes and disabled features still make the surface confusing. |
| Agent execution | 6/10 | The ReAct loop, task steps, and tool handling are implemented, but shared mutable agent state, synchronous chat calls, and an unbounded SRE retry path weaken predictability. |
| Studio usability | 7/10 | Studio supports agent management, chat, tasks, Agent OS, skills, settings, and A2A response inspection. It has no automated browser regression suite. |
| Protocol interoperability | 6/10 | A2A discovery and JSON-RPC `SendMessage`/`GetTask` were manually exercised against the official sample, but the implementation deliberately supports only a subset. MCP transports exist, while the Studio lifecycle indicator is not a real process lifecycle. |
| Memory | 5/10 | Persistent per-agent SQLite text memory and a separate knowledge category work, but retrieval is basic keyword matching; the optional vector index is transient and not a production embedding store. |
| Maintainability | 5/10 | Core concepts have separate modules, but the API server is a large central module, route registrations are duplicated, and disabled/legacy modules remain. |
| LLM integration | 5/10 | Several direct provider adapters and a mock provider exist, but configuration propagation, model selection, tool-call parity, and provider-specific cost accounting need correction. |
| Security | 2/10 | A2A has destination checks and optional inbound bearer auth, but the general API is unauthenticated and exposes unrestricted code, filesystem, and outbound HTTP capabilities. |
| Reliability and testing | 2/10 | Persistent task/trace records and some error handling exist, but concurrency and retry edge cases remain; no Python tests or CI workflows were found. |
| Operations and deployment | 4/10 | Startup scripts and Docker Compose provide a usable single-host path, but tasks are process-local, SQLite has no migration/backup process, health is shallow, and defaults expose the service on all interfaces. |
| Documentation | 6/10 | Installation, project, and protocol guides exist and the deep analysis has been refreshed, but historical feature drift and unsupported quality claims existed and should be checked across the remaining docs. |

The equal-weight arithmetic reflects the initial reviewed snapshot, not the current in-progress worktree. Security and production-readiness are intentionally not averaged away as a footnote: the remaining gaps still block an internet-facing production claim.

## Upgrade Progress

The following changes are implemented and covered by focused tests in the current worktree:

| Area | Verified change | Remaining limitation |
|---|---|---|
| API boundary | Optional `ADGENTS_API_TOKEN` protects REST, MCP, A2A task, and WebSocket entry points. Non-loopback requests fail closed if no token is configured. | This is one shared bearer token, not per-user identity, role-based authorization, or tenant isolation. Use HTTPS for remote traffic. |
| Tool policy | Arbitrary Python, filesystem/network built-ins, and Python custom skills are hidden and blocked by default. | Explicit opt-in is not a sandbox; there are no OS/container isolation guarantees or fine-grained approvals. |
| Agent execution | A per-agent lock serializes mutable runs; per-task thought callbacks are restored after completion; sync chat runs off the event loop. | One agent cannot execute multiple tasks concurrently, and cancellation is cooperative. |
| Retries and LLM settings | SRE prompt retries consume the iteration limit; provider models and Gemini key aliases use environment settings; router reload preserves references held by agents. | Provider-specific tool-call parity and accurate billing rates still need work. |
| SDK and IDE | SDK task calls poll the started task; IDE fallback uses the actual `Persona` and `Agent` constructor contracts. | Broader API contract coverage remains needed. |
| MCP | Start/stop now gates the mounted HTTP JSON-RPC endpoint; Studio reports the actual transport and path. | The HTTP transport is JSON-RPC, not SSE; stdio remains a separate process. |

Focused tests currently cover these changes. CI, full API workflow coverage, independent authorization, sandboxed execution, durable job processing, and deployment operations remain open.

## Review Scope and Snapshot

The review read the current source, runtime configuration, packaging files, and recent Git history. Findings below are based on code paths, not product-documentation claims.

At review time, `HEAD` was commit `534f2e8` on branch `dev`. The worktree also contained uncommitted changes to `server.py`, Studio files, and documentation, plus the new `core/a2a_registry.py` and A2A guide. These changes include the Agent Card/peer registry work and should be treated as in-progress until committed and covered by repeatable tests.

At initial review, no `test_*.py` files or `.github/workflows` files were found. The current worktree now contains focused Python tests and a GitHub Actions test workflow; broader API/protocol coverage remains incomplete. A manual interoperability test against the official A2A Hello World sample was performed earlier in this work session; it is not a committed regression test.

## Current Architecture

| Area | Actual implementation |
|---|---|
| HTTP application | FastAPI routes and application wiring are concentrated in `server.py`. The module also loads `.env`, loads saved personas into a process-local dictionary, mounts Studio and MCP routes, and configures CORS. |
| Agent runtime | `core/agent.py` implements `think()` for a synchronous chat turn and `run()` for a bounded-iteration ReAct loop with tool calls, task steps, traces, and SRE hooks. |
| LLM adapters | `core/llm.py` implements direct HTTP calls for OpenAI, Gemini, Anthropic, Ollama, and Mock. The router normalizes responses, but provider tool-call behavior is not uniform. |
| Persona persistence | `core/agent_store.py` stores persona JSON under `data/agents`; active `Agent` instances and working memory live in process memory. |
| Memory | `core/memory.py` stores episodic and semantic records in per-agent SQLite files. Working memory is in-memory. The optional vector helper is rebuilt in memory and uses hashed token counts, not a durable embedding service. |
| Callable tools | `core/skills.py` registers built-in and persisted custom Python handlers. `core/agent_skills.py` separately stores Markdown workflow instructions and injects assigned content into prompts. |
| Tasks and runtime traces | `core/task_db.py` stores task history; `core/trace_db.py` stores pods, traces, spans, and SRE interventions in SQLite. These are separate databases from persona and memory storage. |
| Browser interface | `studio/index.html`, `studio/app.js`, and `studio/style.css` implement a vanilla JavaScript/CSS single-page Studio. It calls the FastAPI endpoints directly. |
| Other interfaces | `cli.py` provides Typer/Rich commands; `sdk/python/adgents.py` is an HTTP wrapper; `core/mcp_server.py` exposes MCP stdio and HTTP routes. |
| A2A | The current working tree adds a generated Agent Card route, JSON-RPC `SendMessage`/`GetTask`, outbound peer discovery/delegation, and a SQLite peer registry. See [the A2A guide](../docs/project/a2a.md). |

### Runtime and Persistence Model

On server import, saved persona JSON files are loaded into a global `agents` dictionary. Each `Agent` owns mutable working memory, status, current task, trace/pod identifiers, and a default thought callback. Public `think()` and `run()` calls now serialize on a per-agent lock; autonomous task callbacks are scoped to a call and restored afterward. Agent state remains process-local. Creating or deleting a persona updates JSON storage; conversational state is not restored on restart. Episodic/semantic memories, tasks, traces, and remote peer cards use separate SQLite files. The tables are created with `CREATE TABLE IF NOT EXISTS`; no migration framework or schema-version process was found.

`POST /api/chat` uses `Agent.think()` for ordinary chat and `Agent.run()` for autonomous chat. `POST /api/tasks` schedules a background runner, executes the agent in a thread, streams thought-step events over `/ws/{agent_id}`, and writes task history when execution ends. This is process-local background work, not a durable job queue: a server restart can lose active work.

## Feature Status From Source

| Feature | Status | Evidence-based description |
|---|---|---|
| Persona agents | Implemented | Five templates and custom personas are defined in `core/persona.py`; saved personas reload at server startup. Persona attributes shape prompts and skill selection. |
| ReAct tasks | Implemented, single-process | The agent can call registered tools, collect observations, retry some errors, and stop at an iteration limit. It is not a distributed execution engine. |
| Memory | Implemented with limited retrieval | Working memory is a bounded message list. Episodic and semantic entries share SQLite storage and use keyword `LIKE` search ordered by importance/recency. There is no demonstrated forgetting policy or memory archival. |
| Vector search | Optional prototype | `VectorMemory` requires optional NumPy/FAISS imports not listed as project dependencies. Its fallback embedding is a fixed-width hashed bag of tokens, and its index is process-local. Do not describe this as durable semantic embedding search. |
| Built-in skills | Implemented with a default-deny policy for high-risk tools | Search, calculations, parsing, and utility handlers are available by default. Arbitrary code, filesystem/network built-ins, and Python custom skills require explicit environment opt-in; the opt-in does not provide sandboxing. |
| Markdown Agent Skills | Implemented | Named `SKILL.md` workflows are persisted under `data/agent_skills` and selected workflow content is added to the agent prompt. These are instructions, not isolated executable plugins. |
| Agent OS | Implemented as cooperative controls and SQLite traces | Pods, traces, spans, and interventions are recorded. Suspend/stop is checked between agent-loop iterations; it does not kill or isolate an operating-system process. SRE repair is LLM-generated prompt/parameter guidance, not verified code repair. |
| A2A | Limited implementation in the current worktree | The new routes publish `/.well-known/agent-card.json` and support JSON-RPC 1.0 `SendMessage` and `GetTask`, plus remote card discovery and outbound tasks. This is not full A2A feature coverage. |
| MCP | HTTP JSON-RPC lifecycle is controllable; stdio is standalone | `core/mcp_server.py` implements stdio JSON-RPC and an HTTP router mounted at `/mcp`. Start/stop gates the HTTP routes; the HTTP server's agent list is captured at import time. The mounted transport is not SSE. |
| Crews | Removed/disabled | Crew implementation files were deleted. `/api/crews` and crew communication routes return disabled responses. There is no active crew planner, delegation engine, or parallel crew execution in the current server. |
| Plugin integrations | Disabled, with legacy residue | Plugin database and manager functions are stubs. `core/plugin_manager.py` still imports `core.plugins.base_plugin`, but no `core/plugins` source directory exists in the current tree, so importing that module is expected to fail. |
| Legacy A2A simulator | Dormant and distinct from wire protocol | `core/a2a_protocol.py` contains in-memory message objects and queues. The new Agent Card JSON-RPC routes do not use it; it is not itself a network A2A implementation. |

## Refactors and Feature Evolution

This timeline is derived from Git history, not the earlier report:

| Date | Commit | Verified change |
|---|---|---|
| 2026-04-17 | `74c551b` | Removed `core/langchain_integration.py` and LangChain dependencies; simplified the server and Studio around the in-house agent and provider code. |
| 2026-08-16 | `ef450c3` | Added plugin database/manager and integrations. |
| 2026-09-07 | `99d8dfd` | Disabled plugin integrations and removed provider implementations and UI paths. Stub modules remain. |
| 2026-09-28 | `d923df6` | Deleted Crew implementation and removed related routes/UI code; current compatibility endpoints report crews as disabled. |
| 2026-10-13 | `8a898b3` | Added autonomous chat/task execution and progress-tracking changes. |
| 2026-10-23 | `7c88e21` | Added Markdown-based Agent Skills storage, assignment, and Studio management. |
| 2026-11-13 | `534f2e8` | Added Agent OS task-management UI and WebSocket improvements. |
| Current uncommitted work | Worktree changes | Adds the Agent Card/A2A peer workflow and response inspection UI; the implementation is not represented by the current `HEAD` commit. |

The product has therefore moved away from crews and plugin integrations toward a simpler single-agent runtime, reusable Markdown workflows, operational trace visibility, and protocol-based interoperability. The old competitive report described features that were later removed.

## Verified Risks and Correctness Gaps

### High Priority: Security Boundary

- `start.py`, `cli.py serve`, and the direct `server.py` entry point now default to `127.0.0.1`; Docker Compose publishes to host loopback by default. Explicit `API_HOST` or `ADGENTS_BIND_ADDRESS` overrides can still expose the service.
- The API now accepts a shared `ADGENTS_API_TOKEN` bearer token for REST, MCP, A2A task, and WebSocket paths. Non-loopback requests fail closed when no token is configured. This is not per-user authorization, and the public Agent Card route remains discoverable.
- High-risk built-ins and Python custom skills are hidden and blocked unless explicitly enabled with environment flags. When enabled, Python execution and custom handlers still run without an OS/container sandbox; filesystem paths and outbound HTTP destinations still need fine-grained containment.
- The A2A peer fetcher has useful HTTPS/private-address/redirect checks by default, but those A2A checks do not constrain the general `api_call` tool or other application routes.

**Assessment:** Local defaults are safer and remote API access has a shared-token boundary, but this is not production-ready. Use HTTPS, rotate tokens, and do not enable unsafe tools on an exposed service.

### High Priority: Shared Agent State and Blocking Requests

- Agents remain global mutable instances, but `think()` and `run()` now serialize per agent; task callbacks are passed per run and restored. This prevents overlapping mutations but limits throughput for each agent.
- `/api/chat` now sends synchronous `think()` work to a thread. Provider adapters still use synchronous `httpx.Client` calls with up to 180-second timeouts, and long calls are not immediately cancellable.
- Agent OS suspend/stop is cooperative and checked at loop boundaries. A long provider call or tool call cannot be interrupted immediately.

**Remaining upgrade:** Adopt per-run state rather than shared mutable agent memory, add async provider clients or managed worker execution, and define cancellation/task ownership before adding worker scaling.

### High Priority: Retry and Provider Configuration

- SRE `memory_append` retries now consume the configured iteration budget, preventing the previously unbounded provider-failure loop.
- The shared LLM router now reloads in place so existing agents see provider changes; OpenAI/Gemini/Claude model variables and the Gemini `GOOGLE_API_KEY` alias are honored.
- Usage cost in the agent loop is a fixed formula for all providers/models, not provider-specific billing data. Treat trace cost as a rough placeholder, not a billable estimate.

### Correctness and Product Surface

- The no-agent fallback in `/api/ide/refactor` now uses the real `Persona` type and `llm_router` constructor keyword.
- SDK `Agent.run_task()` now polls the task it starts. The API persists an initial `running` record so polling has a stable task resource.
- The installed `adgents` entry point now targets `start:main` and starts Uvicorn. The optional Typer CLI still needs `typer` and `rich`, which are not listed in the base runtime dependencies.
- MCP start/stop now gates the mounted HTTP JSON-RPC routes. Its agent snapshot still does not refresh when agents are created or deleted later.
- `server.py` registers duplicate `/` handlers and duplicate `/api/templates` handlers. The earlier template handler currently wins by route order; the later disabled duplicate is misleading and fragile. The earlier root redirect similarly shadows the later root handler.
- Disabled crew/plugin compatibility routes and modules remain alongside the new interfaces. This creates ambiguity for maintainers and SDK callers.

### Testing, Build, and Operations

- Focused Python regression tests now exist for config defaults, agent execution/retries, LLM reload, SDK task polling, MCP lifecycle, skill policy, and API authentication. The suite is not yet a comprehensive API/protocol regression suite.
- `Makefile lint` appends `|| true` to lint commands, so lint failures do not fail the target. `make docs` expects MkDocs, while no `mkdocs.yml` was found. Build/test/lint targets are not currently reliable quality gates.
- The existing package workflow now installs the `dev` extra and runs the focused suite across its Python/OS matrix. It does not yet include linting or broader protocol/API tests.
- `pyproject.toml` labels the package Beta. The wheel now includes SDK modules and Studio assets; a local wheel build and archive inspection passed. Startup and writable data-directory behavior in a clean installed environment still need an end-to-end smoke test.
- The API health handler returns `healthy` and `database_status: ready` without performing a database readiness check. Treat it as a basic status endpoint, not a production readiness probe.

## Recommended Upgrade Plan

Prioritize the smallest changes that make the current single-host product safer and predictable. Do not start with Redis, Celery, or a broad framework rewrite.

1. **Finish the security boundary.** Add per-user authorization if multi-user access is intended, refine secrets/deployment handling, and use HTTPS for remote access.
2. **Contain opt-in tools.** Add a real OS/container sandbox, canonical file allowlists, outbound HTTP destination controls, and enforced approval semantics before enabling high-risk tools.
3. **Make agent runs fully isolated and cancellable.** Replace shared working memory with per-run state and define cancellation/ownership before scaling workers.
4. **Complete provider correctness.** Test each provider's tool-call round trip and replace the fixed cost approximation with explicit provider/model pricing metadata.
5. **Repair remaining packaging and route issues.** Remove duplicate route registrations and test installed-wheel startup with a writable data directory.
6. **Establish release gates.** Expand API/A2A tests and add CI that fails on test/lint errors.
7. **Then improve operational visibility.** Make health checks verify dependencies, label token/cost estimates accurately, define data retention and SQLite backup/migration policy, and only scale beyond one process after moving mutable runtime state to a deliberate job/state architecture.

## Bottom Line

The strongest verified differentiator is the focused, inspectable runtime: personas, a small tool registry, persistent text memory, Studio task visibility, Markdown workflow skills, and an emerging A2A surface. The refactors that removed LangChain, crews, and plugins materially changed the product; they should be reflected consistently in source, SDK behavior, UI, and docs.

The project is a promising Beta/local-first platform, not a production-ready or horizontally scalable service today. The current work has closed several immediate correctness and default-exposure gaps, with focused tests. The next meaningful upgrades are real isolation for powerful tools, per-user authorization if needed, durable/cancellable task execution, packaging/CI gates, and operational data policies. Keep the product simple while making those core paths dependable.
