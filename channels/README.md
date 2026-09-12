# channels — CopilotKit Channels (Slack surface)

Thin Node layer. Forwards Slack `@mention`/thread events to the Python LangGraph agent in
`../agent` over the AG-UI protocol (`AGENT_URL`). See root `AGENTS.md` for the full
architecture.

## What's implemented (tasks F1/F2, A2–A5)

- `src/env.ts` — env var helpers (tested: `src/env.test.ts`).
- `src/agent.ts` — `HttpAgent` pointed at `AGENT_URL`, wrapped in a reentry-safe facade
  (tested: `src/agent.test.ts`).
- `src/handlers.ts` — `onMention` (subscribe + run) and `onMessage` (run only in subscribed
  threads) behavior, kept out of `channel.ts` so it can be tested against a fake thread with
  no credentials and no network (tested: `src/handlers.test.ts`).
- `src/channel.ts` — `createChannel`: the Channel name, the agent factory, the registered
  handlers, and the two card components.
- `src/components/standup-digest.tsx` (A3) and `src/components/meeting-confirmation.tsx`
  (A4) — `defineChannelComponent` cards with `zod` parameter schemas.
- `src/server.ts` — boots the CopilotKit runtime and Channel; exits non-zero if the
  Channel doesn't reach `online`.

Verified locally: `npx tsc --noEmit` passes, `npm test` passes, `npm run doctor` is clean, and
`npm run start` reaches `Channel "mytro" online — listening on :3000` against the real
project.

## The agent must *stream* its reply, not just write it into state

This is the single non-obvious constraint of the whole surface, and it silently
swallowed every reply until it was found (see A1 in `TASKS.md`).

CopilotKit's Slack renderer (`createRunRenderer` in `@copilotkit/channels-slack`) renders
`TEXT_MESSAGE_START/CONTENT/END`, tool-call events, and custom events. It does **not** read
`MESSAGES_SNAPSHOT`. A LangGraph node that returns an `AIMessage` in its state update
produces only `STATE_SNAPSHOT` / `MESSAGES_SNAPSHOT` on the AG-UI wire, so the delivery is
rendered as an empty message: the dashboard's State tab shows the right text, History logs
`Provider delivery completed`, and Slack shows nothing at all — no error anywhere.

Every node that produces a reply must emit it explicitly — see `emit_assistant_text` in
`../agent/graph.py`, which dispatches `ag_ui_langgraph`'s `manually_emit_message` custom
event. Only a chat model invoked with *streaming* produces the text events on its own; the
react-agent branches use `ainvoke`, which does not, so they emit their final reply through
the same helper. `tests/test_graph.py` asserts the event is emitted, so the failure mode
can't return unnoticed.

## Card components (A3/A4)

The agent calls a card by name and the hosted pipeline renders it into Slack Block Kit. Both
card payloads are **frozen stubs** until Epic B produces them for real (B5 for the digest,
B7 for the meeting) — see `src/components/stubs.ts` for the sample payloads the tests and
the preview use.

| Component | Name the agent calls | Payload |
|---|---|---|
| `standupDigest` | `standup_digest` | `{ title, people: [{ name, status, summary, jiraLinks: [{ key, url }] }] }`, `status` one of `done` / `in_progress` / `blocked` (rendered ✅ / 🟡 / ❌) |
| `meetingConfirmation` | `meeting_confirmation` | `{ title, startIso, endIso, timezone, attendees: [{ name, email }], meetUrl }` |

Because live delivery is blocked (see A1 in `TASKS.md`), cards are verified by rendering them
to Block Kit locally — the same `renderToIR` → `renderSlackMessage` path the hosted pipeline
uses:

```
npm run cards:preview     # prints both cards as Block Kit JSON
```

Paste either object into <https://app.slack.com/block-kit-builder> for a visual check.
`src/components/*.test.ts` assert on that same rendered JSON.

## Required Slack bot scopes (A5)

These are the 17 bot scopes the CopilotKit wizard's manifest actually granted, read from the
live app's **OAuth & Permissions → Reinstall** URL (app `A0C197HT29K`, workspace
`New Workspace`). The "needed for" column comes from the scope table shipped in
`node_modules/@copilotkit/channels-slack/README.md` — the adapter that makes these calls.

| Scope | Needed for |
|---|---|
| `app_mentions:read` | Receiving the `app_mention` event. Everything here is mention-gated, so without it the bot never wakes up. |
| `chat:write` | Posting the reply, streaming it, ephemeral messages, and opening modals. |
| `channels:history` / `channels:read` | Reading public-channel thread messages (`conversations.replies`) and channel metadata — needed for `onMessage` follow-ups. |
| `groups:history` / `groups:read` | The same, in private channels. |
| `im:history` / `im:read` / `im:write` | The same, in DMs, plus opening a DM. |
| `mpim:history` / `mpim:read` | The same, in group DMs. |
| `users:read` | Resolving Slack user profiles, e.g. mapping a mentioned user to a team member. |
| `reactions:read` / `reactions:write` | Reading and adding reactions. Not used by the current handlers. |
| `files:read` / `files:write` | Reading attachments and `thread.postFile()`. Not used by the current handlers. |
| `assistant:write` | Slack's assistant pane and native tool-timeline updates. Not used by the current handlers. |

