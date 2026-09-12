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

> **Architecture: hybrid.** Slack is handled by the **CopilotKit Channels** managed runtime
> (Node), which reaches our **Python LangGraph agent** over the **AG-UI protocol**
> (`AGENT_URL`). Channels hosts the public URL — **no Socket Mode, no tunnel/ngrok**. Note:
> managed Slack apps get **no slash commands**, so all interaction is via `@mention`
> (which is what we want). Interactivity/`block_actions` still work if we ever enable an
> approval toggle. The **scheduled** standup has no triggering mention, so the Python
> scheduler posts it via the **Slack Web API (`chat.postMessage`) directly**.

| Trigger | Source | Handler |
|---|---|---|
| `onMention` (`@dailyagent …`, `@meetagent …`) | CopilotKit Channels | subscribe thread → invoke LangGraph agent |
| `onMessage` in a subscribed thread | CopilotKit Channels | invoke agent (follow-ups) |
| scheduled standup tick | Python APScheduler | run standup agent → post via Slack Web API |
| account linking callback | Auth0 redirect | store identity mapping |

Channels handles the Slack 3s ACK for us; the LangGraph agent does the real work behind AG-UI.

## 5. High-Level Design

```
        Slack Workspace  (#team-standup, threads, native cards)
                |  mentions / thread messages
                v
     +------------------------------------+   (managed URL, hosts 3s ACK)
     |  CopilotKit Channels  (Node)       |
     |  - onMention / onMessage           |
     |  - defineChannelComponent (cards)  |
     +------------------+-----------------+
                        |  AG-UI over AGENT_URL
                        v
     +------------------------------------+     +------------------------+
     |  Python LangGraph Agent            |<----|  APScheduler (Python)  |
     |  (OpenAI model)                    |     |  cron per StandupConfig|
     |  tools:                            |     |  -> run standup, post  |
     |   - jira / google / auth0 / slots  |     |     via Slack Web API  |
     +---+-------------+-------------+-----+     +------------------------+
         | on-behalf   |             |
    +----v------+  +---v----------+  +--v---------+
    |  Auth0    |  |  Jira REST   |  |  Google    |     +-----------+
    |  Token    |  |  (JQL,       |  |  Calendar  |     | SQLite    |
    |  Vault    |  |   httpx)     |  |  API       |     | (configs, |
    +-----------+  +--------------+  +------------+     |  runs)    |
     per-user Jira + Google tokens                     +-----------+
```

**Standup flow (interactive):** `@dailyagent run now` → Channels invokes the LangGraph
agent → for each member fetch in-progress sprint issues from Jira (that user's token) →
one LLM summary per person → render digest as a native Channels card → post in-thread →
write `StandupRun` keyed on `(config, date)` (idempotent).

**Standup flow (scheduled):** APScheduler fires → run the standup agent directly →
post the digest via the **Slack Web API (`chat.postMessage`)** (no mention to trigger it).

**Meeting flow:** `@meetagent create a meet with @u1 @u2` → Channels invokes the agent →
resolve attendees → Google `freebusy.query` per attendee → compute best common slot →
`events.insert` with `conferenceData` (Meet link) + invites → post confirmation card
in-thread (autonomous, no approval).

## 6. Tool / Sponsor Integration Map

| Concern | Tool | Notes |
|---|---|---|
| Slack surface: mentions, native cards, 3s ack, managed URL | **CopilotKit Channels** (Node) | Managed Slack app; `onMention`/`onMessage`; `defineChannelComponent` for cards. Fork the **agents-everywhere-starter-kit** Slack template. **No Socket Mode, no slash commands.** |
| Agent framework (the brain) | **LangGraph** (Python) over **AG-UI** | AG-UI partnership; the starter kit ships a LangGraph agent wired to Channels — we swap in our tools. |
| Reasoning model | **OpenAI** (OpenRouter optional) | The model *inside* LangGraph. |
| Jira sprint issues per user | **Atlassian Jira Cloud REST API** (JQL: `assignee = X AND sprint in openSprints()`) | LangGraph tool; `httpx`; Atlassian 3LO OAuth. |
| Per-user delegated auth (Jira + Google) | **Auth0 for AI Agents — Token Vault** | The moat: one-time connect per engineer, agent uses each user's token. |
| Calendar free/busy + create Meet | **Google Calendar API** (`freebusy.query`, `events.insert` + `conferenceData`) | Meet link via `conferenceDataVersion=1`. |
| Scheduled standup posting | **Slack Web API** (`chat.postMessage`) + **APScheduler** | Proactive posts have no mention to ride on, so post directly with the bot token. |

### Interaction model
- `@dailyagent set schedule weekdays 9:00 #standup` / `@dailyagent run now` / `@dailyagent pause`
- `@meetagent create a meet with @u1 @u2 this week 30m` — or auto-detect meeting intent in a thread.

## 7. Deep Dives

- **A. 3-second ACK handled by Channels.** CopilotKit Channels owns the Slack endpoint and
  the fast ACK; our LangGraph agent runs behind AG-UI without racing Slack's 3s limit.
- **B. Reliable scheduling + idempotency.** APScheduler (Python) evaluates each config's cron
  in its tz; runs keyed `(config_id, run_date)`; agent checks for an existing `StandupRun`
  before posting (via Slack Web API). Demo fallback: Slack `chat.scheduleMessage`.
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
- Fully winnable in one day with 3 people.

## 9. Tech stack (hybrid)

**Slack surface (Node — thin, from starter kit)**
- **CopilotKit Channels** (`@copilotkit/runtime`, `@copilotkit/channels`) — managed Slack
  app, `onMention`/`onMessage`, `defineChannelComponent` for native cards.
- Forked from **CopilotKit/agents-everywhere-starter-kit** (`apps/channel` Slack template).

**Agent + logic (Python — where our code lives)**
- **LangGraph** — the agent, exposed over **AG-UI** so Channels can reach it (`AGENT_URL`).
- **OpenAI** — the reasoning model inside LangGraph (OpenRouter optional).
- **Scheduling:** `APScheduler` (cron per StandupConfig, timezone-aware).
- **Scheduled posting:** Slack Web API (`slack_sdk` `chat.postMessage`) for the proactive
  standup (no mention to ride on).
- **Persistence:** `SQLModel` + SQLite (hackathon); Postgres-ready.
- **Jira:** `httpx` against Jira Cloud REST (JQL).
- **Google Calendar:** `google-api-python-client` (`freebusy`, `events.insert`).
- **Delegated auth:** Auth0 for AI Agents — Token Vault (per-user Jira + Google tokens).
- **Utils:** `pydantic`, `python-dotenv`.

## 10. Team split (3 people)

- **Person A — Slack surface (Channels):** fork/run the starter-kit Slack template, provision
  the Channel, wire `AGENT_URL` to our Python agent, build `defineChannelComponent` cards
  for the standup digest + meeting confirmation. (Thin Node layer — mostly config.)
- **Person B — Agent core (LangGraph, Python):** the LangGraph graph + AG-UI server, standup
  summarization, meeting reasoning + common-slot algorithm, mention/command parsing.
- **Person C — Integrations & data (Python):** Auth0 Token Vault, Jira client, Google Calendar
  client (as LangGraph tools), DB models/persistence, APScheduler + scheduled Slack posting.

Demo, video, README, and the social post are shared, owned by whoever finishes first.

## 11. Submission checklist (from handbook)

- [ ] Project title
- [ ] Written description
- [ ] Public GitHub repository
- [ ] Two-minute demo video
- [ ] Social media post tagging event partners
- [ ] Net-new build during the hackathon period
