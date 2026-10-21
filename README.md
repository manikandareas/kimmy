# Kimmy - Fleet Operations Assistant

Kimmy is an operations chatbot for logistics truck fleet managers. Users ask questions in everyday language, and Kimmy answers from the company's actual data: it reads fleet data through **tools**, computes metrics deterministically in the backend, remembers **user memory notes** across threads, and refers to **company SOPs** through RAG with openable source citations.

The project focuses on three capabilities:

- **Tools** - the agent calls domain tools for trip, fuel consumption, operating hour, maintenance, and breakdown data. All calculations are performed by SQL/Python, never by the LLM.
- **Memory** - general notes the user explicitly asks Kimmy to remember are stored as free text, reused in new threads, and can be corrected or forgotten.
- **RAG** - three company SOPs are indexed as embedded chunks; answers include citations pointing to the exact chunks used.

Execution is **durable**: send a message and close the browser, and the work keeps running in the worker; the final result is still available when the page is reopened - with no duplicated answers.

---

## Architecture

The application is a modular monolith (backend and worker in one codebase) with a feature-based React frontend. A single PostgreSQL database serves fleet data, chat, memory, RAG documents, agent checkpoints, and the job queue.

```mermaid
flowchart LR
    U["Browser"] --> T["Dokploy / Traefik<br>Domain and HTTPS"]
    T --> W["web / Nginx<br>React and /api proxy"]
    W --> A["api / FastAPI<br>Commands, snapshots, SSE"]
    A --> P[("PostgreSQL + pgvector<br>Data, memory, runs, events, queue")]
    J["worker / Procrastinate"] <--> P
    J --> G["LangChain agent"]
    G --> F["Domain tools and RAG"]
    F --> P
    G --> L["OpenAI / OpenRouter"]
```

### Agent components

The agent is built with LangChain `create_agent` on top of LangGraph, with a PostgreSQL checkpoint per thread. The LLM only selects tools and composes explanations; every number is computed by backend services.

```mermaid
flowchart TB
    MSG["User message"] --> CTX["Run context<br>Thread checkpoint + memory recall"]
    CTX --> LLM["LLM<br>OpenAI / OpenRouter"]
    LLM --> DEC{"Needs data?"}
    DEC -->|"fleet data"| DT["Domain tools"]
    DEC -->|"SOP"| RAG["search_knowledge"]
    DEC -->|"memory"| MT["remember / forget_preference"]
    DEC -->|"no"| ANS["Final answer"]
    DT --> SVC["Domain service<br>Pure metric functions in Python"]
    SVC --> REPO["Repository"] --> PG[("PostgreSQL<br>7 fleet tables")]
    RAG --> EMB["Embeddings + pgvector<br>Versioned SOP chunks"]
    MT --> MEM[("General memory<br>Versioned revisions per user/note ID")]
    SVC --> LLM
    EMB --> LLM
    MEM --> LLM
    LLM --> DEC
```

Available tools:

| Tool | Purpose |
| --- | --- |
| `search_vehicles` | Finds vehicle candidates by unit_code, current depot, and technical status (derived from breakdowns/work orders) |
| `get_vehicle_activity` | Trips with derived distance (odometer difference) and engine-on/idle time from operation sessions, including historical depot snapshots |
| `analyze_fuel_consumption` | Fuel spend (liters x unit price) and full-to-full efficiency estimates per period/depot |
| `get_maintenance_history` | Work order history and schedule per unit, including recorded costs |
| `get_breakdown_history` | Breakdown history per unit and downtime from event interval overlap |
| `search_knowledge` | Retrieves relevant SOP chunks with citations |
| `remember_preference` | Stores or corrects a memory note the user explicitly asked to remember |
| `forget_preference` | Revokes a note from future recalls |

Operational tool results always carry `method`, `record_refs` (table name and id), `observed_period`, and `coverage`, so every number can be traced back to its source records. Errors are explicitly distinguished: `NO_DATA`, `VEHICLE_NOT_FOUND`, invalid input, and service failure.

### Streaming chat flow (durable execution)

Messages are not executed on an open HTTP connection. The API stores the message, run, and delivery atomically, then a worker executes it asynchronously. Every event is assigned a sequence number (`seq`) and persisted before being broadcast, so a reconnect simply replays the events that were missed.

```mermaid
sequenceDiagram
    participant UI as React
    participant API as FastAPI
    participant DB as PostgreSQL
    participant W as Worker
    UI->>API: Send message + request_key
    API->>DB: Store message, run, and delivery atomically
    API-->>UI: 202 + run_id
    W->>DB: Claim run (lease) and checkpoint
    W->>W: Run agent and tools
    W->>DB: Persist events, progress, and result
    Note over UI,W: Browser closed, worker keeps running
    UI->>API: Reopen: fetch snapshot
    API-->>UI: Transcript, status, through_seq
    UI->>API: SSE after through_seq
    API-->>UI: Replay stored events
```

