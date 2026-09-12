# channels — CopilotKit Channels (Slack surface)

Thin Node layer. Forwards Slack `@mention`/thread events to the Python LangGraph agent in
`../agent` over the AG-UI protocol (`AGENT_URL`). See root `AGENTS.md` for the full
architecture.

## What's implemented (tasks F1/F2)

- `src/env.ts` — env var helpers (tested: `src/env.test.ts`).
- `src/agent.ts` — `HttpAgent` pointed at `AGENT_URL`, wrapped in a reentry-safe facade.
- `src/channel.ts` — `createChannel`, `onMention` (subscribe + run), `onMessage`
  (run only in subscribed threads). No cards yet — those are tasks A3/A4.
- `src/server.ts` — boots the CopilotKit runtime and Channel; exits non-zero if the
  Channel doesn't reach `online`.

Verified locally: `npx tsc --noEmit` passes, `npm test` passes, and `node --env-file=../.env
--import tsx src/server.ts` runs correctly up to the real-credential boundary (fails with a
clear `ChannelConfigError` on a placeholder `INTELLIGENCE_API_KEY`, as expected).

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
