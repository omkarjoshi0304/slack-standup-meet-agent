/**
 * Thread handlers wired into the Channel in `channel.ts`.
 *
 * They live apart from `createChannel` so they can be exercised directly against
 * a fake thread — importing `channel.ts` would build a real Channel and demand
 * live credentials.
 */

/** The slice of the Channels thread API these handlers use. */
export type HandlerThread = {
  subscribe(): Promise<unknown>;
  isSubscribed(): Promise<boolean>;
  runAgent(): Promise<unknown>;
};

/**
 * A mention subscribes the thread, so the agent follows along afterward instead
 * of needing to be @-mentioned on every turn.
 */
export async function handleMention({ thread }: { thread: HandlerThread }) {
  await thread.subscribe();
  await thread.runAgent();
}

/**
 * Non-mentioned turns only reach `onMessage` — gate on subscription so the agent
 * stays silent in every channel it is invited to until someone mentions it (A5).
 */
export async function handleMessage({ thread }: { thread: HandlerThread }) {
  if (await thread.isSubscribed()) {
    await thread.runAgent();
  }
}
