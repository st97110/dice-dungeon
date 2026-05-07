// Pyodide host worker.
// Stdout flows back via Pyodide's setStdout write hook.
// Stdin uses a direct monkey-patch of builtins.input that calls a JS function
// blocking on Atomics.wait — bypasses Pyodide's stdin pipeline (which has
// version-dependent quirks around buffering / autoEOF).

importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js');

let stdinLen, stdinData;
const decoder = new TextDecoder();

function diceReadLine() {
  // Block worker thread until main writes a line.
  Atomics.wait(stdinLen, 0, 0);
  const len = Atomics.load(stdinLen, 0);
  const bytes = new Uint8Array(len);
  bytes.set(stdinData.subarray(0, len));
  Atomics.store(stdinLen, 0, 0);
  let s = decoder.decode(bytes);
  if (s.endsWith('\n')) s = s.slice(0, -1);
  if (s.endsWith('\r')) s = s.slice(0, -1);
  return s;
}

function postStdout(text) {
  text = text.replace(/(?<!\r)\n/g, '\r\n');
  self.postMessage({ type: 'stdout', data: text });
}

async function main() {
  self.postMessage({ type: 'status', data: '正在下載 Pyodide…' });
  const pyodide = await loadPyodide({
    indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.27.2/full/',
  });

  self.postMessage({ type: 'status', data: '正在設置執行環境…' });

  // Stdout — try `write` (per-buffer), fall back to `batched` if unsupported.
  try {
    pyodide.setStdout({
      write: (buffer) => {
        postStdout(decoder.decode(buffer));
        return buffer.length;
      },
      isatty: true,
    });
    pyodide.setStderr({
      write: (buffer) => {
        postStdout(decoder.decode(buffer));
        return buffer.length;
      },
      isatty: true,
    });
  } catch (_) {
    pyodide.setStdout({ batched: postStdout, isatty: true });
    pyodide.setStderr({ batched: postStdout, isatty: true });
  }

  // Expose blocking line-read to Python.
  globalThis.diceReadLine = diceReadLine;

  // Patch Python's input() so it pulls from our SAB-backed JS function.
  pyodide.runPython(`
import sys
import builtins
import js

def _patched_input(prompt=""):
    if prompt:
        sys.stdout.write(str(prompt))
        sys.stdout.flush()
    return js.diceReadLine()

builtins.input = _patched_input
`);

  self.postMessage({ type: 'status', data: '正在載入遊戲程式碼…' });
  const code = await fetch('dice_dungeon.py').then((r) => r.text());

  self.postMessage({ type: 'ready' });

  try {
    pyodide.runPython(code);
    self.postMessage({ type: 'done' });
  } catch (e) {
    self.postMessage({ type: 'error', data: String(e && e.message ? e.message : e) });
  }
}

self.onmessage = (e) => {
  if (e.data && e.data.type === 'init') {
    stdinLen = new Int32Array(e.data.stdinBuf, 0, 1);
    stdinData = new Uint8Array(e.data.stdinBuf, 4);
    main().catch((err) => {
      self.postMessage({ type: 'error', data: String(err && err.message ? err.message : err) });
    });
  }
};
