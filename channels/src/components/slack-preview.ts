import type { ChannelComponentRenderContext } from "@copilotkit/channels";
import { renderToIR, type Renderable } from "@copilotkit/channels-ui";
import { renderSlackMessage } from "@copilotkit/channels-slack";

/**
 * Render a card definition all the way to Slack Block Kit JSON locally.
 *
 * The hosted CopilotKit pipeline normally does this on delivery, so this is the
 * only way to check a card's real Slack output without a working live delivery
 * (A1 is blocked on exactly that). Used by the card tests and by
 * `npm run cards:preview`, whose JSON can be pasted into Slack's Block Kit
 * Builder for a visual check.
 */
export async function renderToSlack<Props>(
  component: {
    render(
      props: Props,
      context: ChannelComponentRenderContext,
    ): Renderable | Promise<Renderable>;
  },
  props: Props,
) {
  const ui = await component.render(props, {
    platform: "slack",
    signal: new AbortController().signal,
  });
  return renderSlackMessage(renderToIR(ui));
}
