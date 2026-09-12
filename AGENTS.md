# AGENTS.md — Project Context for Coding Agents

This file gives an AI coding agent (Claude Code, Cursor, etc.) the full context needed to
work on this repo. Read this before making changes. See `PLAN.md` for the system design and
`TASKS.md` for the task breakdown.

## What we're building

A **Slack-native agent** for engineering teams, for the "Agents, Everywhere" hackathon.
Two capabilities, both living inside Slack:

1. **`@dailyagent`** — replaces the manual daily standup. On a configurable schedule it
   pulls each engineer's current-sprint Jira work, summarizes it per person
   (done / in-progress / blockers), and posts a threaded digest to a Slack channel.
2. **`@meetagent`** — schedules meetings from chat. On mention (e.g.
   `@meetagent create a meet with @user1 @user2`) it reads each attendee's Google Calendar,
   finds the best common free slot, and **autonomously** creates a Google Calendar event
   with a Meet link, invites everyone, and posts confirmation in-thread.

### Human-in-the-loop policy (IMPORTANT)
Both features are **autonomous — NO approval gate**. Do not add Approve/Reject buttons to
the default flow. The meeting is booked directly; the standup digest is posted directly.
A `require_approval` config toggle may exist as an *optional* stretch, but it defaults off.

## Architecture: HYBRID (read this carefully)

Slack is handled by **CopilotKit Channels** (a Node runtime), which reaches our
**Python LangGraph agent** over the **AG-UI protocol** at `AGENT_URL`.

```
Slack ──mention/thread──► CopilotKit Channels (Node)  ──AG-UI (AGENT_URL)──►  Python LangGraph agent
                          (managed URL, onMention,                              ├─ standup logic
                           onMessage, native cards)                            ├─ meeting logic + slots
                                                                                ├─ tools: jira/google/auth0
Scheduled standup ─────────────────────────────────────────────────────────► └─ LLM summarize (OpenAI)
   (Python APScheduler → Slack Web API chat.postMessage directly)
```

Key consequences of using CopilotKit Channels (a managed Slack app):
- **No Socket Mode, no public tunnel/ngrok** — Channels hosts the URL.
- **No slash commands** — managed Slack apps never receive them. ALL interaction is via
  `@mention`. Do not build slash-command handlers.
- **`onMention`** subscribes a thread and runs the agent; **`onMessage`** replies only in
  already-subscribed threads. Native cards via **`defineChannelComponent`**.
- Channels handles Slack's 3-second ACK — our agent does not race that limit.
- The **scheduled** standup has no triggering mention, so the Python scheduler posts it via
  the **Slack Web API (`chat.postMessage`)** directly with the bot token.

We fork **CopilotKit/agents-everywhere-starter-kit** (its `apps/channel` Slack template) for
the Node layer; it already ships a LangGraph-style agent wired to Channels over AG-UI, so we
swap in our tools rather than build the bridge from scratch.

## Language & stack

**Node (thin Slack layer — from starter kit):**
- `@copilotkit/runtime`, `@copilotkit/channels` (Channels runtime + native cards).

**Python (all our real logic — 3.11+):**
- **LangGraph** — the agent, exposed over **AG-UI** (`AGENT_URL`).
- **OpenAI** — the model inside LangGraph (OpenRouter optional).
- `APScheduler` — timezone-aware cron for standups.
- `slack_sdk` — `chat.postMessage` for scheduled/proactive posts.
- `SQLModel` + SQLite — persistence (Postgres-compatible).
- `httpx` — Jira Cloud REST (JQL).
- `google-api-python-client` — Google Calendar (`freebusy`, `events.insert`).
- **Auth0 for AI Agents — Token Vault** — per-user Jira + Google tokens.
- `pydantic`, `python-dotenv`.

Do not add extra Node services beyond the Channels layer. Keep all business logic in Python.

## Repository layout (target)

