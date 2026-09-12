# Slack Standup + Meeting Agent — Project Plan

> Hackathon: **Agents, Everywhere** — build an agent for a place people already work,
> talk, or live, and make it meaningfully more useful because of that context.
> **Environment:** Slack. **Theme fit:** the agent lives where the standup and the
> "let's hop on a call" conversation already happen.

## 1. Concept

A Slack-native agent (exposed as two bots) that removes two daily frictions for an
engineering team:

- **`@dailyagent`** — replaces the manual daily standup. On a configurable schedule
  it pulls each engineer's current-sprint work from Jira, summarizes it per person
  (done / in-progress / blockers), and posts a threaded digest to Slack.
- **`@meetagent`** — schedules meetings from chat. When members mention creating a
  meeting (or call it explicitly, e.g. `@meetagent create a meet with @user1 @user2`),
  it reads each attendee's Google Calendar, finds the best common free slot, and
  **autonomously** creates a Google Calendar event with a Meet link, invites everyone,
  and posts the confirmation in the Slack thread — no human approval step.

**Why it beats a chatbox:** the value comes from being *in* the workspace — reacting to
live conversation, acting on each engineer's own Jira/Calendar via delegated auth, and
posting back where the team already is.

## 2. Requirements (Hello Interview delivery framework)

### Functional
- **FR1 — Async standup:** on a schedule, for a configured team, pull each member's
  current-sprint Jira issues, summarize per person, post a threaded digest to a channel.
- **FR2 — Standup config:** users set frequency, time, timezone, channel, members via
  `@dailyagent` (e.g. `@dailyagent set schedule weekdays 9:00 #team-standup`).
- **FR3 — Meeting scheduling:** triggered by explicit `@meetagent` mention or detected
  intent in a thread. Resolve attendees → read each Google Calendar free/busy → compute
  best common slot → **autonomously** create the Calendar event with a Meet link and post
  confirmation in-thread (no approval gate).

### Human-in-the-loop policy
Both features act **autonomously** — no approval buttons.
- Meeting: the agent picks the earliest viable common slot and books it directly.
- Standup: the digest is posted to the thread directly.
An optional per-feature `require_approval` toggle can add Approve/Reject buttons later,
but the default flow is hands-off.

### Non-functional
- **Slack 3-second rule:** ACK every event/command within 3s; do real work async.
- **Reliability:** scheduled standups fire despite restarts; runs are idempotent.
- **Security:** per-user delegated auth for Jira + Google (act on behalf, least privilege);
  no shared god-token.
- **Latency:** `@meetagent` proposes slots within a few seconds.
- **Multi-tenant-ready:** design for multiple teams/workspaces (demo uses one).

## 3. Core Entities

```jsonc
Workspace     { id, slack_team_id, bot_token }
User          { id, slack_user_id, tz, jira_account_id, google_account_id }
              // tokens NOT stored here — held in Auth0 Token Vault
StandupConfig { id, workspace_id, channel_id, member_ids[], schedule_cron, tz, active }
StandupRun    { id, config_id, run_date, status, digest_message_ts }
              // idempotency key = (config_id, run_date)
MeetingRequest{ id, thread_ts, organizer_id, attendee_ids[], window,
                proposed_slots[], chosen_slot,
                status: DETECTED|PROPOSED|CONFIRMED|BOOKED|FAILED,
                calendar_event_id }
```

## 4. API / System Interface

| Trigger | Source | Handler |
|---|---|---|
| `app_mention` (`@dailyagent …`, `@meetagent …`) | Slack Events API | ack → enqueue `HandleMention` |
| `message` in watched thread | Slack Events API | intent check → maybe enqueue |
| `block_actions` (optional Approve/Reject) | Slack interactivity | only if `require_approval` toggle is on |
| scheduler tick | internal cron | enqueue `RunStandup(config_id, date)` |
| OAuth callback | Auth0 redirect | store identity mapping |

Everything beyond the 3s ack is a **job on a queue** processed by workers.

## 5. High-Level Design

```
        Slack Workspace  (#team-standup, threads, buttons)
                |  events / interactions / mentions
                v
     +-------------------------+   ack < 3s, then enqueue
     |  Slack Gateway (Bolt)   |--------------+
     |  - verify signature     |              |
     |  - fast ACK             |              v
     +-------------------------+        +-----------+
                ^  post digest / cards   | Job Queue | (Redis/SQS)
                |                        +-----+-----+
     +----------+-----------+                  |
     |  Scheduler Service    |-enqueue RunStandup
     |  (durable cron per    |                  |
     |   StandupConfig, tz)  |                  v
     +----------------------+        +----------------------+
                                     |   Agent Workers       |
                                     |  - Standup Agent      |
                                     |  - Meeting Agent      |
                                     |   LLM (OpenAI/Claude) |
                                     +---+-------------+-----+
                    on-behalf tokens     |             |
              +-----------------------+---v--+   +------v-----+
              |  Auth0 Token Vault           |   | Postgres   |
              | (per-user Jira + Google)     |   | configs,   |
              +----+------------------+------+   | runs       |
                   v                  v          +------------+
             Jira REST API     Google Calendar API
```

