import { test } from "node:test";
import assert from "node:assert/strict";
import {
  meetingConfirmation,
  meetingConfirmationParameters,
} from "./meeting-confirmation";
import { renderToSlack } from "./slack-preview";
import { MEETING_CONFIRMATION_STUB } from "./stubs";

/** Every mrkdwn string in the rendered blocks, flattened. */
function allText(blocks: unknown[]): string[] {
  const texts: string[] = [];
  const walk = (value: unknown) => {
    if (Array.isArray(value)) return value.forEach(walk);
    if (typeof value !== "object" || value === null) return;
    for (const [key, child] of Object.entries(value)) {
      if (key === "text" && typeof child === "string") texts.push(child);
      else walk(child);
    }
  };
  walk(blocks);
  return texts;
}

test("the parameters schema accepts the frozen payload and rejects a missing Meet link", () => {
  assert.doesNotThrow(() => meetingConfirmationParameters.parse(MEETING_CONFIRMATION_STUB));
  const { meetUrl: _dropped, ...withoutMeetUrl } = MEETING_CONFIRMATION_STUB;
  assert.throws(() => meetingConfirmationParameters.parse(withoutMeetUrl));
});

test("the confirmation leads with the meeting title as a header", async () => {
  const { blocks } = await renderToSlack(meetingConfirmation, MEETING_CONFIRMATION_STUB);

  assert.equal(blocks[0]?.type, "header");
  assert.equal(
    (blocks[0] as { text: { text: string } }).text.text,
    MEETING_CONFIRMATION_STUB.title,
  );
});

test("the booked slot renders in the event's own timezone", async () => {
  const { blocks } = await renderToSlack(meetingConfirmation, MEETING_CONFIRMATION_STUB);
  const when = allText(blocks).find((text) => text.startsWith("*When*"));

  assert.ok(when, "no *When* field rendered");
  // 14:00 +01:00 in Europe/London is 14:00 local — the card must not shift it to UTC.
  assert.ok(when.includes("14:00–14:30"), when);
  assert.ok(when.includes("Wed 16 Sept"), when);
  assert.ok(when.includes(MEETING_CONFIRMATION_STUB.timezone), when);
});

test("the same slot renders in local time for a different timezone", async () => {
  const { blocks } = await renderToSlack(meetingConfirmation, {
    ...MEETING_CONFIRMATION_STUB,
    timezone: "America/New_York",
  });
  const when = allText(blocks).find((text) => text.startsWith("*When*"));

  assert.ok(when?.includes("09:00–09:30"), when);
});

test("the Meet link renders as a Slack link", async () => {
  const { blocks } = await renderToSlack(meetingConfirmation, MEETING_CONFIRMATION_STUB);

  assert.ok(
    allText(blocks).some((text) =>
      text.includes(`<${MEETING_CONFIRMATION_STUB.meetUrl}|Google Meet>`),
    ),
    JSON.stringify(blocks),
  );
});

test("every attendee appears by name, with their email in the context line", async () => {
  const { blocks } = await renderToSlack(meetingConfirmation, MEETING_CONFIRMATION_STUB);
  const texts = allText(blocks);

  for (const attendee of MEETING_CONFIRMATION_STUB.attendees) {
    assert.ok(
      texts.some((text) => text.includes(attendee.name)),
      `missing ${attendee.name}`,
    );
    assert.ok(
      texts.some((text) => text.includes(attendee.email)),
      `missing ${attendee.email}`,
    );
  }
});
