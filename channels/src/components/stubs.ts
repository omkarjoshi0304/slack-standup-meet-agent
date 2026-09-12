import type { MeetingConfirmationPayload } from "./meeting-confirmation";
import type { StandupDigestPayload } from "./standup-digest";

/**
 * Stub card payloads standing in for Epic B's real output (B5 for the digest,
 * B7 for the meeting) until those branches land. Shared by the card tests and
 * `npm run cards:preview` so the visual check and the assertions describe the
 * same card.
 */
export const STANDUP_DIGEST_STUB: StandupDigestPayload = {
  title: "Standup — Tue 15 Sep",
  people: [
    {
      name: "Ada Lovelace",
      status: "done",
      summary: "Finished the Jira OAuth exchange; picking up sprint cleanup next.",
      jiraLinks: [
        { key: "MYT-12", url: "https://mytro.atlassian.net/browse/MYT-12" },
        { key: "MYT-14", url: "https://mytro.atlassian.net/browse/MYT-14" },
      ],
    },
    {
      name: "Grace Hopper",
      status: "in_progress",
      summary: "Halfway through the freebusy merge; expects to finish tomorrow.",
      jiraLinks: [{ key: "MYT-21", url: "https://mytro.atlassian.net/browse/MYT-21" }],
    },
    {
      name: "Alan Turing",
      status: "blocked",
      summary: "Blocked on Google Calendar scopes — needs admin approval.",
      jiraLinks: [{ key: "MYT-30", url: "https://mytro.atlassian.net/browse/MYT-30" }],
    },
  ],
};

export const MEETING_CONFIRMATION_STUB: MeetingConfirmationPayload = {
  title: "Sprint planning",
  startIso: "2026-09-16T14:00:00+01:00",
  endIso: "2026-09-16T14:30:00+01:00",
  timezone: "Europe/London",
  attendees: [
    { name: "Ada Lovelace", email: "ada@mytro.dev" },
    { name: "Grace Hopper", email: "grace@mytro.dev" },
  ],
  meetUrl: "https://meet.google.com/abc-defg-hij",
};
