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

- [ ] **F1** Fork **CopilotKit/agents-everywhere-starter-kit**; get the `apps/channel` Slack
  template running (`npm ci`, `.env`, `npm run dev:slack`); confirm the sample agent replies
  to a mention in a test Slack channel. — *A*
- [ ] **F2** Stand up the Python side: repo layout from `AGENTS.md`, `requirements.txt`,
  a minimal **LangGraph agent exposed over AG-UI** that echoes; point the Channels
  `AGENT_URL` at it and confirm end-to-end mention → Python → reply. — *B*
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

- [ ] **A1** Provision the Channel (`copilotkit channels add --adapter slack`); set the
  Slack **Bot User OAuth Token** + **Signing Secret**; confirm status `online`. — (dep: F1)
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

- [ ] **B1** LangGraph graph skeleton + AG-UI server (`agent/main.py`, `agent/graph.py`):
  route a mention to the `daily` or `meet` branch based on parsed intent. — (dep: F2)
- [ ] **B2** `agent/parsing.py`: parse `@dailyagent`/`@meetagent` subcommands and extract
  `@mention` user IDs, dates, durations from the message text. — (dep: B1)
- [ ] **B3** `agent/tools.py`: define LangGraph tools wrapping `jira_client`,
  `google_calendar`, `auth0_vault`, `slots` (against C's stubs first). — (dep: F5)
- [ ] **B4** Standup summarization: given a user's sprint issues, produce
  `{done, in_progress, blockers}` (OpenAI call + pydantic schema); one call per member,
  parallelized. — (dep: B3)
- [ ] **B5** Standup branch: for each member fetch issues → summarize → assemble the
  `standup_digest` card payload → return to Channels. — (dep: B4, A3)
- [ ] **B6** `agent/slots.py`: implement `best_common_slot` (merge busy intervals, invert
  vs working hours + tz, earliest gap >= duration). Unit-tested. — (dep: F5)
- [ ] **B7** Meeting branch: resolve attendees → freebusy → `best_common_slot` →
  `create_event` → return `meeting_confirmation` payload. **Autonomous, no approval.**
  — (dep: B6, A4)
- [ ] **B8** Standup config command logic: apply `set schedule / run now / pause / resume`
  to `StandupConfig`. — (dep: F4, B2)

---

## Epic C — Integrations & data (Person C, Python)

- [ ] **C1** `integrations/auth0_vault.get_token`: fetch per-user delegated tokens (Jira,
  Google) from Auth0 Token Vault; identity mapping slack_user_id → auth0_user_id. — (dep: F3)
- [ ] **C2** One-time account-linking flow: DM a user an Auth0 connect URL; handle the
  callback; persist the mapping. — (dep: C1)
- [ ] **C3** `integrations/jira_client.get_sprint_issues`: JQL
  `assignee = X AND sprint in openSprints() AND status != Done` via `httpx`; normalize to
  `Issue`. — (dep: C1)
- [ ] **C4** `integrations/google_calendar.get_freebusy`: `freebusy.query` per user over a
  window; return busy intervals. — (dep: C1)
- [ ] **C5** `integrations/google_calendar.create_event`: `events.insert` with
  `conferenceDataVersion=1` (auto Meet link) + attendees. — (dep: C1)
- [ ] **C6** `integrations/slack_web.post_message`: `chat.postMessage` with Block Kit for
  scheduled digests (bot token). — (dep: F3)
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