Design consequences:

- `request_key` makes submission idempotent: the same payload returns the same run; a different payload with the same key is rejected.
- An SSE subscription only reads events; it never starts a model call.
- Cancel and retry are explicit commands; the final result is persisted before the run is marked complete.
- Events and messages are deduplicated on the client by `seq`, so a refresh never duplicates an answer.

---

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React, Vite, TypeScript, shadcn/ui, TanStack Query |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Agent | LangChain (`create_agent`), LangGraph with PostgreSQL checkpointing |
| LLM | OpenAI / OpenRouter via LangChain's native adapters; chat and embedding models configured separately |
| Database | PostgreSQL + pgvector (fleet data, chat, memory, SOP chunks, checkpoints, queue) |
| Job queue | Procrastinate (PostgreSQL-backed durable worker) |
| Deployment | Docker Compose via Dokploy; Traefik for domain/HTTPS; Nginx serves React and proxies `/api` |
| Quality gates | Ruff, mypy, ESLint, Prettier, TypeScript, build |

---

## Memory: how it works

Kimmy separates two kinds of memory:

**1. Conversation context (per thread).** Thread content is continued through LangGraph checkpoints in PostgreSQL. A new thread starts with an empty transcript.

**2. General user memory (across threads).** Long-term memory consists of free-text notes the user explicitly asked Kimmy to remember. There is a single main field, `content`, holding text; there is no category or preference-key whitelist. A user may have at most eight active notes, each at most 1,000 characters. IDs and revisions are metadata, not categories.

Storage and recall flow:

```mermaid
flowchart LR
    M["Explicit user instruction"] --> T["Structured tool call"]
    T --> V["Validate content<br>Limit of 8 notes, 1,000 characters"]
    V --> S[("PostgreSQL<br>Canonical revision per note ID")]
    S --> Q["SQL<br>All active notes"]
    Q --> C["Memory context for the run"]
    E["Correction or forget"] --> S
```

Rules:

- Notes are stored only from explicit instructions ("remember, ...") via a structured tool call; the backend binds `user_id` and `source_message_id` from the run as provenance evidence.
- A new note receives a stable ID; a correction uses the ID and the expected revision. Identical content is a no-op; a change creates a new revision atomically - there is exactly one active revision per user/ID.
- Recall fetches all active notes before the model call. Priority: the current message instruction, then memory, then application defaults. Memory is user context, not a system instruction and not evidence of fleet data.
- A new thread has an empty transcript with the same active memory; memory is not copied into permanent user messages.
- A correction or forget bumps a *generation* counter. Runs carrying an old generation are rejected at progress/publication, and checkpoints from an old generation are not reused; chat history remains stored and readable by the user. After invalidation, model context restarts from the current message and the active memory.
- The memory panel provides list, add, correct, and forget. Direct panel changes come from user action and do not fabricate a `source_message_id`; a chat source applies only to tool actions.
- Forgetting revokes recall without deleting the original chat history. The eight-note limit is rejected explicitly when full - notes are never dropped silently.

V1 memory deliberately uses no embeddings, vector search, decay, automatic capture, or summarization of whole conversations; embeddings and vector search are used for the SOPs (RAG), not for memory.

---

## RAG: company SOPs

Three simulated SOP documents form the knowledge base: `maintenance-policy.md`, `breakdown-procedure.md`, and `fuel-investigation.md`.

```mermaid
flowchart LR
    MD["SOP Markdown"] --> CH["Chunk by section"]
    CH --> EM["Configured embeddings"]
    EM --> PG[("pgvector + metadata")]
    Q["Question"] --> SEARCH["search_knowledge<br>Active version and relevance"]
    PG --> SEARCH
    SEARCH --> ANSWER["Answer with citation"]
    ANSWER --> READER["Source dialog<br>Section, version, excerpt"]
```

Indexing uses the document version/hash to deduplicate chunks and records the embedding model and dimensions. A citation may only point to a chunk the model actually received; when no SOP supports an answer, the answer states that limitation. SOP content is treated as data, not as instructions.

---

## Fleet data

The data is synthetic (no sample data was provided by the test giver) and generated deterministically: **12 vehicles, 2 depots, 60 days**, with consistent cross-record relationships - including one vehicle that transfers depots mid-period to prove the historical snapshot design.

Seven fleet tables:

```mermaid
erDiagram
    DEPOTS ||--o{ VEHICLES : current_base
    DEPOTS ||--o{ TRIPS : snapshot
    DEPOTS ||--o{ FUEL_ENTRIES : snapshot
    DEPOTS ||--o{ OPERATION_SESSIONS : snapshot
    VEHICLES ||--o{ TRIPS : operates
    VEHICLES ||--o{ FUEL_ENTRIES : refuels
    VEHICLES ||--o{ OPERATION_SESSIONS : runs
    VEHICLES ||--o{ MAINTENANCE_WORK_ORDERS : serviced
    VEHICLES ||--o{ BREAKDOWN_EVENTS : reports
    MAINTENANCE_WORK_ORDERS o|--o{ BREAKDOWN_EVENTS : handles
```

Data principles:

- **Derived values are never stored.** Trip distance = odometer difference; fuel spend = liters x unit price; a vehicle's technical status = derived from breakdowns/work orders. All are computed at query time by pure metric functions.
- **Depot snapshots.** Trips, fuel entries, and operation sessions store the depot at the time of the event, so historical reports do not change when a vehicle moves depots. `vehicles.depot_id` states the current depot.
- **Fuel efficiency is a full-to-full estimate**: the volume between two full fills (including partial fills in between) divided by the odometer difference; `reset_baseline` breaks an interval; an invalid meter reading only disqualifies its use as a boundary, not the volume/cost itself.
- **Operating hours come from `engine_on_seconds`** in operation_sessions, not from trip durations. Unavailable values stay null and are shown as unavailable - never silently replaced with zero.
- The seed deliberately includes edge cases: partial/unknown fills, empty/invalid meter readings, baseline resets, complete/partial/none operation coverage, work orders in varied statuses, an unresolved breakdown, and a fuel entry recorded late (`recorded_at` long after `occurred_at`).

---

## Running the project

### Prerequisites

- Docker and Docker Compose
- An OpenAI or OpenRouter API key (for the chat and embedding models)
- For deployment: a Dokploy instance

### Environment configuration

Copy `.env.example` to `.env` and fill in:

```bash
DATABASE_URL=postgresql://kimmy:kimmy@postgres:5432/kimmy
LLM_PROVIDER=openrouter            # or openai
OPENROUTER_API_KEY=                # fill in per provider
OPENAI_API_KEY=
LLM_MODEL=openai/gpt-4o-mini
EMBEDDING_MODEL=openai/text-embedding-3-small
DEMO_USER_ID=demo
```

### Deployment (Dokploy)

1. Connect the repository to a Dokploy Docker Compose service with `compose.yaml` as the compose path.
2. Fill in the environment: database, chat provider/model, embedding provider/model, and the demo user identity.
3. Set the domain for the `web` service (port 80) and enable HTTPS.
4. Deploy. Startup order is enforced by healthchecks: `postgres` healthy, then the `migrate` service (Alembic + queue/checkpointer schema setup) completes, then `api` and `worker` start.
5. Run the fleet seed explicitly - the seed only runs on empty fleet tables and refuses a database that already contains data.
6. Run SOP indexing; re-runs are safe because of version/hash deduplication.
7. Walk through the deployed domain, including refreshing the page mid-response and restarting the worker.

### Local development

`compose.local.yaml` adds local port access for PostgreSQL and the API. Day-to-day commands (development, migrations, seed, SOP indexing, lint, type check, build, logs) are available through the repository's Makefile/CLI.

---

## Repository structure

```txt
kimmy/
├── apps/
│   ├── api/            # Python backend: FastAPI + worker (same image, different commands)
│   │   └── src/kimmy/
│   │       ├── agent/      # Agent factory, context, checkpoints, tools
│   │       ├── chat/       # Router, service, events, streaming, recovery
│   │       ├── fleet/      # Fleet models, repository, pure metric functions
│   │       ├── memory/     # General user memory notes
│   │       ├── knowledge/  # SOP ingestion and search (RAG)
│   │       └── jobs/       # Procrastinate queue and tasks
│   └── web/            # React frontend (feature-based)
│       └── src/
│           ├── app/        # Page composition and routing
│           ├── features/   # chat and memory
│           └── components/ # shadcn/ui and shared components
├── knowledge/          # The three SOP Markdown files (RAG input)
├── compose.yaml        # Dokploy deployment
├── compose.local.yaml  # Local development overrides
├── Makefile
└── README.md
```

Module boundaries are strict: routers handle HTTP, services own domain rules, repositories own queries. Tools only validate input, call a service, and shape the result - no metric logic lives inside a tool or a prompt.

---

## Demo questions

1. "Remember, my favorite depot is Makassar. Please answer in Indonesian."
2. In a new thread: "Which truck is the least fuel-efficient this week? Compare it with last week."
3. "Check this unit's maintenance history and the relevant investigation SOP." (open the citation)
4. "The vehicle that moved depots this month - at which depot were its earlier fuel entries recorded?"
5. "Which fuel entries were recorded more than 24 hours after they occurred?"
6. Refresh the page while an answer is streaming - the same answer reappears without duplication.
7. "Forget my favorite depot note." The next thread no longer uses that note.