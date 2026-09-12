# LLM Implementation Guidelines — agenthub (& the Platform Ecosystem)

The coding briefing for any AI assistant writing code in this repo. Read it before the first line.
It is the concrete-implementation companion to [BRAIN.md](./BRAIN.md) (how to *think*) — this file
is how to *build*, the `agenthub` way. Read [BRAIN.md](./BRAIN.md) first.

> **The one rule that overrides every other rule below:**
> **Match the existing codebase and platform. Convention beats principle.**
> When a SOLID/scalability/"best practice" instinct conflicts with how this repo and the platform
> already do it, the repo wins. Principles serve the code; the code does not serve the principles.

---

## 0. Think first — read the map

Before touching a file:

1. **Read the convention canon: [CLAUDE.md](../CLAUDE.md).** It is the live, authoritative
   description of this app's architecture — the nine absolute ground rules (apps/KBs-ARE-Services,
   sealed credentials, the single LLM gateway, SSRF-guarded fetch, no FK/JOIN with sanctioned raw-SQL
   spots, the two API surfaces, the RAG invariants, no CSS token overrides, queue-jobs-not-listeners),
   the strict ports, and the DB. **Above CLAUDE.md sits the platform-wide canon,
   [`framework-ai/`](../framework-ai/)** — the convention shared by *every* app on this platform:
   transport, release doctrine, the service model, `sanitize`, OAuth, DB. It is a symlink to
   `../framework-ai` (gitignored, recreated via `npm run link:docs`); read it as the platform
   authority (`framework-ai/transport.md`, `conventions.md`, `release-methods.md`, …). The hierarchy
   is **`framework-ai` (platform-wide) → CLAUDE.md (this app's concrete instantiation) → the code.**
   When both speak, CLAUDE.md's app-specific shape wins for *this* app.
   Then read the docs this app already ships, which are unusually complete — **use them, don't
   re-derive them:**
   - [`docs/plans/README.md`](../docs/plans/README.md) — the plan index: the master port plan
     (decisions D1–D5), phase plans 2–9 (decisions D6–D11), QA audits, and the post-parity feature
     wave. This is the app's own history of *why* each subsystem has its shape.
   - [`docs/plans/discovery/`](../docs/plans/discovery/) — read-only deep-maps of the upstream fork
     (chat-agent, knowledge indexing, retrieval, tools, file reading). The fork source may not exist
     on this machine; **these files ARE the mined knowledge** (§1.4).
   - [`docs/specs/`](../docs/specs/) — design specs for the chunk-settings / economy-index /
     qa-chunk / structured-doc / summary-index wave.
   For the whole data model at a glance — entities, columns, logical relationships — see
   [reference/database-erd.mmd](./reference/database-erd.mmd).
2. **Trace the data flow end-to-end** before changing anything. The `agenthub` chain has **no
   `modules/` directory and no listeners** — each domain co-locates its model, loader, and reader
   under `server/<domain>/`. The full chain:
   `schema (.sql) → server/<domain>/{model,loader,reader}.mjs → server/{apis,api}/*.mjs (routes) → src/services/api.js | stream.js → React`.
   Plus the async branch: `dispatch() → worker.mjs → server/kb/{indexer,cleanup,webimport}.mjs`.
   A change at one layer almost always has a counterpart at another. The generation runtime
   (`server/generate/*`), the RAG pipeline (`server/extract/*` + `server/kb/indexer.mjs` +
   `server/retrieval/`), the tool system (`server/tools/*`), and the `/v1` BaaS surface
   (`server/api/*`) are subsystems most sibling apps don't have — see §3.
3. **Look before building.** Search this repo and the platform first — the helper, loader, builtin
   tool, extract stage, or component you're about to write may already exist (§1, §2). This is
   doubly true for anything provider-facing: ALL model traffic already flows through one gateway
   (`server/llm/llm.mjs`) — extend it, never bypass it.
4. **Ask only when it changes the work** and you can't resolve it from code, docs, or convention.

**Domain context (for provider/KB/app/tool/BaaS work).** `agenthub` is an **LLM-app platform** — a
studio where a tenant configures AI apps (chat / agent / completion) grounded in knowledge bases and
tools, then serves them to end users via a Dify-compatible API — *not* a chatbot and *not* a
copilot. Before building a RAG/agent/BaaS feature, skim
[reference/llm-app-platform-foundations.md](./reference/llm-app-platform-foundations.md) for the
vocabulary (app modes, indexing techniques, chunk modes, retrieval modes, annotation reply, the
studio/BaaS duality) so you build at the right altitude. This is **orientation, not authority** for
current code shape — `CLAUDE.md`, the plans/specs, the schemas, and the ERD are that.

**Deciding *what* to build.** Before writing a feature/strategy plan (§0.3), run the product
diagnostic in [PRODUCT-DIAGNOSTIC.md](./PRODUCT-DIAGNOSTIC.md) — a builder-mode set of forcing
questions (real problem, who needs it, narrowest wedge, what already exists, prior art, alternatives)
that feeds a PREMISES + APPROACHES block straight into the plan doc.

### 0.1 Document the *why*, with evidence — cite your sources

Code says *what*; it rarely says *why*. Every non-obvious decision you make — a JSONB key vs a new
column, a cap, a wire-shape choice, a "we chose A over B" — must arrive **with its rationale and a
citation to an authority**, not just your judgment.

**Apply it here:**
- **Anchor to an authority, in priority order:** (1) an existing `agenthub`/platform convention
  (cite `file:line`, a `CLAUDE.md` passage, a `docs/plans/`/`docs/specs/` decision, or the
  platform-wide `framework-ai` canon); (2) a documented pattern from a credible product or standard
  (the upstream Dify fork via `docs/plans/discovery/`, the Anthropic/OpenAI API docs, the pgvector
  docs, an RFC) — quote it + link it; (3) a named engineering principle, only when (1) and (2)
  don't apply.
- **Cite inline.** A one-line `// why:` comment with a `file:line`/URL beats a paragraph of unsourced
  reasoning. This codebase already does this well — e.g. the `v1Error()` comment explaining why
  `/v1` errors bypass `ctx.error` (`server/api/v1.mjs`), or the 32 MB body-cap rationale in
  `dev-server.mjs`. Match that standard.
- **Record the trade-off.** When you pick A over B, say what B was and why A won.
- **"Modelled after X (cited)" outranks "seems right."** The port itself was built this way — every
  phase plan carries numbered decisions (D1–D11). If you can't find a source for a non-obvious
  choice, treat that as a signal to look harder or to ask — not to assert.

### 0.1.1 Verify before claiming — quote the line, or lower your confidence
§0.1 governs the *why*; this governs the *what*. Before you assert anything load-bearing about the
code — "this event isn't emitted", "no index covers this query", "that path isn't handled", "that's
already tested" — you must be able to **quote the specific `file:line` that motivates the claim,
verbatim**. If you cannot quote it, the claim is *unverified*: say so ("unverified — needs checking")
and do not state it as fact.

- **Registry / dispatch / wire symbols (the agenthub traps).** Several things here resolve at
  runtime, not at grep time: builtin tools register by name through `server/tools/registry.mjs` and
  are deduped/merged with custom OpenAPI ops in `server/tools/resolve.mjs`; provider adapters
  dispatch on the `provider` string inside `server/llm/llm.mjs`; the `/v1` surface re-wraps internal
  SSE events into Dify envelopes (`server/generate/dify-events.mjs`); KB `chunk_rules` are
  migrate-on-read deep-merged with defaults (`server/kb/service.mjs`). For anything sourced that
  way, the verification is *"I read the code that creates this symbol"*, not *"I grepped the name
  and didn't find it."* A missing grep hit is not evidence of absence here.
- **Score findings, gate the display.** When you report an audit/review finding, tag a confidence:
  `[severity] (confidence: N/10) file:line — description`. **9-10** = read the code and confirmed;
  **7-8** = strong pattern match; **5-6** = show it, but flag "verify this"; **3-4** = keep it out of
  the main report (appendix only); **1-2** = drop it, unless it would be data-loss or a security
  hole. Prefer zero noise over zero misses.
- **No completion claim without fresh verification.** "Done" / "fixed" / "works" requires evidence
  from THIS session: for pure logic, a green `npm test` run (this app HAS a real test runner — §4);
  for integration behavior (SSE, worker jobs, RAG end-to-end, UI), exercising the path on
  `3746/3747` and observing the result. "I re-read the code and it looks right" is not verification.
  Reject the rationalizations: *"should work now"* → run it; *"it's a trivial change"* → trivial
  changes break; *"I tested it earlier"* → the code changed since, test again. Classify each fix
  honestly: **verified** (re-ran, confirmed, no new errors) / **best-effort** (applied but couldn't
  fully confirm — say so) / **reverted** (regressed → backed out).

### 0.2 Language: Vietnamese replies, English artifacts (one exception: plan docs)
**Reply to the user in Vietnamese** (English technical terms are fine and encouraged — `release()`,
`system_id`, `chunk_rules`, `embedding_frozen`, loader/reader, agent loop, BaaS, etc. — don't
translate them). But **everything written into the repo is in English**: code, identifiers, inline
comments, schema/SQL comments, commit messages, and most doc/markdown files. The conversation is
Vietnamese; the artifacts are English.

**The one exception — plan docs are written in Vietnamese.** Pre-implementation plan documents (the
reviewed markdown plans under `.0-docs/plans/` per §0.3) are **prose written in Vietnamese**, because
they exist for the user to read and approve. Keep all technical terms, identifiers, file paths, code
snippets, API/route names, and schema/field names in English — only the explanatory prose is
Vietnamese. Everything else in the repo stays English. (The pre-existing tracked plans under
`docs/plans/` are English — they ship with the repo and follow the artifact rule; do not convert
them.)

#### 0.2.1 `.0-docs/` is local scaffolding — NEVER reference it from committed artifacts
The `.0-docs/` directory (plans, notes, this guidelines file) is **gitignored, local-only working
scaffolding** (`.gitignore` excludes it). It does not ship, and other readers — humans cloning the
repo, future LLMs, code review — **do not have it**. Therefore **no tracked/committed artifact may
reference `.0-docs/` or the planning vocabulary that lives there.** This is a hard rule.

**Forbidden in code, inline comments, JSDoc/file headers, schema/SQL comments, commit messages, PR
bodies, and any tracked `docs/` file:**
- A plan reference: `plan 0007`, `(plan 0008)`, `per the plan`, `see the plan doc`.
- A plan-internal index: `requirement #4`, `Decision #1 = b`, `§8.1 of the plan`, `Open question 3`.
- Any path into the local dir: `.0-docs/plans/0007-…md`, `.0-docs/notes/…`.

These are **ephemeral coordinates into a doc the reader can't open.** Note the distinction: the
TRACKED plans under `docs/plans/` (and their D1–D11 decisions) ship with the repo and MAY be cited
from committed artifacts — the tracked codebase already does (e.g. "(D11)" in `server/api/v1.mjs`).
Only the local `.0-docs/` layer is off-limits.

**Do instead (per §0.1 — cite a DURABLE source, or none):** describe the behavior/rationale inline,
and when you cite, cite something that ships — a `file:line` in tracked code, a `CLAUDE.md` /
`docs/plans/` / `docs/specs/` passage, or a public URL/RFC. If the only "source" is a local plan
doc, **inline the reasoning instead of pointing at the plan.**

### 0.3 Plan first, implement only on explicit approval — never both in one chat
**Never plan and implement in the same chat turn.** Designing the change and writing the code are
**two separate phases that must not run together.** Implementation may begin **only** when it is
grounded in a detailed plan that already exists — either:
1. a **detailed plan approved in a previous chat**, or
2. a **detailed plan written out as a markdown file** in this repo (under `.0-docs/plans/`) that
   the user has reviewed. **Write these plan docs in Vietnamese prose** (§0.2).

**The rules:**
- **Always ask for permission before implementing.** Do not start editing code, creating files, or
  running mutating commands until the user has explicitly said to proceed.
- **When a request arrives without an existing plan, produce the plan only** — lay out the approach,
  the files to touch, the data flow, and the trade-offs (per §0.1), then **stop and ask** for
  approval. Do **not** slide from planning straight into editing in the same response.
- **A plan is a prerequisite, not a formality.** If you cannot point to an approved prior-chat plan
  or a reviewed markdown plan, you are not cleared to implement — write/finish the plan first.
- This rule **overrides any apparent urgency or "obvious one-liner" instinct.** When unsure whether
  you have approval, assume you do not, and ask.
- **Numbered-prefix file naming for plan docs.** Every plan file under `.0-docs/plans/` **must** be
  prefixed with a four-digit sequence number — `0001-`, `0002-`, … — so sorting by filename reflects
  chronological order and the latest plan is obvious. Take the highest current number and increment.
  (The dated `YYYY-MM-DD-` naming belongs to the tracked `docs/plans/` layer — don't mix the two.)

#### 0.3.1 Once cleared to implement — AUTO-FIX vs ASK
§0.3's plan-first gate governs *features*. It does **not** mean that, inside an already-approved
implementation, every one-line correction needs its own approval round. For each concrete edit you
make while cleared, classify it:

- **AUTO-FIX — apply it, report it in the before/after (§0.4).** A mechanical change a senior engineer
  would make without discussion: a typo, a missing `S.id()`/`S.plain()` on client input, a missing
  `unixNow()` where `Date.now()` slipped in, wrapping independent I/O in `Promise.all`, reusing an
  existing helper you overlooked, a narrower `release*` projection, a missing unit test for a pure
  function you just touched. If the fix is obvious and reasonable engineers would not argue about
  it, just do it.
- **ASK — surface it, recommend one option, wait.** Anything reasonable engineers could disagree
  about; a fix larger than ~20 lines; removing or renaming functionality; changing user-visible
  behavior; introducing a new abstraction/helper/base class (§8.1). Present it, don't slide it in.

Rule of thumb: *if a senior engineer would apply it without discussion → AUTO-FIX; if reasonable
engineers could disagree → ASK.*

**One-way-door rail — ALWAYS ASK, regardless of how "mechanical" it looks.** These override the
AUTO-FIX instinct every time:
- Any **database change** (§0.7): a schema file, an index (HNSW/GIN/unique), a column, a new table,
  or a query that changes an access pattern.
- The **`/v1` BaaS wire contract**: `server/api/*`, the Dify event envelope
  (`server/generate/dify-events.mjs`), the flat error shape, the bearer format. External clients
  depend on it — a "cleanup" here is a breaking change for someone you can't see.
- **Crypto / credentials seams**: `server/provider/crypto.mjs`, anything that widens where
  `decryptObject` is called, any projection that could leak a secret, the api-token hash flow.
- **ACL / tenant scoping**: `viewable`/`managedBy` predicates, `isAppAdmin` gates, anything touching
  `system_id` or the 404-not-403 visibility rule (§5, §6).
- **RAG invariants**: `EMBED_DIMENSIONS`, the `embedding_frozen` freeze, the `run_token` claim
  protocol, economy-mode semantics, `unaccent` placement (§3, §0.7).
- **SSRF policy**: `server/utils/url-safety.mjs` and every call site that fetches an outbound URL.
- **Lifecycle / destructive**: the cleanup cascade (`server/kb/cleanup.mjs`), archive/status
  transitions, hard deletes.

A change in this list is never "just mechanical" — it is a checkpoint even inside an approved plan.

### 0.4 Explain every change — before vs after
After each implementation batch, **provide a concise before-vs-after summary** of what changed and
why — before moving on or asking for input.

- **Before:** the prior state — what the code did (or didn't), the shape it had, the gap.
- **After:** the new state — what it does now, what was added/removed/renamed. Reference `file:line`.
- **Why:** the rationale — the bug it fixes, the feature it enables, the convention it follows. Cite
  the authority per §0.1 when non-obvious.

Keep it terse; scale it to the size of the change. Applies after every edit that changes runtime
behavior — not after pure exploration.

### 0.5 Keep the docs in sync — check after every implementation, notify, ask before applying
The docs are only worth trusting if they stay current. **After every implementation**, **re-check the
documents the change touches** and surface any drift — **do not silently edit the docs, and do not
silently skip them.**

**The flow:**
1. **Check.** Review the docs that describe the area you changed — primarily [CLAUDE.md](../CLAUDE.md)
   (the ground rules, ports, DB, scripts) and [`docs/plans/README.md`](../docs/plans/README.md) (the
   plan index and its status lines), but also the relevant `docs/specs/` file,
   [reference/database-erd.mmd](./reference/database-erd.mmd), and this file. Ask: does the change
   make any documented statement wrong, incomplete, or outdated?
2. **Notify.** If something needs updating, **tell the user** — name the file, quote the stale line,
   and state the precise edit you propose (before → after). If nothing needs updating, say so in one
   line so the user knows the check happened.
3. **Ask for permission.** **Do not apply doc edits until the user approves them.** Documentation
   updates are a separate, explicitly-authorized step — propose, then wait for the go-ahead.

**Why:** stale docs actively mislead the next reader (human or LLM), and this repo's whole
convention-first doctrine depends on the canon being accurate.

### 0.6 UI navigation notice — tell the user where to find the change in the app
After every implementation batch that touches **frontend code** (`src/`, platform frontend
components, or anything rendered in the browser), include a **UI navigation note** in the close-out.

1. **Identify the user-facing surface.** Trace the change to the React component / route that renders
   it. If the change is backend-only, skip and say so in one line.
2. **Describe the navigation path.** State the route (e.g. `/apps/:appId` → the Orchestrate tab),
   the UI element (button, dialog, drawer, tab), and any prerequisite state (a configured provider,
   an indexed document, a published config).
3. **Keep it actionable.** One or two lines — enough to open the app and see the change.

**Example:**
> **UI navigation:** Open an agent → `/apps/:appId` → Orchestrate tab → "Tools" section → the new
> tool-config drawer (`src/pages/app/OrchestrateTab.jsx`) opens from the ⚙ icon on a tool row.

The routes live in [`src/App.jsx`](../src/App.jsx); the shell is
[`src/layouts/AppLayout.jsx`](../src/layouts/AppLayout.jsx). Route map: `/` (Home), `/apps`,
`/apps/:appId` (tabs `orchestrate`/`annotations`/`logs`/`api`/`usage`/`settings`; index → `orchestrate`), `/apps/:appId/chat`
(standalone chat window), `/knowledge`, `/knowledge/new` (3-step wizard), `/knowledge/:kbId`
(tabs `documents`/`hit-testing`/`logs`/`settings`), `/knowledge/:kbId/documents/:docId` (document detail),
`/settings` → `providers`/`tools`/`connectors`.

### 0.7 Database changes — verify indexes, flag non-obvious concerns, ask before proceeding
The database is the most sensitive layer. In this app, most feature growth is **NOT `ALTER TABLE`**
— app/KB settings ride the service row's JSONB `config`/`data` (CLAUDE.md ground rule #1), config
sections ride `app_configs`' JSONB columns, and per-turn state rides `conversations`/`messages`
JSONB. That makes the *few* real DB changes (a new column, a new index, a new table, a query that
changes an access pattern) all the more worth scrutinizing.

**The rules:**
1. **Check indexes for every query path.** Before writing or modifying a query, trace the columns it
   filters / sorts on and verify a matching index exists in `database/schemas/schema-<table>.sql`.
   The load-bearing ones today: `idx_chunks_hnsw` (pgvector cosine, HNSW) + `idx_chunks_tsv` (GIN on
   the stored tsvector) + `idx_chunks_doc (document_id, position)` + `idx_chunks_kb (kb_id, enabled,
   status)`; `idx_documents_kb (kb_id, status, created_at)`; `idx_messages_conv (conversation_id,
   created_at)` + `idx_messages_app (system_id, app_id, created_at DESC)`;
   `idx_conversations_app (app_id, updated_at DESC)`; `idx_annotations_hnsw` + `idx_annotations_app`;
   the unique `idx_end_users_app_ext (app_id, external_id)`; `idx_usage_daily_sys`. If no index
   covers the query, **stop and notify the user** — propose the exact `CREATE INDEX IF NOT EXISTS`
   and wait for approval.
2. **Flag non-obvious DB concerns — even outside your immediate change.** Notify the user explicitly
   about (non-exhaustive):
   - **Vector-leg blindness:** `vectorSearch` filters `embedding IS NOT NULL` — economy chunks are
     served by the keyword leg only. A feature that assumes every chunk has a vector is wrong by
     design (`server/kb/indexer.mjs` header comment).
   - **`unaccent` volatility:** it is applied at write time (`content_tsv`) and query time only —
     **never** put it in an index expression (`database/schemas/schema-chunks.sql`).
   - **HNSW recall vs filter:** the HNSW index serves cosine ordering; heavy additional `WHERE`
     filtering on top of a vector query changes its effectiveness — surface it.
   - `LOWER()`/`LIKE '%…'` leading-wildcard, `OR` across unindexed columns, functions on indexed
     columns in `WHERE`; potential sequential scans on `chunks` and `messages` (the two hot,
     unbounded tables).
   - Stale denormalizations: `usage_daily` counters and `documents.word_count/chunk_count/
     token_count` are write-maintained; a new write path that skips them silently under-counts.
   State the concern, the affected query/table, and the proposed direction. **Wait for the user's
   direction before proceeding.**
3. **DB changes require explicit permission — stricter than §0.3.** Any change that touches the
   database — a schema file, a new index, a column addition, a new table, or a query change that
   alters an access pattern — must be surfaced with a clear summary and **may not be applied without
   explicit approval.** Even within an approved plan, each concrete DB change is a checkpoint.
   > **Note — no migration runner in this app.** Schema files under `database/schemas/` are the
   > desired-state declaration, applied by `npm run db:setup` (`database/setup/setup-db.mjs`), and
   > lean on idempotent `CREATE TABLE IF NOT EXISTS` / `ALTER TABLE ADD COLUMN IF NOT EXISTS`
   > (several schemas already carry such idempotent adds — follow that shape).
   > `database/migrations/` exists but holds only hand-run one-off backfills (currently one:
   > `2026-07-unaccent-backfill.sql`) — there is **no `db:migrate` script**. If a change needs a
   > data backfill on an existing installed table, that's a real gap — raise it with the user and
   > propose a one-off migration file rather than appending destructive logic to a schema file.
4. **State the trade-off for every DB decision** (§0.1 applied to the DB): JSONB key vs new column,
   denorm vs compute-on-read, HNSW vs exact scan, write-time vs read-time derivation. Surface what
   you rejected and why, not just the chosen path.

### 0.8 Merge-request content — from the branch diff, into a numbered file (follow the template)
When the user asks for **merge-request content from one branch into another** (e.g. "create the MR
content from `zen` to `master`"), produce a markdown file — don't just print the text into chat.

1. **Read the actual diff first — never write the MR from memory.**
   - `git log --oneline <target>..<source>` — the commits.
   - `git diff --stat <target>...<source>` — the files (**three-dot** = the true MR delta); new files
     via `git diff --diff-filter=A --name-only <target>...<source>`.
   - Open terse commits with `git show <sha>` rather than guessing from the subject.
2. **Follow the template.** Match [`.0-docs/merge_requests/template.md`](./merge_requests/template.md):
   a `## Title` (one conventional-commit line) and a `## Description` with **Summary / What's included
   / Files / Notes / How to test**. Group by feature, not by commit.
3. **Write it into a NEW numbered file under `.0-docs/merge_requests/`** — never overwrite
   `template.md`. Prefix with a four-digit sequence number (`0001-`, …) + a short slug.
4. **Language: English** (it's a published PR body) with **no `.0-docs/` references** (§0.2.1) — cite
   `file:line` / routes / tables.
5. **Accuracy over completeness.** Describe only what the diff contains. Flag any real schema/index
   change, any `/v1` wire change, and whether `npm test` passes on the source branch.

---

## 1. Convention-first — the prime rule

This codebase is internally consistent on purpose. Your job is to extend it *invisibly* — new code
should be indistinguishable from what's there. Before writing anything new, find the nearest existing
example and copy its shape.

**Three authorities, in order:**
1. **`agenthub` itself** — the closest existing domain to what you're building. The domains under
   `server/` (`provider`, `kb`, `app`, `tools`, `api`) each follow the same trio shape (model file +
   `loader.mjs` + `reader.mjs`) with thin routes in `server/{apis,api}/`. Copy the nearest neighbor.
2. **The platform + sibling apps** — the source of truth for shared patterns. Sibling apps
   (`dataset`, `request`, `meeting`, `vcall`, `project`, `home`, `workforces`) are useful precedents;
   a pattern used by two or more apps *is* a platform convention — follow it, don't invent a third
   way. **When siblings disagree, prefer the app authored by `eric`** — his apps are the canonical
   reference for this platform's conventions.
3. **The upstream fork (agentstudio / Dify) — for PRODUCT behavior only.** This app was built as a
   deliberate parity port; its plans carry numbered decisions (D1–D11) recording where we follow the
   fork and where we deliberately differ. When you add behavior to a surface that exists upstream
   (chat wire, retrieval semantics, chunk modes, tool auth), read the matching
   [`docs/plans/discovery/`](../docs/plans/discovery/) map first and match the fork's *behavior* —
   never its Python/Flask *shape* (§1.4).

### 1.1 The jsonb-vs-new-table rule (read this twice)
This app follows the platform's jsonb-first convention hard: a KB's entire configuration
(`indexing_technique`, `embedding`, `chunk_rules`, `ocr`, `retrieval`) rides the service row's
`config` JSONB; an app's mode and published pointer ride `data`; an app config's seven behavior
sections (`model`, `prompt`, `variables`, `features`, `knowledge`, `agent`, `annotation_reply`) are
JSONB columns on ONE `app_configs` row; a conversation's sticky state (`attachments`, `images`,
`inputs`) and a message's `prompt`/`usage`/`retrieval`/`agent_thoughts` are JSONB. There is **no
`apps` table, no `kbs` table, no `kb_settings` table** (CLAUDE.md ground rule #1).

> **Anti-pattern to avoid:** adding a dedicated table (or a real typed column) to store what belongs
> in a service row's `config`/`data` or an existing row's JSONB column. A whole new table — schema,
> indexes, loader — to hold a per-KB setting or a per-message artifact fights the entire design.

**Decide it like this:**
- **JSONB (default, reach for it first)** — a per-KB/app setting (→ service `config`/`data`), a new
  app-behavior knob (→ a key inside the right `app_configs` section, via `config-reader.mjs`), a
  per-message artifact (→ a `messages` JSONB column), per-conversation sticky state.
- **New table** only when the data is **independently queried/paginated/aggregated across rows, has
  its own lifecycle, or is a true reverse index.** The existing twelve app tables earn their place
  exactly this way: `chunks` (vector/keyword-searched in bulk), `app_configs` (versioned
  draft→publish lifecycle), `documents` (independently listed/paginated per KB with their own status
  machine), `messages`/`conversations` (paginated logs), `annotations` (vector-matched), `providers`
  / `tools` (sealed credentials + admin lifecycle), `api_tokens` (hash lookup), `end_users` (unique
  reverse index), `usage_daily` (tiny counter read).

When in doubt, grep for how a comparable value is stored and do that.

### 1.2 Don't fork — extend
If a platform component/helper is *almost* right, add the variant to the platform (or compose it),
don't copy it into the app and diverge. The same applies inside the app: **`server/llm/llm.mjs` is
the single gateway** onto every model provider — never call a provider's HTTP API from a route,
builtin, or worker; add the capability to the gateway (as vision parts, native document blocks, and
embeddings already were). Likewise `server/utils/url-safety.mjs` is THE outbound-fetch guard — new
outbound calls go through it, not around it.

### 1.3 Build local first, promote to platform when stable
**Consume** what the platform offers freely, but be **slow to push NEW code up into platform.** The
LLM gateway, the extract pipeline, and the SSE helpers live in `agenthub` *precisely* because they
are this app's domain, not yet settled platform primitives. Promote shared-looking code to
`platform/` only once it is (a) stable and (b) a real second consumer needs it.

### 1.4 The upstream fork — mine it for knowledge, not for shape
The product this app re-implements is **agentstudio, a trimmed Dify fork** (Flask + Celery +
Next.js). The fork's source may not exist on this machine — what ships in this repo is the mined
knowledge:
- [`docs/plans/discovery/`](../docs/plans/discovery/) — deep read-only maps of the fork's chat-agent
  loop, knowledge indexing, retrieval, tools, and file-reading pipelines, written against the actual
  fork source.
- [`docs/plans/2026-07-07-aistudio-port.md`](../docs/plans/2026-07-07-aistudio-port.md) Part A —
  what the fork actually is, and Part A.1 — the extraction behaviors ported faithfully (vision-OCR
  rules, image extraction, DOCX tables→markdown, 2.0× render scale, throttles).
- [`docs/plans/2026-07-09-aistudio-gap-parity.md`](../docs/plans/2026-07-09-aistudio-gap-parity.md)
  — the feature-by-feature gap matrix and the D6–D11 decisions.

It is a different stack, and this Node+React app supersedes it. But it carries **years of Dify's
accumulated product decisions** — wire formats external SDKs expect, chunking edge cases, agent-loop
safeguards — that the rewrite hasn't necessarily re-derived. Treat it as **orientation and
prior-art, NOT current-code authority.** When the fork and this codebase disagree about shape, this
codebase wins — but read the discovery map first so you don't throw away a subtlety the fork solved.
When you lean on a fork decision, **cite it** (the discovery-doc section or the plan's D-number) and
say *why* it still applies.

### 1.5 pipeshub-ai — the primary UI/UX reference (experience, not implementation)
For **UI/UX design work going forward** — screen layouts, user flows, interaction patterns, the
overall feel of a surface — the primary inspiration source is **PipesHub**, vendored locally at
[`.0-repos/pipeshub-ai/`](../.0-repos/pipeshub-ai/) (an open-source "Workplace AI / enterprise
context layer" platform: Next.js + Radix UI Themes frontend). This is an owner decision: when
designing a **new or reworked UI surface**, look at how pipeshub-ai solves the equivalent
experience *before* inventing a flow.

**The division of labor between the three external references is strict:**

| Reference | Authority over | Never authority over |
|---|---|---|
| **Dify fork** (§1.4, via `docs/plans/discovery/`) | Product behavior & wire contracts (`/v1` compat, chunking, agent-loop semantics) | UI look & feel, code shape |
| **pipeshub-ai** (this section) | **UX & flow design**: screen composition, navigation, interaction patterns, empty/loading/error experiences | Styling implementation, tech stack, wire contracts, backend shape |
| **Platform** (`framework-ai/` → CLAUDE.md → code) | **All implementation**: components, CSS tokens, stack, conventions | — (it always wins on *how*) |

**What to take from pipeshub-ai (the UX layer):**
- **Flow & screen design** — how a feature is composed into pages, panels, and steps: the
  `app/(main)/` route surfaces (`chat`, `agents`, `knowledge-base`, `connectors`, `workspace`,
  `record`) are the closest product analogues to agenthub's apps/KB/tools/settings surfaces.
- **Interaction patterns, documented** — pipeshub ships unusually good UX docs under
  `frontend/docs/`: `url-driven-panel-state.md` (panel/dialog state in URL query params —
  shareable + reload-safe), `dropdown-pill-behaviors.md` (pill/chip input keyboard behaviors),
  `component-usage.md`, `state-and-data.md`, `style-guide.md`, and `features/` (chat message
  actions, multi-streaming chats, KB sidebar architecture, URL filter persistence). Read the doc
  before reverse-engineering the `.tsx`.
- **Captured screens** — `.0-docs/.tmp/pipehubs-ai-*.html` are DOM captures of live pipeshub
  screens; the user may drop more of these as concrete "make it feel like this" references
  (non-exhaustive — the repo itself is the fuller source).
- The other repos under `.0-repos/` (dify, FastGPT, ragflow) are **secondary** look-around
  references — primarily for **product behavior & RAG internals** (parsing, chunking, retrieval),
  not UX; pipeshub-ai is *the* primary UX one. (These four — dify, FastGPT, pipeshub-ai, ragflow —
  are the only repos currently vendored; earlier look-arounds like anything-llm, LibreChat,
  SurfSense, haystack, and llama_index have been removed.)

**What NOT to take — translate, never transplant.** pipeshub's stack is Next.js App Router,
Radix UI Themes (custom emerald/olive scales, Manrope, Material Icons), Zustand, SWR, axios.
**None of that crosses over.** Styling and implementation remain 100% platform convention (§2):
platform components (`PageLayout`, `Dialog`, `SidePeek`, `FormField`, …), platform CSS tokens
(`--color-*`, never overridden — CLAUDE.md ground rule #8), Tailwind 4, `lucide-react`, React
Context + `useState` (no zustand/React Query), `src/services/api.js`/`stream.js`. Porting a
pipeshub pattern means **re-expressing the experience in platform vocabulary**: a Radix
`<Flex>`-composed panel becomes a platform `SidePeek`/`PageLayout.Sidebar`; a Radix accent token
becomes the nearest platform `--color-*` token; a Material icon becomes its `lucide-react`
equivalent; a page-local Zustand store becomes page `useState`/Outlet context (§2.1). If a
pipeshub interaction genuinely needs a component the platform lacks, that's a §0.3 decision to
surface — not a license to import pipeshub's.

**Citing it:** `.0-repos/` is gitignored, exactly like `.0-docs/` — so per §0.2.1, **no tracked
artifact (code, comments, commits, `docs/`) may reference `pipeshub`, `.0-repos/…` paths, or its
doc files.** In committed code, describe the behavior itself ("panel open-state persisted in URL
query params so links are shareable") instead of naming the source. Inside `.0-docs/` plan docs
(local-only), cite pipeshub freely and precisely — `frontend/docs/url-driven-panel-state.md`,
a route path, or a captured HTML — so the user can verify the reference.

---

## 2. Platform-first — use what exists

The platform (`platform/` → `../platform`, a symlink; imported via `#platform/*`) is the shared,
tested foundation. Reach for it before building.

- **Frontend:** check `platform/frontend/` first — `MasterLayout`/`MasterMenu` (the shell),
  `PageLayout` (`.Content/.Header/.HeaderTabs/.Body/.Sidebar`, plus **`.SearchInput`** for a search
  box, the **`.SubHeader`** family — `.SubHeader/.SubHeaderGroup/.SubHeaderDivider/.SubHeaderMeta/
  .SubHeaderButton` — for a filter/scope strip, and **`.ToggleGroup/.ToggleSegment`** for a view
  toggle), `Dialog` (+`.Form/.Body/.Footer`), `ConfirmDialog`, `SidePeek` (+`.Section`), `Toast`,
  `EmptyState`, the `form/FormField` family (`FormField`, `Input`, `Select`, `Toggle`, `Checkbox`,
  `Textarea`, `FormRow`), `SegmentedButton`, `Pagination`. Use platform button classes (`btn`,
  `btn-primary`, `btn-secondary`, `btn-icon`) and `form-input` — not hand-rolled controls. Icons are
  `lucide-react` (pinned via `pinDeps`). (UX/flow *design* for new surfaces draws on pipeshub-ai —
  §1.5 — but the *implementation* is always these platform components and tokens.)
  **Never hand-roll a control the platform already ships** — a search box (a `<div>`+`<svg>`+`<input
  class="form-input">` is a re-invention of `PageLayout.SearchInput`), a sub-toolbar / tab-and-view
  strip (`PageLayout.SubHeader` + `PageLayout.HeaderTabs` + `SegmentedButton`, the way `meeting`
  composes its page subheader), a segmented toggle, a pager. **Grep
  [`platform/frontend/layout/PageLayout.jsx`](../platform/frontend/layout/PageLayout.jsx) and
  `platform/frontend/components/` before building any page chrome** — the piece almost always
  exists, and reproducing its markup inline is the exact "reinvent the wheel" anti-pattern (§0.3
  "look before building").
- **Styling:** platform CSS tokens (`--color-*`, `--radius-*`, `--shadow-*`) on top of **Tailwind 4**
  (`@tailwindcss/vite`, no config file). **Never override platform tokens** (CLAUDE.md ground rule
  #8; declared at `src/index.css:36`). All styling flows through [`src/index.css`](../src/index.css)
  — platform token/base imports first, then only additive app CSS (keyframes, `.typing-dots`, the
  `.chat-markdown` typography scope). Component styling goes in a **co-located `.css` file** imported
  once from `src/index.css`, using **platform-token-only classes** with a short feature prefix — the
  platform convention as practised by `dataset` (`src/components/ai/copilot.css` → `.ai-cp-*`,
  imported at `dataset/src/index.css:2`) and applied here in `src/modules/provider/providers.css`
  (`.am-*`). Keep inline `style={{}}` for **runtime-dynamic values only** (a computed width, a
  per-item color); everything static belongs in the class. Media queries, `:hover`/`:focus`/
  `:disabled` states, and keyframes live in that `.css` file — inline cannot express them. Don't
  introduce CSS modules or styled-components. Dark mode is `[data-theme]` upstream. *(The repo-wide
  inline-style audit is DONE — every `src/` surface now follows the co-located-CSS convention above;
  the ~39 remaining inline `style={{}}` are all legitimately runtime-dynamic or forced by a platform
  component that exposes only a `style` prop — `FormField`/`Input`/`Textarea` take no `className`, so
  a `flex:1`/reset there stays inline. **A ratchet guard enforces this: `npm run lint:style`**
  (`scripts/check-inline-style.mjs`) fails CI if the inline count exceeds its baseline — lower the
  baseline, never raise it. Cross-surface recurring recipes live in `src/styles/shared.css`
  (`.sh-hint`/`.sh-textarea`/`.sh-empty`/`.sh-mono`/`.sh-stack`/`.sh-contents`); the shared doc-status
  palette + labels live in `src/modules/kb/doc-status.mjs`.)*
  - **Class-prefix naming (all CSS is global — collisions are real).** Every co-located feature
    `.css` file namespaces its classes with a **short, lowercase, kebab-case prefix that abbreviates
    the feature/domain**, and that prefix **must be unique across the whole cascade** — the imported
    platform styles *and* every app feature file share one flat namespace (there is no CSS-module
    scoping). Pick it like this: (1) abbreviate the feature name — the Settings → **AI Models**
    surface is `am-` (`.am-card`, `.am-tab`, `.am-grid`); a hypothetical Action Manager would want a
    *different* prefix precisely because `am-` is taken. (2) **Before choosing, grep the taken
    prefixes** — `grep -rhoE '\.[a-z]{2,4}-' platform/frontend/styles platform/frontend/layout
    src/index.css src/**/*.css | sort -u`. Already in use (non-exhaustive): platform `page-`, `fl-`
    (fluent-layout), `ml-`/`mm-`/`mmi-`/`mh-` (master layout/menu), `svc-`, `dlg-`, `cbtn-`, `ci-`,
    `il-`, `bm-`, `rich-`, `is-`/`has-` (state); app `chat-`, `am-`. (3) If the natural abbreviation
    collides, lengthen or re-letter it (`am-`→`aim-`, or feature-scope it `am-tab` vs a global app
    prefix) — never reuse a taken one. Modifiers use `--` BEM suffixes (`.am-chip--llm`), states use
    shared `.is-*`/`.has-*`. Record what the prefix stands for in the file's header comment.
- **Backend:** `#platform/db/db.mjs` (`DB` base + `Cond`), `#platform/db/reader.mjs` (`Reader`
  base), `#platform/db/dto.mjs` (`DTO`), `#platform/sanitize.mjs` (`S.id()`, `S.plain()`),
  `#platform/service/service.mjs` (the `Service` base both app services extend),
  `#platform/http/router.mjs`, `#platform/http/rate-limit.mjs`, `#platform/http/multipart.mjs`,
  `#platform/backend/queue.mjs` (`dispatch`/`createWorkers`), `#platform/suid.mjs`.
- **Dev mock-LLM mode (`AGENTHUB_MOCK_LLM=1 npm run dev` / `npm run dev:mock`).** For UI/UX work
  without real provider keys: the gateway's `invokeChat`/`embed` short-circuit into
  `server/llm/mock.mjs` BEFORE credential decryption and SSRF checks — every model-touching flow
  (verify, chat streaming, agent tool round, indexing→ready, hit-testing, Q&A/summary, OCR,
  auto-name) completes with deterministic fake output, and a "LLM MOCK" badge shows in the header.
  Double-gated on `config.env === 0` (prod-safe). **Hard rules:** all mock behavior lives in
  `mock.mjs` (its header is the living removal checklist); every touch point outside it carries the
  grep-able tag `[DEV-MOCK]` (`rg '\[DEV-MOCK\]'` finds all); never add a mock branch anywhere else
  — the gateway seam is the only one.
- **Imports:** always use the registered subpath aliases `#platform/*`, `#server/*` (see
  `package.json#imports`). Never `../../platform/...` from backend code.
- **Time:** DB timestamps are **Unix seconds** (`int:now` in the schema DSL). Use `unixNow()`
  helpers (defined per-file as `Math.floor(Date.now() / 1000)`), never raw `Date.now()`
  (milliseconds). `usage_daily.day` is a `yyyymmdd` UTC int.
- **No backend imports in frontend.** `vite.config.js`'s `blockBackendImports()` is a
  **security-critical, default-deny** plugin: it hard-errors if frontend code imports backend
  modules, secrets (`config.json`/`backend.json`), or non-frontend platform paths. Frontend may only
  import from `src/`, `platform/frontend/`, `platform/components/`, `platform/modules/<m>/frontend/`.
  This is exactly why `modules/kb/chunk-rules-form.mjs` re-declares backend defaults instead of
  importing them — keep pure frontend mirrors React-free and unit-tested rather than importing
  server code.

### 2.1 Frontend architecture (the landmarks)
- **API calls:** always go through [`src/services/api.js`](../src/services/api.js) — per-entity
  namespaces (`providerApi`, `kbApi`, `appApi`, `toolApi`, `annotationApi`, `documentApi`,
  `chunkApi`) wrapping the platform `post`/`upload` helpers (which keep CSRF + cookies + 401
  session-recovery consistent). Never `fetch` directly for JSON.
  **Streaming is the one exception:** [`src/services/stream.js`](../src/services/stream.js)
  `streamPost()` uses `fetch` + `ReadableStream` (NOT `EventSource` — SSE here needs POST + CSRF),
  parses `event:`/`data:` frames manually, and returns an abort function. Chat
  (`/api/app/chat-messages`) and the provider playground consume it; completion apps POST blocking.
  > This app does **not** use TanStack React Query — data is fetched through these namespaces and
  > held in context/component state. Don't introduce a query-cache library.
- **Auth & app state:** [`src/stores/authStore.jsx`](../src/stores/authStore.jsx) is **React Context
  + useState, NOT zustand.** `AppStoreProvider` holds three slices — `providers`, `kbs`, `apps`
  (`authStore.jsx:16-21`) — filled from `/auth/me` via `storeAppData()`. The `platformAppStores()`
  Vite plugin aliases platform store imports onto this file so platform + app share one context.
  Per-page/tab data (messages, documents, tokens, annotations) is local `useState` in the page,
  passed to tabs via router `Outlet` context.
- **The three component layers:** `src/pages/` (route-bound, own data loading), `src/modules/`
  (**context-free feature units** — dialogs/panels/forms that receive everything via props:
  `app/chat-box.jsx`, `kb/chunk-browser.jsx`, `provider/form.jsx`, …), `src/components/`
  (app-local primitives: `Markdown`, `KebabMenu`, `ChipInput`, `Spinner`). New UI slots into this
  split — a reusable panel goes in `modules/`, not `pages/`.
- **Markdown:** [`src/components/Markdown.jsx`](../src/components/Markdown.jsx) — `marked` +
  DOMPurify with a strict policy (no `style/iframe/form/input/button`; links forced
  `target=_blank rel=noopener`), rendered per SSE delta and tolerant of half-written markdown.
  Never render model output through anything else.
- **i18n:** platform `t()`/`tp()` from `platform/frontend/i18n/t`. Source strings ARE the English.
  **Never `t()` a runtime value** — declare a static label map with `t()` on the literals and look
  up by key (the pattern in `src/pages/kb/DocumentsTab.jsx` and siblings). Catalogs compile via
  `npm run i18n:build` to `public/i18n/`.
- **Routing & layout:** `react-router-dom` v7; entry [`src/main.jsx`](../src/main.jsx); routes +
  OAuth-callback handling in [`src/App.jsx`](../src/App.jsx); shell
  [`src/layouts/AppLayout.jsx`](../src/layouts/AppLayout.jsx) (platform `MasterLayout`). Route map
  in §0.6. Dirty-state guards use `useBlocker` + `beforeunload` (see `OrchestrateTab.jsx`) — reuse
  that pattern for new editors.

---

## 3. The domain shape (agenthub's backend layout)

**There is no `modules/` directory and there are no listeners.** Each domain lives under
`server/<domain>/` and co-locates its model, loader, and reader. Side effects are **best-effort
inline** (try/catch-swallowed so they never fail the primary write) — e.g. `bumpUsage()` after a
persisted message, the ≤1/min api-token `touchToken`. Heavy async work is a **queue job** (ground
rule #9). Don't introduce an event bus, an entity-listener layer, or a cron framework.

| Piece | Responsibility | Must not |
|---|---|---|
| `server/<domain>/<entity>.mjs` | The model. `class X extends DB` (or `extends Service` for the two services). Schema DSL, domain accessors over JSONB, `release()`/`releaseHeader()`, ACL predicates (`viewable`/`managedBy`). | Hold query functions or route logic. |
| `server/<domain>/loader.mjs` | Pure async reads (`getXById`, `listX`) — tenant-scoped, returning hydrated instances. | Mutate; contain HTTP. |
| `server/<domain>/reader.mjs` | `forCreate()`/`forEdit(id)` → a `Reader` subclass: `read(body, user)` → `validate()` → `save()`. Owns input sanitization (DTO, `S.*`, clamps, caps). | Be bypassed — routes never write the DB directly. |
| `server/apis/<resource>.mjs` | Console routes (`/api/<resource>/<action>`, mostly POST, session + CSRF). Thin transport: parse `ctx.body()` → `S.id()` → loader/reader → ACL → return `release()`. | Contain SQL, state machines, or provider calls. |
| `server/api/*` | The `/v1/*` BaaS surface: bearer guard, token/end-user models, Dify-wire routes, usage counters. | Leak the console error shape (`ctx.error`) — use `v1Error()`. |

**The agenthub-specific subsystems** (most sibling apps don't have these — read the matching
discovery map before touching them):
- **`server/llm/`** — THE model gateway: `llm.mjs` (`invokeChat`/`embed`; decrypts credentials,
  SSRF-checks base URLs, dispatches by provider), `anthropic.mjs` / `openai-compatible.mjs`
  (adapters), `parts.mjs` (multimodal/native-document routing), `sse.mjs`.
- **`server/extract/`** — file → source pages: `extract.mjs` dispatches by extension
  (`SUPPORTED_EXTENSIONS`), `pdf/docx/excel/csv/html/text.mjs`, `ocr.mjs` (vision-LLM OCR),
  `images.mjs`, `clean.mjs`, `structured.mjs`, `splitter.mjs` (the structure-aware splitter —
  character budgets + small-piece merging, markdown-heading sections with title inheritance,
  atomic tables/code fences; `SPLITTER_VERSION = 3`), `turndown.mjs` (shared HTML→GFM-markdown
  converter used by both docx and html extractors).
- **`server/kb/`** — the RAG domain: `indexer.mjs` (the worker pipeline: claim → extract → chunk →
  embed → insert → ready, all writes guarded by `extract.run_token`), `docstore.mjs` (filedb binary
  I/O), `qa.mjs`/`summary.mjs` (LLM-generated Q&A / summary indexes), `cleanup.mjs` (cascade job),
  `recovery.mjs` (stuck-doc sweep, startup + every 10 min), `webimport.mjs` (BFS crawl job).
- **`server/retrieval/retrieval.mjs`** — hybrid retrieval: pgvector cosine leg + tsvector keyword
  leg (`unaccent`ed), merged to `[0,1]` with weights (default `{vector: 0.7, keyword: 0.3}`,
  precedence app-override → KB-stored → default), modes `vector|keyword|hybrid`.
- **`server/generate/`** — the generation runtime: `pipeline.mjs` (chat/completion),
  `agent-runner.mjs` (the tool loop: ≤ `max_iterations`, thoughts persisted to
  `messages.agent_thoughts`, repeat-round breaker, guaranteed non-empty answer), `prompt.mjs`
  (message building, `{{var}}` resolution, the static/dynamic system split with the
  cacheable prefix, the `<context>` fence), `guard.mjs` (untrusted fencing + name
  guarding), `lang.mjs` (reply-language pin), `persona.mjs` (always-on meta persona),
  `contexts.mjs` (@-mention chips + memory sanitize), `actions.mjs` ("/" action specs),
  `history-summary.mjs` (rolling summary → conversations `data.summary`), `errors.mjs`
  (console error taxonomy), `annotation.mjs` (annotation-reply short-circuit),
  `attachments.mjs`/`images.mjs` (sticky, budget-capped), `auto-name.mjs`,
  `suggest.mjs` (follow-ups + the "Suggest" one-shot), `dify-events.mjs` (the `/v1` envelope).
- **`server/tools/`** — `registry.mjs` + `builtin/` (8 builtins), `openapi.mjs` (import + exec),
  `resolve.mjs`: defs↔executors kept strictly 1:1 by name (first registration wins, later
  collisions dropped from BOTH), and **form-preset stripping** — admin-locked params are removed
  from the schema the model sees and injected preset-wins at execute time.
- **`server/helpers/`** — `sse-route.mjs` (`openStream()`: heartbeat every 15 s, emits dropped
  after client close but generation still persists), `stop-flag.mjs` (task stop registry —
  only the task owner may stop), `files.mjs`.
- **Workers** — `worker.mjs` registers `agenthub-index-document` ×3, `agenthub-cleanup` ×1,
  `agenthub-import-web` ×1 via `createWorkers()`; producers call `dispatch(name, payload)`.

**Routes are thin transport.** A handler does: parse `ctx.body()` → `S.id()` client ids →
load/validate via loader/reader → ACL (404 if `!viewable`, 403 if `!managedBy`) → do the one
domain call → return `entity.release()`. Use `ctx`: `ctx.user`, `ctx.body()`, `ctx.json(data)`,
`ctx.error(msg, status)` (console only). SSE routes go through `openStream()`.

---

## 4. Data model, schema & tests

- **Type DSL** in the model's `static schema` is the platform `DB` convention: `'suid:pkey'`,
  `'varchar'`, `'text'`, `'int:0'`, `'int:1'`, `'int:now'`, `'jsonb:{}'`, `'jsonb:[]'`. Copy the
  shape from an existing model (`server/provider/provider.mjs` is a clean example).
- **PKs are SUIDs** (`VARCHAR(31)`, generated in Node via `#platform/suid.mjs`) for all app rows.
  Integer auto-increment is reserved for platform-managed `users`/`systems`. `usage_daily` has no
  model class and a composite PK `(app_id, day)` — it is written only via the sanctioned upsert in
  `server/api/usage.mjs`.
- **The twelve app tables** (`database/schemas/schema-*.sql`): `providers`, `app_configs`,
  `documents`, `chunks`, `conversations`, `messages`, `annotations`, `tools`, `api_tokens`,
  `end_users`, `usage_daily`, `kb_logs`. An **app or KB itself is a `services` row** in `standard_platform` —
  there is no `apps`/`kbs` table here (CLAUDE.md ground rule #1). Read each schema file's leading
  comment block; it's the human spec of the table.
- **Schemas are declaration-only** and **applied by `npm run db:setup`** — idempotent
  `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN IF NOT EXISTS` (the existing schemas
  model this). `database/migrations/` holds hand-run one-off backfills only; there is no
  `db:migrate` (§0.7 note).
- **pgvector is a hard dependency** — `db:setup` runs `CREATE EXTENSION IF NOT EXISTS vector` on the
  app DB; `chunks.embedding` and `annotations.question_embedding` are `vector(1536)`.
- **No FK, no JOIN** (CLAUDE.md ground rule #5) — all SQL is single-table; relations are assembled
  in Node via batched-id reads + `Promise.all` (e.g. retrieval hydrates document names with one
  batched read). Raw SQL is sanctioned ONLY at the spots the ORM can't express (pgvector/tsvector
  writes and searches, the counter upserts) — always parameterized, table names hard-coded.
- **Tests are real here — write and run them.** `npm test` runs vitest over `tests/*.test.mjs`
  (~77 files). The convention: backend modules take a `deps` parameter for dependency injection so
  tests run offline (no DB, no network) — see `server/kb/indexer.mjs`'s injectable
  `embedBatches`/`insertChunksFn` and the tests that exercise claim/economy/qa paths. **A backend
  change with pure logic ships with a unit test**; a bugfix ships with the regression test that
  would have caught it. `vitest.config.mjs` deliberately bypasses `blockBackendImports` — don't
  "fix" that. Integration behavior (SSE, worker jobs, RAG end-to-end, UI flows) still needs a live
  check on `3746/3747`. There is no e2e suite; the manual walk lives in
  `docs/plans/2026-07-10-qa-checklist.md`.
- Throwaway DB-inspection scripts go in a gitignored temp dir, never at the repo root.

---

## 5. Multi-tenancy & the release doctrine

### 5.1 `system_id` — every row, every query
Every app table carries `system_id` (the integer tenant) and every query filters by it. Documents
and chunks are additionally scoped by `kb_id`; conversations/messages/annotations/tokens by
`app_id`. The cleanup cascade scopes **every** statement by `system_id` (+ `app_id`/`kb_id`) as
defense-in-depth (`server/kb/cleanup.mjs`). When you add a table: carry `system_id` + `user_id` +
`created_at`/`updated_at` like every neighbor, and filter every read by tenant. (Exception: pure
counter/reverse-index tables — `usage_daily`, `end_users` — may trim the audit columns; they still
carry `system_id`.)

### 5.2 `release()` vs `releaseHeader()` — and the `/v1` projection
- **`release()` is the default READ projection** for the console SPA. It returns the row minus
  private fields. **Secrets reduce to signals**: `Provider.release()` emits `configured: !!creds` +
  the last-4 `hint` (`server/provider/provider.mjs:31-45`); `Tool.release()` emits an auth *summary*
  (type + placement, never the key); `Document.release()` strips `file.key`. Reads always go
  through it.
- **`releaseHeader()` is the compact list/identity snapshot** (used for the `/auth/me` app/KB
  slices). Detail reads use `release()`.
- **The `/v1` surface has its OWN projections** — Dify-shaped bodies assembled in
  `server/api/v1.mjs` + `server/generate/dify-events.mjs`. Never leak an internal `release()` shape
  onto `/v1`, and never leak the Dify shape into the console.

Always return through a projection — never a raw row.

---

## 6. Security & ACL

- **404, not 403, for tenant/visibility misses.** When a row isn't found *or* the caller can't see
  it, return `404` — revealing existence is an enumeration leak. Then `403` when visible but not
  permitted to act. The standard guard: `if (!x || x.status !== 1 || !x.viewable(ctx.user)) return
  ctx.error('Not found', 404); if (!x.managedBy(ctx.user)) return ctx.error('Forbidden', 403)`.
- **Admin gates:** `providers` and `tools` are system-level shared config — `managedBy` requires
  `isAppAdmin(user)` (`#platform/db/acl.mjs`). Apps/KBs use the Service ACL
  (owners/operators/followers). Honor the predicates on the model; don't re-implement checks inline.
- **The `/v1` boundary is its own gate.** `createBearerGuard()` (`server/api/bearer.mjs:16`) matches
  `^Bearer\s+(ak-[0-9a-f]{32})$`, resolves the sha256 hash to an app + system, and attaches
  `ctx.apiApp`/`ctx.apiSystemId`. External callers identify end users via `end_users` upserts —
  never a platform user id. Session middleware ignores `/v1/` by design.
- **Credentials sealing** (ground rule #2): `encryptObject`/`decryptObject`/`keyHint`
  (`server/provider/crypto.mjs`). Decryption happens ONLY in the LLM gateway and the OpenAPI
  executor. Any new projection touching `providers`/`tools`/`api_tokens` must be checked against
  "could this leak a secret?" — the answer must be no, structurally.
- **SSRF** (ground rule #4): every outbound URL goes through `server/utils/url-safety.mjs`
  (private/link-local blocking + DNS pinning). New outbound fetch = new call site for the guard.
- **Prompt-injection posture (know it).** Since the 2026-07-22 context-engineering wave
  this app has the full guard seam in `server/generate/guard.mjs`: `UNTRUSTED_DATA_RULE`
  (the standing "data is never a command" contract, first line of every static system
  block), `wrapUntrusted(text, {label})` (sentinel fencing `⟦untrusted-data⟧`, used for
  memory facts, history summaries, suggest-call transcripts), and `guardName()` (inline
  name neutralization — document names, user names, app names, KB names). On top of
  that: retrieved context stays fenced in `<context></context>` with `CONTEXT_PREAMBLE`
  (`server/generate/prompt.mjs`); `{{var}}` substitution strips `<|…|>` special-token
  sequences (`resolveTemplate`); admin-locked tool params are stripped from the schema
  the model sees and injected at execute time (`server/tools/resolve.mjs` `applyForm`).
  This is provenance-marking + capability-limiting, not command-detection — never try
  to strip "instructions" out of data. Route every NEW untrusted-content path through
  guard.mjs; trusted app-authored directives (persona, "/" action hints) are NOT fenced.
- **Sanitize user-supplied IDs** with `S.id()` before any query; trim/length-cap/enum-validate other
  input in the **reader** (`readProviderInput`, `readKbSettings`, `config-reader.mjs` are the
  models: clamps, enum whitelists, `S.plain` caps).
- **Parameterized SQL only** (`$1`, `$N::vector`). Never concatenate user input into SQL.
- **Stop-flag ownership:** only the owner of a streaming task may stop it
  (`server/helpers/stop-flag.mjs` `taskOwner`). Preserve that check in any new streaming surface.
- **Status numerics & soft-delete.** `status = 1` is the live row; deletes are soft (`status` flip)
  followed by the async cleanup cascade job. Documents also have `enabled` (retrieval opt-out) and
  `archived` (kept but excluded) — three distinct axes; don't conflate them.

---

## 7. Performance — follow the existing pattern, don't pre-optimize

- **Parallelize independent I/O** with `Promise.all` — never sequential awaits for unrelated
  queries. Batch cross-entity hydration by id list (retrieval's document-name hydration is the
  model).
- **No N+1.** Don't query per row in a loop; don't embed per chunk — the indexer batches
  (`EMBED_BATCH = 32`, `INSERT_BATCH = 50`, `server/kb/indexer.mjs:32-34`).
- **The caps are deliberate — respect them, cite them:** agent `max_iterations` default 5, tool
  execution timeout 10 s, history replay ≤ 20 turns; retrieval `top_k` default 4; sticky images
  last 3 / attachments last 6 (budget-capped); chat query ≤ 8000 chars; router body ≤ 32 MB with
  the multipart upload's own 50 MB gate (rationale documented in `dev-server.mjs`); QA/summary
  generation concurrency 6. If a cap blocks a legitimate need, raise it as a decision — don't
  silently bump it.
- **Best-effort side effects stay best-effort.** Counters (`bumpUsage`), token touches, auto-naming
  swallow their errors so they never fail generation. Don't "harden" them into the critical path.
- **Denormalize the hot reads.** `usage_daily` exists so the dashboard never scans `messages`;
  `documents.word_count/chunk_count/token_count` are stamped at index time. Maintain them on the
  write path, never recompute per read.
- **Index by the access pattern** — HNSW for vector cosine, GIN on the *stored* tsvector column,
  composite btrees matching the list queries (§0.7 list). Add an index when you add a hot query
  path; don't speculatively index.
- **Streaming hygiene:** SSE routes send a heartbeat every 15 s and keep persisting after client
  disconnect (`server/helpers/sse-route.mjs`) — new streaming endpoints reuse `openStream()`, not a
  hand-rolled `res.write` loop.

---

## 8. SOLID & maintainability — applied with restraint

The layering already *is* SOLID: model = shape + ACL, loader = reads, reader = validation + write,
route = transport, gateway = the one provider seam, worker = async. Keep that separation and you've
satisfied single-responsibility without ceremony. Beyond that:

- **Extend, don't modify:** add a loader function / a narrower projection / a new builtin via
  `server/tools/registry.mjs` / a new extract stage via the `extract.mjs` dispatcher, rather than
  widening an existing seam.
- **Projections are the server↔client contract:** add a narrower `release*` method rather than
  leaking fields; keep `/v1` shapes in `v1.mjs`/`dify-events.mjs`.

### 8.1 Do NOT over-engineer (explicit)
Following a principle too literally is itself a defect here. Avoid:

- **A vector-store abstraction layer.** The fork has 30+ pluggable vector stores; this app
  **deliberately has exactly one pgvector path** (master plan, Part A conclusion). Don't build an
  interface for hypothetical stores.
- **A model-runtime abstraction (LiteLLM-style).** The gateway is three adapter files behind one
  `invokeChat`/`embed` seam. A new provider = a new adapter file, not a plugin framework.
- **A workflow engine.** Workflow apps are **explicitly deferred by the owner** (master plan,
  header). Don't scaffold nodes/canvas/graph-runner "for later."
- **An event bus / entity listeners / a cron framework.** The pattern is best-effort inline +
  queue jobs + the 10-minute recovery sweep. Match it.
- **A new table (or a real column) for what is a `config`/`data`/JSONB-section value** (§1.1) —
  the headline anti-pattern.
- **A chart library.** The Usage tab renders inline SVG on purpose.
- **Speculative abstractions.** No helper, HOF, or base class for a *single* use. Abstract on the
  third or fourth concrete instance.
- **Gold-plating** — unrequested fields, options, or polish that widen scope.
- **Restructuring working code** to satisfy a principle when it already matches the surrounding
  style. **Touch ONLY what the feature requires.** A diff that edits an untouched-by-the-feature
  method is churn: it inflates review surface, risks a silent behavior change, and muddies
  `git blame` for zero functional gain.

The test: *does this make the change smaller and more like the existing code, or larger and more
clever?* Prefer smaller and more like.

---

## 9. Pre-implementation checklist (agenthub-accurate)

```
[ ] Cleared to implement: an approved prior-chat plan OR a reviewed markdown plan exists, and the user gave explicit go-ahead (§0.3) — NOT planning + implementing in the same chat
[ ] Read CLAUDE.md (+ docs/plans/README.md for history, the matching discovery map for fork behavior, docs/specs for the feature wave); checked the ERD
[ ] Traced the full chain (schema → server/<domain>/{model,loader,reader} → server/{apis,api} routes → src/services/api.js|stream.js → React; async: dispatch → worker → job)
[ ] Found the nearest existing domain/route/module (provider/kb/app/tools) and am mirroring its trio shape
[ ] Is this a service config/data key or an existing JSONB section (default) — or does it truly warrant a new table/column (§1.1)?
[ ] Model traffic through server/llm/llm.mjs ONLY; outbound URLs through url-safety; credentials never decrypted outside the gateway/executor?
[ ] Frontend: platform component/token first? (no React Query; api.js for JSON, stream.js for SSE; modules/ vs pages/ vs components/ split; no token overrides; no backend imports)
[ ] New/reworked UI surface → checked pipeshub-ai for the equivalent flow/interaction (§1.5), then re-expressed it in platform vocabulary (no Radix/zustand/Material-icon transplants; no pipeshub/.0-repos references in tracked artifacts)?
[ ] /v1 change → Dify wire parity checked (dify-events envelope, v1Error flat shape) and treated as a one-way door (§0.3.1)?
[ ] New table → carries system_id (filter every query) + suid pkey, mirroring a neighbor? Justified by independent query/lifecycle, not a JSONB value?
[ ] Schema change → idempotent CREATE/ALTER IF NOT EXISTS applied by db:setup (no migration runner); one-off backfills as a hand-run migrations/ file, surfaced to the user?
[ ] DB query: verified every WHERE/ORDER BY column has a matching index (HNSW/GIN/btree list in §0.7); flagged any non-obvious concern (economy NULL embeddings, unaccent placement, hot-table scans) and waited for direction?
[ ] RAG invariants intact: 1536 dims, embedding_frozen, run_token claim, economy = keyword-only; indexing stays a worker job, never inline in a route?
[ ] Side effects: best-effort inline (swallowed) or a queue job — no new listener/event-bus machinery?
[ ] Route is thin: parse ctx.body() → S.id() → loader/reader → ACL (404-then-403, isAppAdmin where required) → release(); no SQL/provider calls in the route?
[ ] Each in-flight edit classified AUTO-FIX vs ASK; anything touching DB / v1 wire / crypto / ACL / RAG invariants / SSRF / destructive-lifecycle went to ASK regardless (§0.3.1)
[ ] User IDs run through S.id(); other input trimmed/typed/clamped in the reader?
[ ] Independent queries Promise.all'd? Batched, capped (§7)? Hot read uses a denorm (usage_daily, doc counters), not a scan?
[ ] Timestamps via unixNow()/'int:now', not Date.now()? status/enabled/archived axes respected?
[ ] Imports via #platform/#server aliases? No backend import from frontend (blockBackendImports)?
[ ] Pure-logic change ships with a vitest unit test (deps-injected, offline) and `npm test` is green; integration behavior exercised live on 3746/3747 (§4, §0.1.1)
[ ] Smallest correct change — no vector-store/model-runtime/workflow/event-bus abstraction, no speculative generality, no refactoring of working code the feature doesn't touch (§8.1)?
[ ] Non-obvious decision documented with its why + a citation (convention / fork-behavior via discovery map / URL / principle)?
[ ] Load-bearing claims about the code quote a file:line (or are marked unverified); findings carry a confidence score (§0.1.1)
[ ] Provided a before-vs-after summary of what changed and why (§0.4)?
[ ] Re-checked the docs the change touches (CLAUDE.md / docs/plans/README.md / specs / ERD), notified the user of any drift, and asked before applying doc edits (§0.5)?
[ ] Frontend change → included a UI navigation note (route, tab, dialog, interaction path) (§0.6)?
```

---

## 10. Where conventions live / reference apps

| Source | Use for |
|---|---|
| [`framework-ai/`](../framework-ai/) (`../framework-ai`) | The platform-wide convention canon shared by every app — transport, release doctrine, the service model, `sanitize`, OAuth, DB. Sits ABOVE CLAUDE.md. Symlinked at root via `npm run link:docs` |
| [CLAUDE.md](../CLAUDE.md) | The live convention canon — the 9 absolute ground rules, ports, DB, scripts, testing doctrine |
| [`docs/plans/README.md`](../docs/plans/README.md) | The plan index — master port plan, phase plans, QA audits, decision history D1–D11 |
| [`docs/plans/discovery/`](../docs/plans/discovery/) | Deep-maps of the upstream fork (Dify) — product-behavior prior art to mine (§1.4); orientation, not current-code authority |
| [`.0-repos/pipeshub-ai/`](../.0-repos/pipeshub-ai/) | **The primary UI/UX reference** (§1.5) — flows, screen layouts, interaction patterns; its `frontend/docs/` + `app/(main)/` routes + the `.0-docs/.tmp/` captures. Experience only — implementation stays platform. Gitignored: never cite from tracked artifacts |
| [`docs/specs/`](../docs/specs/) | Design specs for the chunk-settings / economy / QA-chunk / structured-doc / summary-index wave |
| `database/schemas/*.sql` | The desired-state shape of every table + its indexes (read the comment block); applied by `db:setup` |
| [reference/database-erd.mmd](./reference/database-erd.mmd) | The full data model — entities, columns, logical relationships at a glance |
| [reference/llm-app-platform-foundations.md](./reference/llm-app-platform-foundations.md) | Domain orientation — LLM-app-platform vocabulary (app modes, indexing techniques, chunk/retrieval modes, annotation reply, BaaS) so you build at the right altitude |
| `server/*` | The nearest working example of the pattern you're building |
| `platform/` (`../platform`) | Source of truth for shared components, tokens, DB/Reader/Service base, router, sanitize, queue |
| `request` / `meeting` / `dataset` / `project` / `home` / `hris` / `creator` / `career` | Sibling apps — a pattern shared by ≥2 is a platform convention. Prefer apps authored by `eric` when siblings disagree |
| `tests/*.test.mjs` | The testing conventions — deps-injection, offline fixtures, route-level tests |

When a pattern exists in two or more places, it's the convention. Implement new work to match it — not
a different, "better" way.
