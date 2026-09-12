# TASKS.md — Work Breakdown (Team of 3)

Small, assignable tasks grouped by epic. IDs like `A1`, `B2`, `C3`.
Owners: **A = Slack surface**, **B = Agent core**, **C = Integrations & data**.
Do the **Foundation** epic together first (or split the 3 tasks), then work in parallel
against the interfaces. Stub-first: build against fake data, swap real clients in later.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · **(dep: …)** = depends on.

---

## Epic 0 — Foundation (shared, hour 0–1)

- [ ] **F1** Repo scaffolding: create the folder layout from `AGENTS.md`,
  `requirements.txt`, `main.py` skeleton, `.env.example`. — *any*
- [ ] **F2** `core/config.py` + `.env.example`: load all env vars (Slack tokens, Auth0,
  Jira base URL, Google creds, LLM key). — *C*
- [ ] **F3** `core/models.py` + `core/db.py`: SQLModel entities (Workspace, User,
  StandupConfig, StandupRun, MeetingRequest) + SQLite engine/session. — *C*
- [ ] **F4** Agree on the internal interfaces below and write them as stubs so A/B/C
  don't block each other. — *all*

### Shared interfaces (freeze these in hour 1)
```python
# integrations/jira_client.py
def get_sprint_issues(user: User) -> list[Issue]: ...          # C provides; B/A stub

# integrations/google_calendar.py
def get_freebusy(user: User, window: Window) -> list[BusyInterval]: ...
def create_event(organizer: User, attendees: list[User], slot: Slot) -> EventResult: ...

# integrations/auth0_vault.py
def get_token(user: User, provider: Literal["jira","google"]) -> str: ...

# agents/slots.py
def best_common_slot(busy: dict[UserId, list[BusyInterval]],
                     window: Window, duration_min: int, tz_by_user) -> Slot | None: ...

# core/llm.py
def summarize_member(issues: list[Issue]) -> MemberSummary: ...  # {done, in_progress, blockers}
```

---

## Epic A — Slack surface (Person A)

- [ ] **A1** Slack app manifest + Socket Mode setup; bot joins a test channel; `main.py`
  starts the Bolt app. — (dep: F1)
- [ ] **A2** `app_mention` handler: fast `ack()`, then dispatch to a background worker
  (thread/executor). Verify the 3s rule holds. — (dep: A1)
- [ ] **A3** `slack_app/parsing.py`: parse `@dailyagent`/`@meetagent` subcommands and
  extract `@mention` user IDs, dates, durations. — (dep: A2)
- [ ] **A4** `slack_app/formatting.py`: Block Kit builder for the **standup digest**
  (per person: ✅ done / 🟡 in-progress / ❌ blockers, with Jira links) matching the
  target screenshot. — (dep: F4)
- [ ] **A5** Block Kit builder for the **meeting confirmation** card (time, attendees,
  Meet link). — (dep: F4)
- [ ] **A6** Post + thread helpers: post digest to channel, post confirmation in-thread,
  store `message_ts`. — (dep: A1)
- [ ] **A7** (stretch) Passive meeting-intent detection on `message` events in threads.

---

## Epic B — Agent core (Person B)

- [ ] **B1** `core/llm.py`: LLM client + tool-calling loop (OpenAI Agents SDK or Anthropic).
  Define Jira/Calendar tools. — (dep: F1)
- [ ] **B2** `core/llm.summarize_member`: given a user's sprint issues, produce
  `{done, in_progress, blockers}`. Prompt + output schema (pydantic). — (dep: F4)
- [ ] **B3** `agents/standup_agent.py`: orchestrate a run — for each member, fetch issues
  (C's client), summarize (B2), hand digest data to A's formatter, trigger post. Parallel
  per member. — (dep: B2, C-Jira stub)
- [ ] **B4** `agents/slots.py`: implement `best_common_slot` (merge busy intervals, invert
  vs working hours + tz, earliest gap >= duration). Unit-tested. — (dep: F4)
- [ ] **B5** `agents/meeting_agent.py`: orchestrate scheduling — resolve attendees, call
  freebusy (C), run B4, call `create_event` (C), hand result to A's confirmation card.
  **Autonomous, no approval.** — (dep: B4, C-Calendar stub)
- [ ] **B6** Standup config command logic: apply `set schedule / run now / pause / resume`
  to `StandupConfig` (persist via C's models). — (dep: F3, A3)

---

## Epic C — Integrations & data (Person C)

- [ ] **C1** `integrations/auth0_vault.py`: fetch per-user delegated tokens (Jira, Google)
  from Auth0 Token Vault; identity mapping slack_user_id → auth0_user_id. — (dep: F2)
- [ ] **C2** One-time account-linking flow: DM a user an Auth0 connect URL; handle the
  OAuth callback; persist the mapping. — (dep: C1)
- [ ] **C3** `integrations/jira_client.get_sprint_issues`: JQL
  `assignee = X AND sprint in openSprints() AND status != Done` via `httpx`; normalize to
  `Issue`. — (dep: C1)
- [ ] **C4** `integrations/google_calendar.get_freebusy`: `freebusy.query` per user over a
  window; return busy intervals. — (dep: C1)
- [ ] **C5** `integrations/google_calendar.create_event`: `events.insert` with
  `conferenceDataVersion=1` to auto-create a Meet link; add attendees. — (dep: C1)
- [ ] **C6** `core/scheduler.py`: APScheduler; register a cron job per active
  `StandupConfig` (tz-aware); job enqueues `standup_agent.run(config, date)`. — (dep: F3, B3)
- [ ] **C7** Idempotency: before posting, check/create `StandupRun` unique on
  `(config_id, run_date)`. — (dep: F3, C6)

---

## Epic D — Demo & submission (shared, last 2 hours)

- [ ] **D1** Seed 3 demo engineers with linked Jira + Google; put realistic sprint issues.
- [ ] **D2** Freeze features. Rehearse: `@dailyagent run now` posts a digest;
  `@meetagent create a meet with @a @b` books a Meet and confirms in-thread.
- [ ] **D3** Record the 2-minute demo video.
- [ ] **D4** Write project title + description; polish README.
- [ ] **D5** Social media post tagging event partners.

---

## Suggested day-of ordering

1. **Hour 0–1:** F1–F4 together; freeze interfaces.
2. **Hour 1–4:** A1–A4 · B1–B4 · C1–C5, all against stubs.
3. **Hour 4–6:** First integration — real `@dailyagent run now` end-to-end (A+B+C);
   real `@meetagent` end-to-end.
4. **Hour 6–8:** C6–C7 scheduler + idempotency; B6 config commands; A5/A6 polish.
5. **Last 2 hours:** Epic D. No new features.

## Critical path
`F3/F4 → C1 → (C3,C4,C5) → B3/B5 → A4/A5 → D2`. Keep C1 (Auth0 tokens) unblocked early —
it gates both real integrations.