Note: `users:read.email` is **not** granted. The meeting branch (B7) needs attendee emails, so
it will need that scope added and the app reinstalled.

The bot answers **only** when mentioned: `onMention` subscribes the thread and runs the
agent, and `onMessage` runs the agent only in a thread that is already subscribed. A message
in a non-subscribed thread never reaches the agent — asserted in `src/handlers.test.ts`.

## One-time setup (manual — requires a real CopilotKit + Slack account)

This part can't be scripted by a coding agent — it needs a human with dashboard/OAuth access.
Provisioning is **dashboard-first**: create the Channel in Intelligence *before* the Slack app,
so the setup wizard generates a manifest with the correct bot scopes.

1. Sign in at `intelligence.copilotkit.ai` → **Projects → Create project**. One project per
   listener process — two listeners declaring the same Channel race per delivery and the
   loser silently gets nothing.
2. **Channels → Create channel** → display name `Mytro`, confirm the generated code is
   `mytro`, select **Slack**, continue.
3. Wizard → **Create app**. It opens Slack with the generated manifest (17 bot scopes — the
   wizard picks these; nothing to hand-configure). If the link doesn't populate it, use
   **Copy manifest** and paste into Slack's manifest editor. Pick the workspace, review
   scopes, **Create and Install**, **Allow**.
4. Slack app settings → **OAuth & Permissions → Reinstall to Workspace → Allow**. The token
   from the app-creation modal can lack permissions; reinstalling grants the full set.
5. Copy **OAuth & Permissions → Bot User OAuth Token** (`xoxb-…`) — *not* the creation-modal
   token — into the wizard's Bot token field. Copy **Basic Information → App Credentials →
   Signing Secret** into Signing secret. Continue → **Create channel**. Expect
   **Platform setup: Setup complete** and **Waiting for runtime**.
6. `npm run channel:login`, then
   `npx --yes copilotkit@latest project select --project <your-slug> --json`. This writes
   `.copilotkit/project.json` and provisions `CPK_INTELLIGENCE_API_KEY` into the root `.env`.
   Then `npm run channel:add` to declare the Channel in `.copilotkit/channels.json`; without
   it the CLI reports `declared: false` and `no_channels_declared`. The CopilotKit CLI
   resolves `.copilotkit/` from its working directory, so every `channel:*` script runs from
   the repo root — that is where both JSON files live.
7. `cp ../.env.example ../.env` if `.env` doesn't exist yet (before step 6, never after —
   don't overwrite provisioned values). Set `INTELLIGENCE_API_KEY` to the same value as
   `CPK_INTELLIGENCE_API_KEY` (keep both — the CLI provisions one name, `server.ts` reads
   the other). Set `CHANNEL_CODE=mytro`, `LOG_LEVEL=debug`,
   `AGENT_URL=http://localhost:8000/agent`.
8. `npm run doctor` — must exit `0` before continuing. It catches the failure modes below
   locally; it cannot check that `CHANNEL_CODE` matches the dashboard value.
9. `npm run start` — expect `Channel "mytro" online — listening on :3000`. Confirm with
   `npm run channel:status` (expect `overall: online`).
10. `/invite @Mytro` in a Slack channel. Start a new message, type `@mytro`, and **select
    the autocomplete result** — a plain-text `@mytro` never triggers `app_mention`. Send
    `@mytro hello` and expect `echo: hello` in the reply thread (needs `agent/` running,
    e.g. `uvicorn agent.main:app`). This reply, not `online` alone, is A1's real proof of
    life — `online` only proves the gateway connected.

### Failure modes (all silent by default)

| Symptom | Cause | Fix |
|---|---|---|
| `npm run doctor` errors on `INTELLIGENCE_API_KEY` | CLI wrote `CPK_INTELLIGENCE_API_KEY`, `server.ts` reads `INTELLIGENCE_API_KEY` | copy the value, keep both keys |
| Dashboard stuck on **Waiting for runtime** | `CHANNEL_CODE` doesn't match the dashboard code, or listener never started | run `npm run doctor`, compare printed `CHANNEL_CODE` to the dashboard |
| Dashboard shows **setup_required**, listener exits with `Channel is not online` | Slack app/channel provisioning unfinished | finish steps 3–5 above |
| Listener stays `online`, bot never replies | Bot not invited to the channel — Slack emits no `app_mention` at all in that case | `/invite @Mytro` |
| Agent runs, dashboard says `Provider delivery completed`, Slack shows nothing | The agent emitted no `TEXT_MESSAGE_*` events — a state-only reply renders as an empty message | stream the reply (see the section above) |
| Bot never replies even when invited | Sent a plain-text `@mytro` instead of a resolved mention | retype and select the autocomplete result |
| Nothing in the logs at all | `channel "<name>" requires setup` logs at `warn`; default log level is `error` | set `LOG_LEVEL=debug` |

## Run locally

```
npm install
npm run dev      # requires ../.env populated (steps above) and agent/ running
```

## Known constraints (managed Slack Channels)

- No Socket Mode, no tunnel/ngrok — CopilotKit hosts the endpoint.
- **No slash commands** — all interaction must be via `@mention`.
- `onMention` subscribes a thread; `onMessage` only replies in already-subscribed threads.
