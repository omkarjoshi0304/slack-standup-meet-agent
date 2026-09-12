/**
 * Preflight for the three documented-but-silent A1 provisioning failure modes:
 * the CPK_INTELLIGENCE_API_KEY naming trap, a Socket Mode token on the managed
 * path, and a CHANNEL_CODE typo that only surfaces later as dashboard state
 * "Waiting for runtime". Run before `npm run start` — none of this is checked
 * by the runtime itself until the first real mention arrives.
 */
export type Problem = { level: "error" | "warn"; message: string };

const CHANNEL_CODE_RE = /^[a-z][a-z0-9]*(-[a-z0-9]+)*$/;
const INTELLIGENCE_KEY_RE = /^cpk-[^_]+_/;

export function checkEnv(env: NodeJS.ProcessEnv): Problem[] {
  const problems: Problem[] = [];

  const apiKey = env.INTELLIGENCE_API_KEY;
  if (!apiKey && env.CPK_INTELLIGENCE_API_KEY) {
    problems.push({
      level: "error",
      message:
        "INTELLIGENCE_API_KEY is missing but CPK_INTELLIGENCE_API_KEY is set. " +
        "The CLI provisions CPK_INTELLIGENCE_API_KEY; server.ts reads INTELLIGENCE_API_KEY. " +
        "Copy the value across and keep both entries in .env.",
    });
  } else if (!apiKey) {
    problems.push({
      level: "error",
      message: "INTELLIGENCE_API_KEY is missing. Add it to the root .env file.",
    });
  } else if (!INTELLIGENCE_KEY_RE.test(apiKey)) {
    problems.push({
      level: "error",
      message:
        "INTELLIGENCE_API_KEY has wrong format. Expected cpk-{projectId}_... (see .env.example).",
    });
  }

  const channelCode = env.CHANNEL_CODE;
  if (!channelCode) {
    problems.push({
      level: "error",
      message: "CHANNEL_CODE is missing. Add it to the root .env file.",
    });
  } else if (!CHANNEL_CODE_RE.test(channelCode)) {
    problems.push({
      level: "error",
      message:
        `CHANNEL_CODE "${channelCode}" has invalid shape (lowercase letters/digits, ` +
        "single hyphens, must start with a letter). A mismatch fails late as dashboard " +
        'state "Waiting for runtime".',
    });
  }

  for (const [key, value] of Object.entries(env)) {
    if (typeof value === "string" && value.startsWith("xapp-")) {
      problems.push({
        level: "error",
        message:
          `${key} starts with xapp- (a Socket Mode app-level token). The managed Channels ` +
          "path rejects it deliberately — remove it.",
      });
    }
  }

  const agentUrl = env.AGENT_URL;
  if (!agentUrl) {
    problems.push({
      level: "error",
      message:
        "AGENT_URL is missing. agent.ts resolves it lazily inside makeAgent, so the " +
        "process boots fine and only fails on the first real mention.",
    });
  } else if (!agentUrl.endsWith("/agent")) {
    problems.push({
      level: "error",
      message: `AGENT_URL "${agentUrl}" must end in /agent.`,
    });
  }

  if (!env.LOG_LEVEL) {
    problems.push({
      level: "warn",
      message:
        'LOG_LEVEL is unset. The diagnostic channel "<name>" requires setup logs at warn, ' +
        "but the runtime logger defaults to error — set LOG_LEVEL=debug to see it.",
    });
  }

  return problems;
}

async function main() {
  const problems = checkEnv(process.env);
  console.log(`CHANNEL_CODE: ${process.env.CHANNEL_CODE ?? "(unset)"}`);

  for (const problem of problems) {
    const prefix = problem.level === "error" ? "ERROR" : "WARN";
    console.log(`[${prefix}] ${problem.message}`);
  }

  const hasErrors = problems.some((p) => p.level === "error");
  if (hasErrors) {
    console.log(`\ndoctor found ${problems.filter((p) => p.level === "error").length} error(s).`);
    process.exit(1);
  }
  console.log("\ndoctor: no errors.");
  process.exit(0);
}

if (process.argv[1] && import.meta.url === `file://${process.argv[1]}`) {
  await main();
}
