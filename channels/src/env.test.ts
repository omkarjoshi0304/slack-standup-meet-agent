import { test } from "node:test";
import assert from "node:assert/strict";
import { required, optional } from "./env";

test("required returns the value when the env var is set", () => {
  process.env.TEST_REQUIRED_VAR = "hello";
  assert.equal(required("TEST_REQUIRED_VAR"), "hello");
  delete process.env.TEST_REQUIRED_VAR;
});

test("required throws when the env var is missing", () => {
  delete process.env.TEST_MISSING_VAR;
  assert.throws(() => required("TEST_MISSING_VAR"));
});

test("optional returns the fallback when the env var is missing", () => {
  delete process.env.TEST_MISSING_VAR;
  assert.equal(optional("TEST_MISSING_VAR", "fallback"), "fallback");
});

test("optional returns the value when the env var is set", () => {
  process.env.TEST_OPTIONAL_VAR = "value";
  assert.equal(optional("TEST_OPTIONAL_VAR", "fallback"), "value");
  delete process.env.TEST_OPTIONAL_VAR;
});
