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

This part can't be scripted by a coding agent — it needs a human with dashboard/OAuth access:

1. Sign up for CopilotKit Intelligence, create a project, copy the API key
   (`cpk-{projectId}_...`) into the root `.env` as `INTELLIGENCE_API_KEY`.
2. Create a Slack app in your workspace (or use the CopilotKit CLI to do it):
   `npx copilotkit channels add --name <code> --display-name "<name>" --adapter slack --json`
3. Set the Bot User OAuth Token and Signing Secret as instructed by the CLI output.
4. Put the resulting Channel Code into `.env` as `CHANNEL_CODE`.
5. Run `npm run channel:status` (or `copilotkit channels status`) until it reports `online`.
6. Invite the bot to a channel (`/invite @yourbot`) and `@mention` it.

## Run locally

```
npm install
npm run dev      # requires ../.env populated (steps above) and agent/ running
```

## Known constraints (managed Slack Channels)

- No Socket Mode, no tunnel/ngrok — CopilotKit hosts the endpoint.
- **No slash commands** — all interaction must be via `@mention`.
- `onMention` subscribes a thread; `onMessage` only replies in already-subscribed threads.
