// Stop hook: reports the previous worker's errors, then starts a new worker and exits.
// The worker runs detached because extraction and git sync take longer than a hook
// should block, and an async hook may be killed when the session ends.
import { spawn } from "node:child_process";
import { existsSync, readFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

// The worker's own `claude -p` call runs with --safe-mode, so it loads no plugins.
// This guard stops recursion even if that ever changes.
if (process.env.PREFERENCE_TRACKER_CHILD) process.exit(0);

const dataDir = process.env.CLAUDE_PLUGIN_DATA;
if (!dataDir) {
  console.error("preference-tracker: CLAUDE_PLUGIN_DATA is not set");
  process.exit(1);
}

const input = JSON.parse(readFileSync(0, "utf8"));

const errorFile = join(dataDir, "last-error.txt");
if (existsSync(errorFile)) {
  const message = readFileSync(errorFile, "utf8").trim();
  rmSync(errorFile);
  console.log(JSON.stringify({ systemMessage: `preference-tracker failed:\n${message}` }));
}

const workerPath = fileURLToPath(new URL("./worker.mjs", import.meta.url));
spawn(process.execPath, [workerPath, input.session_id, input.transcript_path], {
  detached: true,
  stdio: "ignore",
  windowsHide: true,
}).unref();
