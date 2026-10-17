// apps/browser/decree-bridge.js — Bridge between Decree Portal HTML and Python DecreeLog
// Per ADR-0022: human types → decree → law (real SQLite, not localStorage)
// Works via Python subprocess (DecreeLog.issue → SQLite, hash-chained, append-only)
//
// Usage from Node/Electron:
//   const { DecreeBridge } = require('./decree-bridge.js');
//   const bridge = new DecreeBridge();
//   const decree = await bridge.issueDecree('never use Google DNS', 'prohibition');
//   const all = await bridge.getDecrees();
//
// CLI:
//   node decree-bridge.js issue "text" [category]
//   node decree-bridge.js list
//   node decree-bridge.js check "intent text"

const { spawn } = require("node:child_process");
const path = require("node:path");
const os = require("node:os");

const RUNTIME_SRC = path.join(__dirname, "..", "..", "runtime", "src");
const DB_PATH = path.join(os.homedir(), ".polymath-os", "decrees.db");

class DecreeBridge {
  constructor(opts = {}) {
    this.runtimeSrc = opts.runtimeSrc || RUNTIME_SRC;
    this.dbPath = opts.dbPath || DB_PATH;
    this.ready = true;
  }

  _runPython(script) {
    return new Promise((resolve, reject) => {
      const py = spawn("python3", ["-c", script], {
        env: { ...process.env, PYTHONPATH: this.runtimeSrc },
      });
      let out = "";
      let err = "";
      py.stdout.on("data", (d) => {
        out += d;
      });
      py.stderr.on("data", (d) => {
        err += d;
      });
      py.on("close", (code) => {
        if (code !== 0) {
          return reject(new Error(`python exit ${code}: ${err.slice(0, 400)}`));
        }
        try {
          resolve(JSON.parse(out.trim()));
        } catch (e) {
          reject(new Error(`parse: ${e.message}, got: ${out.slice(0, 200)}`));
        }
      });
    });
  }

  async issueDecree(text, category = "directive", scope = "all") {
    const script = `
import sys, json, os
sys.path.insert(0, ${JSON.stringify(this.runtimeSrc)})
from decree_log import DecreeLog
os.makedirs(os.path.dirname(${JSON.stringify(this.dbPath)}), exist_ok=True)
dl = DecreeLog(${JSON.stringify(this.dbPath)})
result = dl.issue(${JSON.stringify(text)}, category=${JSON.stringify(category)}, scope=${JSON.stringify(scope)})
dl.close()
print(json.dumps(result))
`;
    return this._runPython(script);
  }

  async getDecrees() {
    const script = `
import sys, json, os
sys.path.insert(0, ${JSON.stringify(this.runtimeSrc)})
from decree_log import DecreeLog
if not os.path.exists(${JSON.stringify(this.dbPath)}):
    print(json.dumps([]))
else:
    dl = DecreeLog(${JSON.stringify(this.dbPath)})
    print(json.dumps(dl.get_all()))
    dl.close()
`;
    return this._runPython(script);
  }

  async checkCompliance(intentText) {
    const script = `
import sys, json, os
sys.path.insert(0, ${JSON.stringify(this.runtimeSrc)})
from decree_log import DecreeLog
if not os.path.exists(${JSON.stringify(this.dbPath)}):
    print(json.dumps({"compliant": True, "violations": [], "laws_checked": 0}))
else:
    dl = DecreeLog(${JSON.stringify(this.dbPath)})
    print(json.dumps(dl.check_compliance(${JSON.stringify(intentText)})))
    dl.close()
`;
    return this._runPython(script);
  }
}

// CLI
if (require.main === module) {
  const bridge = new DecreeBridge();
  const cmd = process.argv[2];
  if (cmd === "issue") {
    const text = process.argv[3];
    const cat = process.argv[4] || "directive";
    if (!text) {
      console.error('Usage: node decree-bridge.js issue "text" [category]');
      process.exit(1);
    }
    bridge
      .issueDecree(text, cat)
      .then((r) => {
        console.log(JSON.stringify(r, null, 2));
        process.exit(0);
      })
      .catch((e) => {
        console.error(e.message);
        process.exit(1);
      });
  } else if (cmd === "list") {
    bridge
      .getDecrees()
      .then((r) => {
        console.log(JSON.stringify(r, null, 2));
        process.exit(0);
      })
      .catch((e) => {
        console.error(e.message);
        process.exit(1);
      });
  } else if (cmd === "check") {
    const text = process.argv[3];
    if (!text) {
      console.error('Usage: node decree-bridge.js check "intent text"');
      process.exit(1);
    }
    bridge
      .checkCompliance(text)
      .then((r) => {
        console.log(JSON.stringify(r, null, 2));
        process.exit(0);
      })
      .catch((e) => {
        console.error(e.message);
        process.exit(1);
      });
  } else {
    console.log("Polymath-OS Decree Bridge — Node <-> Python DecreeLog");
    console.log("");
    console.log("Usage:");
    console.log(
      '  node decree-bridge.js issue "decree text" [law|prohibition|permission|directive|observation]',
    );
    console.log("  node decree-bridge.js list");
    console.log('  node decree-bridge.js check "intent text to verify"');
    console.log("");
    console.log("DB:", DB_PATH);
    process.exit(0);
  }
}

module.exports = { DecreeBridge, DB_PATH, RUNTIME_SRC };