```
slack-standup-meet-agent/
  channels/                   # NODE — CopilotKit Channels (forked from starter kit)
    src/channel.ts            # createChannel({ agent, components: [...] })
    src/components/           # defineChannelComponent cards (digest, meeting confirmation)
    .copilotkit/channels.json
    package.json
  agent/                      # PYTHON — LangGraph agent (the brain), served over AG-UI
    main.py                   # AG-UI server exposing the graph at AGENT_URL
    graph.py                  # LangGraph graph: routes @dailyagent / @meetagent
    tools.py                  # LangGraph tools wrapping the integrations below
    prompts.py
    slots.py                  # common-slot algorithm (free/busy -> best slot)
    parsing.py                # parse @dailyagent/@meetagent commands + @mentions
  core/                       # PYTHON — shared
    config.py                 # env loading, settings
    db.py                     # SQLModel engine/session
    models.py                 # Workspace, User, StandupConfig, StandupRun, MeetingRequest
    scheduler.py              # APScheduler; scheduled standup -> Slack Web API
  integrations/               # PYTHON — external systems
    auth0_vault.py            # per-user delegated tokens (Jira, Google)
    jira_client.py            # sprint issues per user via JQL
    google_calendar.py        # freebusy.query + events.insert (Meet link)
    slack_web.py              # chat.postMessage for scheduled posts
  tests/
  requirements.txt
  .env.example                # all required env vars, no secrets
```

## Key domain rules

- **AG-UI is the contract** between Channels and the Python agent. The agent is an AG-UI
  server; Channels is configured with its `AGENT_URL`. Don't invent a custom transport.
- **Interaction is mention-only** (no slash commands). Parse subcommands from the mention text.
- **Per-user delegated auth:** when summarizing user X's work, use X's Jira token; when
  reading a calendar, use that person's Google token. Never a single shared token. Tokens
  come from Auth0 Token Vault, keyed by the user's identity mapping.
- **Idempotent standups:** a `StandupRun` is keyed on `(config_id, run_date)`. Check for an
  existing run before posting so retries never double-post.
- **Meeting slot rule:** merge all attendees' busy intervals over the requested window,
  invert against per-person working hours (respect timezones), pick the earliest gap
  >= the requested duration.
- **Meet link:** create events with `conferenceDataVersion=1` and a
  `conferenceData.createRequest` to auto-generate the Google Meet link.
- **Scheduled vs interactive posting:** interactive replies go back through Channels/AG-UI;
  scheduled standups post via `integrations/slack_web.py` (`chat.postMessage`).

## Core entities (see core/models.py)

```
Workspace     { id, slack_team_id, bot_token }
User          { id, slack_user_id, tz, jira_account_id, google_account_id }
StandupConfig { id, workspace_id, channel_id, member_ids[], schedule_cron, tz, active }
StandupRun    { id, config_id, run_date, status, digest_message_ts }  # unique(config_id, run_date)
MeetingRequest{ id, thread_ts, organizer_id, attendee_ids[], window,
                chosen_slot, status, calendar_event_id }
```

## Interaction commands (all via @mention)

- `@dailyagent set schedule weekdays 9:00 #team-standup`
- `@dailyagent run now`
- `@dailyagent pause` / `@dailyagent resume`
- `@meetagent create a meet with @u1 @u2 [this week] [30m]`
- Passive: detect meeting intent in a subscribed thread (stretch goal).

## Conventions

- Always use red/green TDD when building a new feature or modifying existing code.
- Keep SOLID, DRY, KISS, YAGNI principles. Implementation must be the simplest of any
  possible solutions and the most efficient in terms of time and space complexity.
- Use concurrency and async when appropriate.
- Depending on the situation, use Creational patterns or Structural patterns or
  Behavioral patterns.
- The code must be secured from OWASP Top 10:2025 vulnerabilities.
- Type hints everywhere; `pydantic` models for external API payloads.
- No secrets in code or git. All config via env vars listed in `.env.example`.
- Keep integrations behind thin client classes so they can be mocked in tests and demoed
  with fixtures if a live API is unavailable.
- LangGraph tools should be small, pure wrappers over `integrations/*`.
- Small, focused modules; match existing style when editing.

## Non-goals (for the hackathon build)

- No multi-workspace onboarding UI (single workspace is fine).
- No payments/cost-splitting.
- No web dashboard — Slack is the only surface.
- No slash commands (not supported by managed Channels apps).

## Git conventions

- Do NOT add a `Co-Authored-By` trailer to commits (project owner preference).
- Do NOT force-push. Land changes via PRs off `main`.
- Keep commits scoped to one task where possible.
