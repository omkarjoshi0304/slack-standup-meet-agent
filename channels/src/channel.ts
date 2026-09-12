import { createChannel } from "@copilotkit/channels";
import { makeChannelAgent } from "./agent";
import { required } from "./env";

// Standup digest and meeting confirmation cards land in tasks A3/A4 as
// defineChannelComponent entries, registered here via `components: [...]`.
export const channel = createChannel({
  // Must equal the Channel Code provisioned via `copilotkit channels add`.
  name: required("CHANNEL_CODE"),
  identifyUser: "platform",
  agent: makeChannelAgent,
});

// A mention subscribes the thread, so the agent follows along afterward
// instead of needing to be @-mentioned on every turn.
channel.onMention(async ({ thread }) => {
  await thread.subscribe();
  await thread.runAgent();
});

// Non-mentioned turns only reach onMessage — gate on subscription so the
// agent doesn't answer every message in every channel it's invited to.
channel.onMessage(async ({ thread }) => {
  if (await thread.isSubscribed()) {
    await thread.runAgent();
  }
});
