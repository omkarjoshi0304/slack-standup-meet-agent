import { createChannel } from "@copilotkit/channels";
import { makeChannelAgent } from "./agent";
import { required } from "./env";
import { handleMention, handleMessage } from "./handlers";
import { meetingConfirmation } from "./components/meeting-confirmation";
import { standupDigest } from "./components/standup-digest";

export const channel = createChannel({
  // Must equal the Channel Code provisioned via `copilotkit channels add`.
  name: required("CHANNEL_CODE"),
  identifyUser: "platform",
  agent: makeChannelAgent,
  components: [standupDigest, meetingConfirmation],
});

channel.onMention(handleMention);
channel.onMessage(handleMessage);