**Standup flow:** Scheduler fires → enqueue `RunStandup` → worker loads config → for each
member fetch in-progress sprint issues from Jira (that user's token) → one LLM summary per
person → assemble threaded digest → post via Bolt → write `StandupRun` keyed on
`(config, date)` (idempotent).

**Meeting flow:** `@meetagent create a meet with @u1 @u2` → Bolt acks → enqueue
`HandleMention` → resolve attendees → Google `freebusy.query` per attendee → compute best
common slot → `events.insert` with `conferenceData` (Meet link) + invites →
post confirmation card in-thread (autonomous, no approval).

## 6. Tool / Sponsor Integration Map

| Concern | Tool | Notes |
|---|---|---|
| Slack in/out, mentions, buttons, 3s ack, scheduled posts | **Slack Bolt SDK** (+ **CopilotKit channels** to bind agent to Slack) | Bolt handles the Slack app plumbing; CopilotKit hosts the agent runtime. |
| Jira sprint issues per user | **Atlassian Jira Cloud REST API** (JQL: `assignee = X AND sprint in openSprints()`) | Wrap as an agent tool; Atlassian 3LO OAuth. |
| Per-user delegated auth (Jira + Google) | **Auth0 for AI Agents — Token Vault** | The moat: one-time connect per engineer, agent uses each user's token. |
| Calendar free/busy + create Meet | **Google Calendar API** (`freebusy.query`, `events.insert` + `conferenceData`) | Meet link via `conferenceDataVersion=1`. |
| Reasoning / summarization | **OpenAI Agents SDK** or **Claude** (OpenRouter optional) | Jira/Calendar calls defined as shared agent tools. |

### Interaction model
- `@dailyagent set schedule weekdays 9:00 #standup` / `@dailyagent run now` / `@dailyagent pause`
- `@meetagent create a meet with @u1 @u2 this week 30m` — or auto-detect meeting intent in a thread.

## 7. Deep Dives

- **A. 3-second ACK → async everywhere.** Gateway only verifies signature and acks; all
  Jira/Calendar/LLM work runs in workers off the queue.
- **B. Reliable scheduling + idempotency.** Durable scheduler evaluates each config's cron
  in its tz; jobs keyed `(config_id, run_date)`; worker checks for existing `StandupRun`
  before posting. Demo fallback: Slack `chat.scheduleMessage`.
- **C. Multi-user delegated auth.** Each engineer links Jira + Google once via Auth0;
  agent uses that user's token per action. Least-privilege, auditable, revocable.
- **D. Common-slot algorithm.** Merge each attendee's busy intervals over the window,
  invert against per-person working hours, return earliest N gaps >= duration.
- **E. Standup summarization.** Per member: JQL fetch → normalize issues → one LLM call →
  `{done, in_progress, blockers}` rendered with links (one call/person, parallelizable).

## 8. Demo-day scope cut

- Standup: manual `@dailyagent run now` + one real scheduled fire.
- Meeting: explicit `@meetagent` mention path (passive intent-detection = stretch).
- One Slack workspace, 3 seeded engineers with linked Google + Jira.
- Fully winnable in one day with 4 people.

## 9. Tech stack (Python)

- **Slack:** `slack_bolt` (Socket Mode — no public URL needed for dev)
- **Scheduling:** `APScheduler` (cron per StandupConfig, timezone-aware)
- **Persistence:** `SQLModel` + SQLite (hackathon); Postgres-ready
- **Jira:** `httpx` against Jira Cloud REST (JQL)
- **Google Calendar:** `google-api-python-client` (`freebusy`, `events.insert`)
- **Delegated auth:** Auth0 for AI Agents — Token Vault (per-user Jira + Google tokens)
- **LLM:** OpenAI Agents SDK **or** Anthropic SDK (Claude); `httpx`, `pydantic`, `python-dotenv`
- **Async work:** Bolt acks fast, then work runs in a background thread/executor
  (RQ + Redis optional if we want a real queue)

## 10. Team split (3 people)

- **Person A — Slack surface:** Bolt app, event/mention handlers, mention parsing,
  Block Kit formatting, posting standup digests + meeting confirmations.
- **Person B — Agent core:** LLM tool loop, standup summarization, meeting reasoning +
  common-slot algorithm, `@dailyagent`/`@meetagent` command parsing.
- **Person C — Integrations & data:** Auth0 Token Vault, Jira client, Google Calendar
  client, DB models/persistence, APScheduler.

Demo, video, README, and the social post are shared, owned by whoever finishes first.

## 11. Submission checklist (from handbook)

- [ ] Project title
- [ ] Written description
- [ ] Public GitHub repository
- [ ] Two-minute demo video
- [ ] Social media post tagging event partners
- [ ] Net-new build during the hackathon period
