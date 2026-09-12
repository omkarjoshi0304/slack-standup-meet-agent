# TASKS.md — Work Breakdown (Team of 3)

Small, assignable tasks grouped by epic. IDs like `A1`, `B2`, `C3`.
Owners: **A = Slack surface (CopilotKit Channels, Node)**, **B = Agent core (LangGraph, Python)**,
**C = Integrations & data (Python)**.

Architecture is **hybrid**: CopilotKit Channels (Node) ⇄ AG-UI ⇄ Python LangGraph agent.
See `AGENTS.md`. Do the **Foundation** epic together first, then work in parallel against
the frozen interfaces. Stub-first: build against fake data, swap real clients in later.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · **(dep: …)** = depends on.

---

## Epic 0 — Foundation (shared, hour 0–1)

- [x] **F1** `channels/` scaffolded (trimmed from the starter kit's `apps/channel` pattern —
  `env.ts`, `agent.ts` with an `HttpAgent` pointed at `AGENT_URL`, `channel.ts`
  (`onMention`/`onMessage`, no cards yet), `server.ts`). `npm install`, `npm test`, and
  `tsc --noEmit` all pass. Boot-tested with placeholder credentials: fails cleanly at the
  real-credential boundary (`ChannelConfigError` on the CopilotKit API key format), as
  expected. **Remaining (manual, needs a human):** sign up for CopilotKit Intelligence,
  create the Slack app, run `copilotkit channels add`, and confirm a live mention reply in
  Slack — see `channels/README.md`. — *A*
- [x] **F2** `agent/` scaffolded: `graph.py` (echo `MessagesState` graph with a `MemorySaver`
  checkpointer — AG-UI needs one for per-thread state) and `main.py` (FastAPI +
  `LangGraphAgent` + `add_langgraph_fastapi_endpoint` mounted at `/agent`). Verified for
  real: unit test passes (`tests/test_graph.py`) and a live AG-UI `RunAgentInput` POST to
  `/agent` returns a correct SSE stream ending in `MESSAGES_SNAPSHOT` →
  `"echo: hello"` → `RUN_FINISHED`. End-to-end Slack → Channels → this agent still needs F1's
  manual credentialing step to observe in Slack itself. — *B*
- [x] **F3** `core/config.py` + `.env.example`: all env vars (Channels/Slack tokens, Auth0,
  Jira base URL, Google creds, OpenAI key, `AGENT_URL`). — *C*
- [x] **F4** `core/models.py` + `core/db.py`: SQLModel entities (Workspace, User,
  StandupConfig, StandupRun, MeetingRequest) + SQLite engine/session. — *C*
- [x] **F5** Freeze the shared interfaces below as stubs so A/B/C don't block each other. — *all*

### Shared interfaces (freeze these in hour 1)
```python
# integrations/auth0_vault.py
def get_token(user: User, provider: Literal["jira","google"]) -> str: ...

# integrations/jira_client.py
def get_sprint_issues(user: User) -> list[Issue]: ...

# integrations/google_calendar.py
def get_freebusy(user: User, window: Window) -> list[BusyInterval]: ...
def create_event(organizer: User, attendees: list[User], slot: Slot) -> EventResult: ...

# integrations/slack_web.py
def post_message(channel_id: str, blocks: list) -> str: ...   # returns message_ts

# agent/slots.py
def best_common_slot(busy: dict[UserId, list[BusyInterval]],
                     window: Window, duration_min: int, tz_by_user) -> Slot | None: ...

# LangGraph tools (agent/tools.py) wrap the above and are bound to the graph.
```
The **card contract** (A↔B): the agent returns a typed payload; Channels renders it via
`defineChannelComponent`. Agree on the fields for `standup_digest` and `meeting_confirmation`.

---

## Epic A — Slack surface / CopilotKit Channels (Person A, Node)

- [~] **A1** Provision the Channel — dashboard-first flow used (see `channels/README.md`).
  Channel `mytro` created, Slack app installed with all 17 bot scopes (verified in Slack's
  OAuth & Permissions page, including `chat:write`), Bot Token + Signing Secret set, channel
  shows **Online** in the CopilotKit dashboard. `npm run doctor` passes. Local listener boots
  and reaches `online`. AG-UI round-trip to the Python agent is proven end-to-end: the
  dashboard's **State** tab shows the agent correctly generating `"echo: hello"` for real
  Slack mentions. **Blocked:** the generated reply never appears in Slack — confirmed in two
  different channels (one Slack Connect, one plain), reply text not found via Slack search.
  CopilotKit's dashboard reports delivery `complete` regardless, so the failure is silent on
  both ends. Root cause not yet identified — likely a CopilotKit-hosted-adapter-side issue,
  since posting happens on their infrastructure, not in our listener. One bot count and single
  Channel decision locked (see `channels/README.md`). — (dep: F1)
