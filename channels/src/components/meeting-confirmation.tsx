import { defineChannelComponent } from "@copilotkit/channels";
import { Context, Field, Fields, Header, Message, Section } from "@copilotkit/channels-ui";
import { z } from "zod";

/**
 * Frozen card contract for the meeting confirmation (A4). Epic B's meeting branch
 * (B7) produces this payload after it creates the calendar event; until then it is
 * rendered and tested against stubs.
 */
export const meetingConfirmationParameters = z.object({
  title: z.string().describe("Calendar event title."),
  startIso: z.string().describe("Event start as an ISO-8601 timestamp with offset."),
  endIso: z.string().describe("Event end as an ISO-8601 timestamp with offset."),
  timezone: z.string().describe("IANA timezone the event was scheduled in, e.g. Europe/London."),
  attendees: z
    .array(
      z.object({
        name: z.string().describe("Attendee display name."),
        email: z.string().describe("Attendee email address, as invited."),
      }),
    )
    .describe("Everyone invited to the event, organizer included."),
  meetUrl: z.string().describe("Google Meet join URL for the event."),
});

export type MeetingConfirmationPayload = z.infer<typeof meetingConfirmationParameters>;

/**
 * Render the booked slot in the event's own timezone, so the card reads the same
 * as the calendar entry regardless of where the Slack reader is.
 */
function formatSlot(startIso: string, endIso: string, timezone: string): string {
  const start = new Date(startIso);
  const end = new Date(endIso);
  const day = new Intl.DateTimeFormat("en-GB", {
    timeZone: timezone,
    weekday: "short",
    day: "numeric",
    month: "short",
  }).format(start);
  const time = new Intl.DateTimeFormat("en-GB", {
    timeZone: timezone,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  return `${day}, ${time.format(start)}–${time.format(end)} (${timezone})`;
}

export const meetingConfirmation = defineChannelComponent({
  name: "meeting_confirmation",
  description:
    "Confirm a scheduled meeting: title, the booked slot, the attendee list, and the Google Meet link.",
  parameters: meetingConfirmationParameters,
  render: ({ title, startIso, endIso, timezone, attendees, meetUrl }) => (
    <Message fallbackText={`Meeting scheduled: ${title}`}>
      <Header>{title}</Header>
      <Fields>
        <Field label="When">{formatSlot(startIso, endIso, timezone)}</Field>
        <Field label="Join">[Google Meet]({meetUrl})</Field>
      </Fields>
      <Section>
        **Attendees** — {attendees.map((attendee) => attendee.name).join(", ")}
      </Section>
      <Context>{attendees.map((attendee) => attendee.email).join(" · ")}</Context>
    </Message>
  ),
});
