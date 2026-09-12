import { test } from "node:test";
import assert from "node:assert/strict";
import { AbstractAgent, HttpAgent } from "@ag-ui/client";
import type { BaseEvent, RunAgentInput } from "@ag-ui/core";
import { Observable, Subject } from "rxjs";
import { ChannelRunAgent, makeAgent, makeChannelAgent } from "./agent";

/** Inner agent stand-in: its run stream stays open until the test closes it. */
class FakeInnerAgent extends AbstractAgent {
  events = new Subject<BaseEvent>();
  aborted = 0;
  lastInput: RunAgentInput | undefined;

  override run(input: RunAgentInput): Observable<BaseEvent> {
    this.lastInput = input;
    return this.events.asObservable();
  }

  override abortRun() {
    this.aborted += 1;
  }
}

function runInput(threadId: string): RunAgentInput {
  return {
    threadId,
    runId: `run-${threadId}`,
    state: {},
    messages: [],
    tools: [],
    context: [],
    forwardedProps: {},
  };
}

test("every run() builds a fresh inner agent", () => {
  const built: FakeInnerAgent[] = [];
  const agent = new ChannelRunAgent(() => {
    const inner = new FakeInnerAgent();
    built.push(inner);
    return inner;
  });

  const first = agent.run(runInput("t1")).subscribe();
  const second = agent.run(runInput("t2")).subscribe();

  assert.equal(built.length, 2);
  assert.notEqual(built[0], built[1]);
  first.unsubscribe();
  second.unsubscribe();
});

test("run() forwards the input's threadId to the inner agent", () => {
  let inner: FakeInnerAgent | undefined;
  const agent = new ChannelRunAgent(() => (inner = new FakeInnerAgent()));

  const sub = agent.run(runInput("thread-42")).subscribe();

  assert.equal(inner?.lastInput?.threadId, "thread-42");
  assert.equal(inner?.threadId, "thread-42");
  sub.unsubscribe();
});

test("abortRun propagates to the active inner agent", () => {
  let inner: FakeInnerAgent | undefined;
  const agent = new ChannelRunAgent(() => (inner = new FakeInnerAgent()));

  const sub = agent.run(runInput("t1")).subscribe();
  agent.abortRun();

  assert.equal(inner?.aborted, 1);
  sub.unsubscribe();
});

test("a completed run is released, so a later abortRun no longer reaches it", () => {
  let inner: FakeInnerAgent | undefined;
  const agent = new ChannelRunAgent(() => (inner = new FakeInnerAgent()));

  const sub = agent.run(runInput("t1")).subscribe();
  inner!.events.complete();
  // Completion tears the subscription down, which aborts the spent inner agent.
  const abortsAfterCompletion = inner!.aborted;
  agent.abortRun();

  assert.equal(inner?.aborted, abortsAfterCompletion);
  sub.unsubscribe();
});

test("run() surfaces a factory failure as an observable error", async () => {
  const agent = new ChannelRunAgent(() => {
    throw new Error("no agent for you");
  });

  const error = await new Promise<Error>((resolve) => {
    agent.run(runInput("t1")).subscribe({ error: resolve });
  });

  assert.match(error.message, /no agent for you/);
});

test("makeAgent builds an HttpAgent pointed at AGENT_URL", () => {
  process.env.AGENT_URL = "http://localhost:8000/agent";
  const agent = makeAgent("t1");
  assert.ok(agent instanceof HttpAgent);
  assert.equal(agent.url, "http://localhost:8000/agent");
  assert.equal(agent.threadId, "t1");
  delete process.env.AGENT_URL;
});

test("makeAgent throws when AGENT_URL is missing", () => {
  delete process.env.AGENT_URL;
  assert.throws(() => makeAgent("t1"), /AGENT_URL/);
});

test("makeChannelAgent returns a ChannelRunAgent carrying the thread id", () => {
  const agent = makeChannelAgent("t7");
  assert.ok(agent instanceof ChannelRunAgent);
  assert.equal(agent.threadId, "t7");
});
