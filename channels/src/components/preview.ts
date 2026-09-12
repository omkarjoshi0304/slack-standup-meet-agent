/**
 * Print both cards as Slack Block Kit JSON (`npm run cards:preview`).
 *
 * Paste either object into https://app.slack.com/block-kit-builder for a visual
 * check. This is the card-rendering proof that does not depend on A1's blocked
 * live delivery.
 */
import { meetingConfirmation } from "./meeting-confirmation";
import { renderToSlack } from "./slack-preview";
import { standupDigest } from "./standup-digest";
import { MEETING_CONFIRMATION_STUB, STANDUP_DIGEST_STUB } from "./stubs";

for (const [component, props] of [
  [standupDigest, STANDUP_DIGEST_STUB],
  [meetingConfirmation, MEETING_CONFIRMATION_STUB],
] as const) {
  const { blocks, accent } = await renderToSlack(component, props);
  console.log(`\n// ${component.name}${accent ? ` (accent ${accent})` : ""}`);
  console.log(JSON.stringify({ blocks }, null, 2));
}