- [ ] **A2** Wire `createChannel({ agent, components })` to our Python agent via `AGENT_URL`;
  verify `onMention` subscribes a thread and `onMessage` follows up. — (dep: F2)
- [ ] **A3** `defineChannelComponent` **standup_digest** card — per person: ✅ done /
  🟡 in-progress / ❌ blockers, with Jira links (match the target screenshot). — (dep: F5)
- [ ] **A4** `defineChannelComponent` **meeting_confirmation** card — time, attendees,
  Meet link. — (dep: F5)
- [ ] **A5** Confirm the bot only responds to `@dailyagent`/`@meetagent` mentions and stays
  silent otherwise; document the required Slack scopes. — (dep: A2)
- [ ] **A6** (stretch) Native rendering for passive meeting-intent suggestions.

---

## Epic B — Agent core / LangGraph (Person B, Python)

- [x] **B1** `agent/graph.py` rebuilt: `parse_node` (calls B2) → conditional edge to
  `daily`/`meet`/`END` (friendly reply + end on unparseable text) → lazily-built
  `create_react_agent` per branch, bound to the relevant B3 tools. Lazy so `import
  agent.graph`/`agent.main` never needs `OPENAI_API_KEY` — verified: `python -c "import
  agent.main"` succeeds with the key unset. Routing tested in `tests/test_graph.py`; the
  react-agent nodes themselves need a real key + real integrations, not exercised here.
  — (dep: F2)
- [x] **B2** `agent/parsing.py`: real `parse_mention` — single Channel/bot identity (see F1),
  so the sub-agent is the first token of the mention text, not a separate Slack app. Handles
  `dailyagent {run now, set schedule, pause, resume}` / `meetagent create`, extracts
  `<@ID>` mentions and a `\d+m` duration. Free-text date ranges ("this week") deliberately
  left to the LLM layer. Unit-tested (`tests/test_parsing.py`). — (dep: F5, not B1 — no
  circular dep; B1 calls into B2)
- [x] **B3** `agent/tools.py`: real orchestration — `_get_user` resolves `User` via
  `core/db.py`, then calls the still-stubbed `integrations/*` (raises `NotImplementedError`
  until C lands, as expected). `propose_and_book_meeting` includes the organizer's own
  calendar in the slot search, not just attendees'. Orchestration tested against monkeypatched
  integrations (`tests/test_tools.py`). — (dep: F5)
- [x] **B4** `agent/summarize.py`: `summarize_issues(issues, llm=...)` +
  `StandupSummary` pydantic schema; default `llm` uses `ChatOpenAI(...).with_structured_output`
  (lazy import); empty issue list short-circuits without calling the model. Tested with an
  injected fake `llm` — no network/API key needed (`tests/test_summarize.py`). — (dep: B3)
- [ ] **B5** Standup branch: for each member fetch issues → summarize → assemble the
  `standup_digest` card payload → return to Channels. — (dep: B4, A3)
- [x] **B6** `agent/slots.py`: real `best_common_slot` — merges busy intervals with each
  attendee's own non-working-hours blocks (9-17, per their tz via `zoneinfo`), including
  attendees present only in `tz_by_user` (a real bug caught while writing tests — a busy-only
  attendee with an empty list was silently skipping the working-hours check). Unit-tested
  across busy/tz/no-fit cases (`tests/test_slots.py`). — (dep: F5)
- [ ] **B7** Meeting branch: resolve attendees → freebusy → `best_common_slot` →
  `create_event` → return `meeting_confirmation` payload. **Autonomous, no approval.**
  — (dep: B6, A4)
- [ ] **B8** Standup config command logic: apply `set schedule / run now / pause / resume`
  to `StandupConfig`. — (dep: F4, B2)

---

## Epic C — Integrations & data (Person C, Python)

