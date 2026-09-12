/**
 * CopilotKit Channels entry point — Slack surface only. Business logic lives
 * in the Python LangGraph agent (see /agent), reached over AG-UI via
 * AGENT_URL. This file intentionally does not implement createChannel yet.
 *
 * TODO(A, F1): fork apps/channel from CopilotKit/agents-everywhere-starter-kit,
 * provision the managed Channel, and replace this stub with the real
 * createChannel({ name: CHANNEL_CODE, identifyUser: "platform", agent,
 * components }) wiring — see PLAN.md and AGENTS.md for the target shape.
 * `agent` should be an AG-UI HttpAgent pointed at AGENT_URL, not the starter
 * kit's BuiltInAgent (our agent runs as a separate Python process).
 */

export const AGENT_URL = process.env.AGENT_URL ?? "http://localhost:8000";
