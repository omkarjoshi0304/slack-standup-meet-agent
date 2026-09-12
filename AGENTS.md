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

## Language & stack

- **Python 3.11+** everywhere. This is a Python project — do not introduce Node services.
- `slack_bolt` (Socket Mode) for the Slack app.
- `APScheduler` for timezone-aware cron scheduling.
- `SQLModel` + SQLite for persistence (Postgres-compatible).
- `httpx` for Jira Cloud REST (JQL queries).
- `google-api-python-client` for Google Calendar (`freebusy`, `events.insert`).
- **Auth0 for AI Agents — Token Vault** holds per-user Jira + Google tokens (delegated auth).
- LLM: OpenAI Agents SDK **or** Anthropic SDK (Claude). `pydantic`, `python-dotenv`.
- Bolt acks within Slack's 3s window, then runs work in a background thread/executor.

## Repository layout (target)

```
slack-standup-meet-agent/
  main.py                     # entrypoint: start Bolt (Socket Mode) + scheduler
  requirements.txt
  .env.example                # all required env vars, no secrets
  core/
    config.py                 # env loading, settings
    db.py                     # SQLModel engine/session
    models.py                 # Workspace, User, StandupConfig, StandupRun, MeetingRequest
    scheduler.py              # APScheduler setup, RunStandup jobs, idempotency
    llm.py                    # LLM client + tool-calling loop
  slack_app/
    app.py                    # Bolt app, event handlers (app_mention, message)
    parsing.py                # parse @dailyagent/@meetagent commands + @mentions
    formatting.py             # Block Kit builders (digest, meeting confirmation)
  agents/
    standup_agent.py          # orchestrates a standup run
    meeting_agent.py          # orchestrates meeting scheduling
    slots.py                  # common-slot algorithm (free/busy -> best slot)
  integrations/
    auth0_vault.py            # get per-user delegated tokens
    jira_client.py            # sprint issues per user via JQL
    google_calendar.py        # freebusy.query + events.insert (Meet link)
  tests/
```

## Key domain rules

- **Slack 3-second ACK:** every handler must `ack()` fast, then do real work async.
  Never block the handler on Jira/Calendar/LLM calls.
- **Per-user delegated auth:** when summarizing user X's work, use X's Jira token; when
  reading a calendar, use that person's Google token. Never a single shared token.
  Tokens come from Auth0 Token Vault, keyed by the user's identity mapping.
- **Idempotent standups:** a `StandupRun` is keyed on `(config_id, run_date)`. Check for an
  existing run before posting so retries never double-post.
- **Meeting slot rule:** merge all attendees' busy intervals over the requested window,
  invert against per-person working hours (respect timezones), pick the earliest gap
  >= the requested duration.
- **Meet link:** create events with `conferenceDataVersion=1` and a
  `conferenceData.createRequest` to auto-generate the Google Meet link.

## Core entities (see models.py)

```
Workspace     { id, slack_team_id, bot_token }
User          { id, slack_user_id, tz, jira_account_id, google_account_id }
StandupConfig { id, workspace_id, channel_id, member_ids[], schedule_cron, tz, active }
StandupRun    { id, config_id, run_date, status, digest_message_ts }  # unique(config_id, run_date)
MeetingRequest{ id, thread_ts, organizer_id, attendee_ids[], window,
                chosen_slot, status, calendar_event_id }
```

## Interaction commands

- `@dailyagent set schedule weekdays 9:00 #team-standup`
- `@dailyagent run now`
- `@dailyagent pause` / `@dailyagent resume`
- `@meetagent create a meet with @u1 @u2 [this week] [30m]`
- Passive: detect meeting intent in a thread (stretch goal).

## Conventions

- Type hints everywhere; `pydantic` models for external API payloads.
- No secrets in code or git. All config via env vars listed in `.env.example`.
- Keep integrations behind thin client classes so they can be mocked in tests and demoed
  with fixtures if a live API is unavailable.
- Small, focused modules; match existing style when editing.

## Non-goals (for the hackathon build)

- No multi-workspace onboarding UI (single workspace is fine).
- No payments/cost-splitting.
- No web dashboard — Slack is the only surface.

## Git conventions

- Do NOT add a `Co-Authored-By` trailer to commits (project owner preference).
- Branch off `main`; keep commits scoped to one task where possible.