- [x] **C1** `integrations/auth0_vault.get_token` implemented: exchanges a user's stored
  `User.auth0_refresh_token` (added to the model — populated later by C2) for a federated
  connection's access token via Auth0 Token Vault's token-exchange grant, using
  `auth0-python`'s `GetToken.access_token_for_connection` (not `auth0-ai`/`auth0-ai-langchain`
  — those pull in an incompatible langchain/langgraph and openfga-sdk we don't need).
  Connection name per provider comes from `AUTH0_GOOGLE_CONNECTION`/`AUTH0_JIRA_CONNECTION`.
  Raises a clear `RuntimeError` if the user hasn't linked yet (C2's job). Tested with the
  real Auth0 SDK class mocked at the HTTP boundary (`tests/test_auth0_vault.py`, 4 cases);
  full suite 10/10 passing, including a clean-room `pip install` re-verification.
  — (dep: F3) — *C*
- [x] **C2** `integrations/auth0_link.py` implemented: `build_authorize_url` (signed
  `state` carrying slack_user_id + provider, verified real Auth0 `/authorize` params
  including `connection_scope`), `send_link_prompt` (DMs the link via `slack_web`),
  and `handle_callback` (exchanges the code, persists `auth0_refresh_token` +
  best-effort `auth0_user_id` onto `User`, get-or-create). Wired as
  `GET /link/callback` on the same FastAPI app as the AG-UI agent (`agent/main.py`),
  with a `lifespan` hook calling `core.db.init_db()`. Verified live via FastAPI's
  `TestClient` through the real app (not just unit tests): a signed state + mocked
  Auth0 exchange round-trips to a persisted `User` row, and a tampered/malformed
  state returns a clean 400. **Remaining (manual, needs a human):** for real
  teammates linking from their own browsers, `AUTH0_REDIRECT_URI` must be a public
  HTTPS URL registered in Auth0's Allowed Callback URLs (e.g. via ngrok) — see
  `.env.example`. — (dep: C1) — *C*
- [ ] **C3** `integrations/jira_client.get_sprint_issues`: JQL
  `assignee = X AND sprint in openSprints() AND status != Done` via `httpx`; normalize to
  `Issue`. — (dep: C1)
- [ ] **C4** `integrations/google_calendar.get_freebusy`: `freebusy.query` per user over a
  window; return busy intervals. — (dep: C1)
- [ ] **C5** `integrations/google_calendar.create_event`: `events.insert` with
  `conferenceDataVersion=1` (auto Meet link) + attendees. — (dep: C1)
- [x] **C6** `integrations/slack_web.post_message` + `open_dm` implemented (pulled in
  early by C2's DM step — both share one `slack_sdk.WebClient`). `chat.postMessage`
  for scheduled digests; `conversations_open` + `chat.postMessage` for the link DM.
  — (dep: F3) — *C*
- [ ] **C7** `core/scheduler.py`: APScheduler; cron job per active `StandupConfig` (tz-aware);
  job runs the standup branch and posts via C6. — (dep: F4, B5)
- [ ] **C8** Idempotency: before posting, check/create `StandupRun` unique on
  `(config_id, run_date)`. — (dep: F4, C7)

---

## Epic D — Demo & submission (shared, last 2 hours)

- [ ] **D1** Seed 3 demo engineers with linked Jira + Google; realistic sprint issues.
- [ ] **D2** Freeze features. Rehearse: `@dailyagent run now` posts a digest card;
  `@meetagent create a meet with @a @b` books a Meet and confirms in-thread.
- [ ] **D3** Record the 2-minute demo video.
- [ ] **D4** Write project title + description; polish README.
- [ ] **D5** Social media post tagging event partners.

---

## Suggested day-of ordering

1. **Hour 0–1:** F1–F5 together; get mention → Channels → Python echo working; freeze interfaces.
2. **Hour 1–4:** A1–A4 · B1–B6 · C1–C6, all against stubs.
3. **Hour 4–6:** First real integration — `@dailyagent run now` end-to-end (A+B+C);
   `@meetagent` end-to-end.
4. **Hour 6–8:** C7–C8 scheduler + idempotency; B8 config commands; A5 polish.
5. **Last 2 hours:** Epic D. No new features.

## Critical path
`F2 (Channels⇄AG-UI echo) → C1 → (C3,C4,C5) → B4/B6 → B5/B7 → A3/A4 → D2`.
Keep two things unblocked early: **F2** (the AG-UI bridge) and **C1** (Auth0 tokens) —
they gate everything real.
