// Pyodide host worker. Runs the Python game with synchronous stdin via SAB.

importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.2/full/pyodide.js');

let stdinLen, stdinData, decoder, encoder;

function readStdinLine() {
  // Block here until main thread writes a line into the buffer.
  Atomics.wait(stdinLen, 0, 0);
  const len = Atomics.load(stdinLen, 0);
  const bytes = new Uint8Array(len);
  bytes.set(stdinData.subarray(0, len));
  Atomics.store(stdinLen, 0, 0);
  return decoder.decode(bytes);
}

function postStdout(text) {
  // xterm.js needs CRLF, Python prints LF.
  text = text.replace(/(?<!\r)\n/g, '\r\n');
  self.postMessage({ type: 'stdout', data: text });
}

async function main() {
  decoder = new TextDecoder();
  encoder = new TextEncoder();

  self.postMessage({ type: 'status', data: '正在下載 Pyodide…' });
  const pyodide = await loadPyodide({
    indexURL: 'https://cdn.jsdelivr.net/pyodide/v0.27.2/full/',
  });

  self.postMessage({ type: 'status', data: '正在設置執行環境…' });

  pyodide.setStdin({
    stdin: readStdinLine,
    isatty: true,
    autoEOF: false,
  });

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
