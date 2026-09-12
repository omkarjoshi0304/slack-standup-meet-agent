import { test } from "node:test";
import assert from "node:assert/strict";
import { handleMention, handleMessage, type HandlerThread } from "./handlers";

type Calls = { subscribe: number; isSubscribed: number; runAgent: number };

function fakeThread(subscribed: boolean) {
  const calls: Calls = { subscribe: 0, isSubscribed: 0, runAgent: 0 };
  let isSubscribed = subscribed;
  const thread: HandlerThread = {
    async subscribe() {
      calls.subscribe += 1;
      isSubscribed = true;
    },
    async isSubscribed() {
      calls.isSubscribed += 1;
      return isSubscribed;
    },
    async runAgent() {
      calls.runAgent += 1;
    },
  };
  return { thread, calls };
}

test("a mention subscribes the thread and then runs the agent", async () => {
  const { thread, calls } = fakeThread(false);
  await handleMention({ thread });
  assert.equal(calls.subscribe, 1);
  assert.equal(calls.runAgent, 1);
});

test("a message in a subscribed thread runs the agent", async () => {
  const { thread, calls } = fakeThread(true);
  await handleMessage({ thread });
  assert.equal(calls.runAgent, 1);
});

test("a message in a non-subscribed thread never runs the agent", async () => {
  const { thread, calls } = fakeThread(false);
  await handleMessage({ thread });
  assert.equal(calls.isSubscribed, 1);
  assert.equal(calls.runAgent, 0);
  assert.equal(calls.subscribe, 0);
});

test("a message never subscribes a thread on its own — only a mention does", async () => {
  const { thread, calls } = fakeThread(false);
  await handleMessage({ thread });
  await handleMention({ thread });
  await handleMessage({ thread });
  assert.equal(calls.subscribe, 1);
  // Once from the mention, once from the now-subscribed follow-up message.
  assert.equal(calls.runAgent, 2);
});
