# Slack Standup + Meeting Agent

A Slack-native agent for engineering teams, built for the **Agents, Everywhere** hackathon.

Two capabilities, both living inside Slack:

- **`@dailyagent`** — replaces the manual daily standup by summarizing each engineer's
  current-sprint Jira work on a schedule and posting a threaded digest.
- **`@meetagent`** — schedules meetings from chat by reading attendees' Google Calendars,
  finding a common slot, and creating a Google Meet on approval.

See [PLAN.md](./PLAN.md) for the full system design.

## Status

Early planning. Repo initialized with the design doc.

## Stack (planned)

Slack Bolt · CopilotKit · Auth0 (Token Vault) · Jira REST · Google Calendar API ·
OpenAI Agents SDK / Claude
