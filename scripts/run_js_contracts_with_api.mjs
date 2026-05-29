import { spawn } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const API_URL = process.env.FF_API_BASE_URL || "http://127.0.0.1:8000";
const HEALTH_URL = `${API_URL.replace(/\/$/, "")}/health`;
const PYTHON = process.env.PYTHON || "python";

async function waitForApi(timeoutMs = 15000) {
  const startedAt = Date.now();
  let lastError = null;

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const res = await fetch(HEALTH_URL);
      if (res.ok) return true;
    } catch (error) {
      lastError = error;
    }

    await sleep(350);
  }

  throw new Error(`API did not become ready at ${HEALTH_URL}: ${lastError?.message || "timeout"}`);
}

function spawnApi() {
  return spawn(
    PYTHON,
    ["-m", "uvicorn", "asgi:app", "--app-dir", "apps/api", "--host", "127.0.0.1", "--port", "8000"],
    {
      stdio: ["ignore", "inherit", "inherit"],
      env: {
        ...process.env,
        PYTHONPATH: process.env.PYTHONPATH || "apps/api",
      },
    }
  );
}

function runContracts() {
  return new Promise((resolve) => {
    const child = spawn("node", ["--test", "--test-concurrency=1", "tests/js/contracts.test.js"], {
      stdio: "inherit",
      env: {
        ...process.env,
        FF_API_BASE_URL: API_URL,
      },
    });

    child.on("exit", (code) => resolve(code ?? 1));
  });
}

const api = spawnApi();

let exitCode = 1;

try {
  await waitForApi();
  exitCode = await runContracts();
} catch (error) {
  console.error(error);
  exitCode = 1;
} finally {
  api.kill("SIGTERM");
}

process.exit(exitCode);
