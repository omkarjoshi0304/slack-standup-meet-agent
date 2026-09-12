import { AbstractAgent, HttpAgent } from "@ag-ui/client";
import type { BaseEvent, RunAgentInput } from "@ag-ui/core";
import { Observable, type Subscription } from "rxjs";
import { required } from "./env";

type ChannelAgentFactory = (threadId: string) => AbstractAgent;

function makeAgent(threadId: string): AbstractAgent {
  const agent = new HttpAgent({ url: required("AGENT_URL") });
  agent.threadId = threadId;
  return agent;
}

/**
 * Channel-only facade that keeps AG-UI transcript/state on the outer agent while
 * delegating each low-level run to a fresh inner agent instance.
 *
 * Channels may re-enter the same turn after tool results as soon as the previous
 * observable completes, so a fresh inner agent per run avoids reentrancy issues
 * in agent implementations that keep private per-run state (e.g. an abort
 * controller cleared asynchronously). Adapted from the agents-everywhere-starter-kit
 * reference pattern.
 */
export class ChannelRunAgent extends AbstractAgent {
  private activeInner: AbstractAgent | undefined;

  constructor(
    private agentFactory: ChannelAgentFactory = makeAgent,
    threadId?: string,
  ) {
    super({ threadId });
  }

  override run(input: RunAgentInput): Observable<BaseEvent> {
    return new Observable<BaseEvent>((subscriber) => {
      let inner: AbstractAgent | undefined;
      let subscription: Subscription | undefined;

      const release = () => {
        if (this.activeInner === inner) {
          this.activeInner = undefined;
        }
      };

      try {
        inner = this.agentFactory(input.threadId);
        inner.threadId = input.threadId;
        this.activeInner = inner;
        subscription = inner.run(input).subscribe({
          next: (event) => {
            subscriber.next(event);
          },
          error: (error) => {
            release();
            subscriber.error(error);
          },
          complete: () => {
            release();
            subscriber.complete();
          },
        });
      } catch (error) {
        release();
        subscriber.error(error);
      }

      return () => {
        subscription?.unsubscribe();
        inner?.abortRun();
        release();
      };
    });
  }

  override abortRun() {
    this.activeInner?.abortRun();
    super.abortRun();
  }

  override clone(): ChannelRunAgent {
    const cloned = super.clone() as ChannelRunAgent;
    cloned.agentFactory = this.agentFactory;
    cloned.activeInner = undefined;
    return cloned;
  }
}

export function makeChannelAgent(threadId: string) {
  return new ChannelRunAgent(makeAgent, threadId);
}
