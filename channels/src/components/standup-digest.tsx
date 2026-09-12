import { defineChannelComponent } from "@copilotkit/channels";
import { Header, Message, Section } from "@copilotkit/channels-ui";
import { z } from "zod";

/**
 * Frozen card contract for the standup digest (A3). Epic B's standup branch (B5)
 * produces this payload; until then it is rendered and tested against stubs.
 */
export const standupDigestParameters = z.object({
  title: z.string().describe("Heading for the digest, e.g. the date or sprint name."),
  people: z
    .array(
      z.object({
        name: z.string().describe("Display name of the team member."),
        status: z
          .enum(["done", "in_progress", "blocked"])
          .describe("Overall state of this person's sprint work."),
        summary: z.string().describe("One-line summary of what they did and what is next."),
        jiraLinks: z
          .array(
            z.object({
              key: z.string().describe("Jira issue key, e.g. MYT-42."),
              url: z.string().describe("Browse URL for the issue."),
            }),
          )
          .describe("Jira issues backing the summary."),
      }),
    )
    .describe("One entry per team member, in reporting order."),
});

export type StandupDigestPayload = z.infer<typeof standupDigestParameters>;
export type StandupPerson = StandupDigestPayload["people"][number];

const STATUS_EMOJI: Record<StandupPerson["status"], string> = {
  done: "✅",
  in_progress: "🟡",
  blocked: "❌",
};

function jiraMarkdown(links: StandupPerson["jiraLinks"]): string {
  return links.map((link) => `[${link.key}](${link.url})`).join(" · ");
}

export const standupDigest = defineChannelComponent({
  name: "standup_digest",
  description:
    "Render the daily standup digest: one line per team member with their status, summary, and Jira issues.",
  parameters: standupDigestParameters,
  render: ({ title, people }) => (
    <Message fallbackText={`Standup digest: ${title}`}>
      <Header>{title}</Header>
      {people.map((person) => (
        <Section key={person.name}>
          {STATUS_EMOJI[person.status]} **{person.name}** — {person.summary}
          {person.jiraLinks.length > 0 ? `\n${jiraMarkdown(person.jiraLinks)}` : ""}
        </Section>
      ))}
    </Message>
  ),
});
