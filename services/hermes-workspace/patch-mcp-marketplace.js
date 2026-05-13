const fs = require("node:fs");
const path = require("node:path");

const roots = [
  "/opt/hermes-workspace/dist/server/assets",
  "/opt/hermes-workspace/dist/client/assets",
];

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walk(full));
    } else if (entry.isFile() && entry.name.endsWith(".js")) {
      out.push(full);
    }
  }
  return out;
}

const before = `    const transport = typeof raw.transportType === "string" ? raw.transportType : typeof raw.transport === "string" ? raw.transport : typeof raw.url === "string" ? "http" : "stdio";
    const rawTemplate = {
      name,
      transportType: transport,
      command: typeof raw.command === "string" ? raw.command : void 0,
      args: Array.isArray(raw.args) ? raw.args : void 0,
      env: raw.env && typeof raw.env === "object" && !Array.isArray(raw.env) ? raw.env : void 0,
      url: typeof raw.url === "string" ? raw.url : void 0
    };`;

const after = `    const smitheryUrl = typeof raw.url === "string" ? raw.url : qualified ? \`https://server.smithery.ai/\${qualified}\` : void 0;
    const transport = typeof raw.transportType === "string" ? raw.transportType : typeof raw.transport === "string" ? raw.transport : typeof smitheryUrl === "string" ? "http" : "stdio";
    const rawTemplate = {
      name,
      transportType: transport,
      command: typeof raw.command === "string" ? raw.command : void 0,
      args: Array.isArray(raw.args) ? raw.args : void 0,
      env: raw.env && typeof raw.env === "object" && !Array.isArray(raw.env) ? raw.env : void 0,
      url: smitheryUrl,
      authType: rawAny.remote === true ? "oauth" : void 0
    };`;

let patched = 0;
let chatModePatched = 0;
let localSessionStorePatched = 0;
for (const root of roots) {
for (const file of walk(root)) {
  const text = fs.readFileSync(file, "utf8");
  let next = text;

  if (
    next.includes('const REGISTRY_URL = "https://registry.smithery.ai/servers";') &&
    !next.includes("const smitheryUrl =")
  ) {
    const expandedRegistry = next.replace(
      'const REGISTRY_URL = "https://registry.smithery.ai/servers";',
      'const REGISTRY_URL = "https://registry.smithery.ai/servers?pageSize=100";',
    );
    if (expandedRegistry === next) {
      throw new Error(`MCP marketplace registry URL patch target was not found in ${file}`);
    }
    if (!next.includes(before)) {
      throw new Error(`MCP marketplace patch target was not found in ${file}`);
    }
    next = expandedRegistry.replace(before, after);
    patched += 1;
    console.log(`patched MCP marketplace parser in ${file}`);
  }

  const readableModeBefore = 'if (capabilities2.sessions) return "enhanced-claude";';
  if (next.includes(readableModeBefore)) {
    next = next.replace(
      readableModeBefore,
      'if (capabilities2.enhancedChat) return "enhanced-claude";',
    );
    chatModePatched += 1;
    console.log(`patched readable chat mode detection in ${file}`);
  }

  const minifiedModePattern =
    /if\(([$_\w]+)\.sessions\)return"enhanced-claude";if\(\1\.chatCompletions\|\|\1\.health\)return"portable";/g;
  const minifiedModeNext = next.replace(
    minifiedModePattern,
    'if($1.enhancedChat)return"enhanced-claude";if($1.chatCompletions||$1.health)return"portable";',
  );
  if (minifiedModeNext !== next) {
    next = minifiedModeNext;
    chatModePatched += 1;
    console.log(`patched minified chat mode detection in ${file}`);
  }

  const ternaryModePattern =
    /return ([$_\w]+)\.sessions\?"enhanced-claude":\1\.chatCompletions\|\|\1\.health\?"portable":"disconnected"/g;
  const ternaryModeNext = next.replace(
    ternaryModePattern,
    'return $1.enhancedChat?"enhanced-claude":$1.chatCompletions||$1.health?"portable":"disconnected"',
  );
  if (ternaryModeNext !== next) {
    next = ternaryModeNext;
    chatModePatched += 1;
    console.log(`patched ternary chat mode detection in ${file}`);
  }

  const localStoreBefore = 'const DATA_DIR$1 = join(process.cwd(), ".runtime");';
  if (next.includes(localStoreBefore)) {
    next = next.replace(
      localStoreBefore,
      'const DATA_DIR$1 = join(process.env.HERMES_HOME || process.env.CLAUDE_HOME || process.cwd(), ".runtime");',
    );
    localSessionStorePatched += 1;
    console.log(`patched local session store path in ${file}`);
  }

  if (next !== text) {
    fs.writeFileSync(file, next);
  }
}
}

if (patched === 0) {
  throw new Error("MCP marketplace parser patch did not apply to any files");
}
if (chatModePatched === 0) {
  throw new Error("Chat mode detection patch did not apply to any files");
}
if (localSessionStorePatched === 0) {
  throw new Error("Local session store path patch did not apply to any files");
}
