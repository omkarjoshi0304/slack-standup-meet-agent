import { test } from "node:test";
import assert from "node:assert/strict";
import { renderToSlack } from "./slack-preview";
import { standupDigest, standupDigestParameters } from "./standup-digest";
import { STANDUP_DIGEST_STUB } from "./stubs";

/** Every `section` block's mrkdwn text, in order. */
function sectionTexts(blocks: unknown[]): string[] {
  return blocks
    .filter((b): b is { type: string; text?: { text: string } } => {
      return typeof b === "object" && b !== null && (b as { type: string }).type === "section";
    })
    .map((b) => b.text?.text ?? "");
}

test("the parameters schema accepts the frozen payload and rejects an unknown status", () => {
  assert.doesNotThrow(() => standupDigestParameters.parse(STANDUP_DIGEST_STUB));
  assert.throws(() =>
    standupDigestParameters.parse({
      ...STANDUP_DIGEST_STUB,
      people: [{ ...STANDUP_DIGEST_STUB.people[0], status: "on_holiday" }],
    }),
  );
});

test("the digest renders a header and one section per person", async () => {
  const { blocks } = await renderToSlack(standupDigest, STANDUP_DIGEST_STUB);

  assert.equal(blocks[0]?.type, "header");
  assert.equal(
    (blocks[0] as { text: { text: string } }).text.text,
    STANDUP_DIGEST_STUB.title,
  );
  assert.equal(sectionTexts(blocks).length, STANDUP_DIGEST_STUB.people.length);
});

test("each person's section carries their status emoji, name, and summary", async () => {
  const { blocks } = await renderToSlack(standupDigest, STANDUP_DIGEST_STUB);
  const [done, inProgress, blocked] = sectionTexts(blocks);

  assert.ok(done.startsWith("✅"), done);
  assert.ok(inProgress.startsWith("🟡"), inProgress);
  assert.ok(blocked.startsWith("❌"), blocked);

  for (const [index, person] of STANDUP_DIGEST_STUB.people.entries()) {
    const text = sectionTexts(blocks)[index]!;
    // Slack mrkdwn bolds with single asterisks, not markdown's double.
    assert.ok(text.includes(`*${person.name}*`), text);
    assert.ok(text.includes(person.summary), text);
  }
});

test("Jira keys render as Slack links to their issue URLs", async () => {
  const { blocks } = await renderToSlack(standupDigest, STANDUP_DIGEST_STUB);
  const texts = sectionTexts(blocks);

  for (const [index, person] of STANDUP_DIGEST_STUB.people.entries()) {
    for (const link of person.jiraLinks) {
      assert.ok(texts[index]!.includes(`<${link.url}|${link.key}>`), texts[index]);
    }
  }
});

test("a person with no Jira issues renders without a trailing link line", async () => {
  const { blocks } = await renderToSlack(standupDigest, {
    title: "Standup",
    people: [
      { name: "Solo", status: "done", summary: "Nothing tracked in Jira.", jiraLinks: [] },
    ],
  });

  assert.deepEqual(sectionTexts(blocks), ["✅ *Solo* — Nothing tracked in Jira."]);
});
