/**
 * singulyar_eir_bridge.mjs — JavaScript caller for polymath-os SINGULYAR EIR kernel.
 *
 * This is the JS-side of the Python↔JS bridge. singulyar's JS modules
 * (·21 ОБЩЕНИЕ, ·15 ОРКЕСТРАТОР, etc.) can call this to route Intents
 * through polymath-os's Python kernel.
 *
 * Two modes:
 * 1. subprocess: spawn Python, communicate via stdin/stdout JSON
 * 2. (future) Pyodide: load Python kernel as WASM in browser
 *
 * Usage (subprocess mode):
 *   import { EIRBridge } from './singulyar_eir_bridge.mjs';
 *   const bridge = new EIRBridge();
 *   await bridge.start();
 *   const result = await bridge.run({
 *     intent_id: 'js-call-1',
 *     operation: 'execute_command',
 *     payload: { phrase: 'пинг' },
 *     expected: {}
 *   });
 *   // result = { state: 'CONFIRMED', intent_id: 'js-call-1', via: 'singulyar-eir-bridge' }
 *   await bridge.stop();
 *
 * Per ADR-0012 (SINGULYAR EIR as Layer 5): this proves the kernel works
 * across language boundaries. Intent is language-agnostic.
 */

import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const PYTHON_SCRIPT = join(__dirname, 'subprocess_bridge.py');

export class EIRBridge {
  constructor(options = {}) {
    this.python = options.python || 'python3';
    this.scriptPath = options.scriptPath || PYTHON_SCRIPT;
    this.proc = null;
    this.buffer = '';
    this.pending = [];
    this.ready = false;
  }

  async start() {
    return new Promise((resolve, reject) => {
      this.proc = spawn(this.python, [this.scriptPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: { ...process.env, PYTHONPATH: join(__dirname, '..') + ':' + (process.env.PYTHONPATH || '') }
      });

      this.proc.stdout.on('data', (data) => {
        this.buffer += data.toString();
        const lines = this.buffer.split('\n');
        this.buffer = lines.pop(); // keep incomplete line

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const msg = JSON.parse(line);
            if (msg.type === 'ready') {
              this.ready = true;
              resolve(msg);
            } else if (this.pending.length > 0) {
              const { resolve: resolver } = this.pending.shift();
              resolver(msg);
            }
          } catch (e) {
            // not JSON, ignore or log
            console.error('[EIRBridge] non-JSON line:', line);
          }
        }
      });

      this.proc.stderr.on('data', (data) => {
        console.error('[EIRBridge] stderr:', data.toString());
      });

      this.proc.on('error', (err) => {
        reject(new Error(`failed to start Python: ${err.message}`));
      });

      this.proc.on('exit', (code) => {
        if (!this.ready) {
          reject(new Error(`Python exited before ready (code ${code})`));
        }
      });

      // Timeout if Python doesn't say "ready" in 10s
      setTimeout(() => {
        if (!this.ready) reject(new Error('Python bridge timeout — no ready signal in 10s'));
      }, 10000);
    });
  }

  async run(intent) {
    if (!this.ready || !this.proc) {
      throw new Error('bridge not started — call start() first');
    }
    return new Promise((resolve, reject) => {
      this.pending.push({ resolve, reject });
      this.proc.stdin.write(JSON.stringify(intent) + '\n');
      // Timeout 30s
      setTimeout(() => {
        if (this.pending.length > 0) {
          const { reject: rejecter } = this.pending.shift();
          rejecter(new Error('timeout: kernel did not respond in 30s'));
        }
      }, 30000);
    });
  }

  async ping() {
    return this.run({ type: 'ping' });
  }

  async stop() {
    if (this.proc) {
      this.proc.stdin.write('exit\n');
      this.proc.stdin.end();
      await new Promise((resolve) => {
        this.proc.on('exit', () => resolve());
        setTimeout(() => { this.proc.kill(); resolve(); }, 5000);
      });
      this.proc = null;
      this.ready = false;
    }
  }
}

// CLI usage: node singulyar_eir_bridge.mjs '{"intent_id":"test","operation":"execute_command","payload":{"phrase":"пинг"},"expected":{}}'
if (process.argv[1] && process.argv[1].endsWith('singulyar_eir_bridge.mjs')) {
  const intentJson = process.argv[2];
  if (!intentJson) {
    console.error('Usage: node singulyar_eir_bridge.mjs \'{"intent_id":"test","operation":"execute_command","payload":{"phrase":"пинг"},"expected":{}}\'');
    process.exit(1);
  }
  const bridge = new EIRBridge();
  try {
    await bridge.start();
    const result = await bridge.run(JSON.parse(intentJson));
    console.log(JSON.stringify(result, null, 2));
    await bridge.stop();
  } catch (e) {
    console.error('Error:', e.message);
    await bridge.stop();
    process.exit(1);
  }
}
