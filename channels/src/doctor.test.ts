import { test } from "node:test";
import assert from "node:assert/strict";
import { checkEnv } from "./doctor";

const GOOD_ENV = {
  INTELLIGENCE_API_KEY: "cpk-proj123_abcdef",
  CHANNEL_CODE: "mytro",
  AGENT_URL: "http://localhost:8000/agent",
  LOG_LEVEL: "debug",
};

test("checkEnv reports no errors for a fully correct env", () => {
  const problems = checkEnv({ ...GOOD_ENV });
  assert.deepEqual(
    problems.filter((p) => p.level === "error"),
    [],
  );
});

test("checkEnv flags the CPK_INTELLIGENCE_API_KEY naming trap", () => {
  const problems = checkEnv({
    ...GOOD_ENV,
    INTELLIGENCE_API_KEY: undefined,
    CPK_INTELLIGENCE_API_KEY: "cpk-proj123_abcdef",
  });
  assert.ok(
    problems.some(
      (p) => p.level === "error" && p.message.includes("CPK_INTELLIGENCE_API_KEY"),
    ),
  );
});

test("checkEnv flags INTELLIGENCE_API_KEY missing entirely", () => {
  const problems = checkEnv({ ...GOOD_ENV, INTELLIGENCE_API_KEY: undefined });
  assert.ok(
    problems.some((p) => p.level === "error" && p.message.includes("INTELLIGENCE_API_KEY")),
  );
});

test("checkEnv flags INTELLIGENCE_API_KEY with the wrong format", () => {
  const problems = checkEnv({ ...GOOD_ENV, INTELLIGENCE_API_KEY: "not-the-right-shape" });
  assert.ok(
    problems.some(
      (p) => p.level === "error" && p.message.includes("INTELLIGENCE_API_KEY") && p.message.includes("format"),
    ),
  );
});

test("checkEnv flags CHANNEL_CODE missing", () => {
  const problems = checkEnv({ ...GOOD_ENV, CHANNEL_CODE: undefined });
  assert.ok(problems.some((p) => p.level === "error" && p.message.includes("CHANNEL_CODE")));
});

test("checkEnv flags CHANNEL_CODE with an invalid shape", () => {
  const problems = checkEnv({ ...GOOD_ENV, CHANNEL_CODE: "My_Channel!" });
  assert.ok(
    problems.some(
      (p) => p.level === "error" && p.message.includes("CHANNEL_CODE") && p.message.includes("Waiting for runtime"),
    ),
  );
});

test("checkEnv flags any env value starting with xapp-", () => {
  const problems = checkEnv({ ...GOOD_ENV, SLACK_APP_TOKEN: "xapp-1-abc" });
  assert.ok(
    problems.some((p) => p.level === "error" && p.message.includes("xapp-")),
  );
});

test("checkEnv flags AGENT_URL missing", () => {
  const problems = checkEnv({ ...GOOD_ENV, AGENT_URL: undefined });
  assert.ok(problems.some((p) => p.level === "error" && p.message.includes("AGENT_URL")));
});

test("checkEnv flags AGENT_URL not ending in /agent", () => {
  const problems = checkEnv({ ...GOOD_ENV, AGENT_URL: "http://localhost:8000" });
  assert.ok(problems.some((p) => p.level === "error" && p.message.includes("AGENT_URL")));
});

test("checkEnv warns when LOG_LEVEL is unset", () => {
  const problems = checkEnv({ ...GOOD_ENV, LOG_LEVEL: undefined });
  assert.ok(
    problems.some((p) => p.level === "warn" && p.message.includes("LOG_LEVEL")),
  );
});

test("checkEnv reports every error rule against an empty env", () => {
  const problems = checkEnv({});
  const errors = problems.filter((p) => p.level === "error");
  // CHANNEL_CODE missing, INTELLIGENCE_API_KEY missing, AGENT_URL missing (3 rules;
  // the naming-trap and format/shape rules don't fire when the var is absent).
  assert.equal(errors.length, 3);
});
