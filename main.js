// xterm.js terminal + Web Worker bridge for Pyodide.
// Stdin uses SharedArrayBuffer + Atomics so Python's blocking input() works
// without a Python rewrite. Stdout flows back via postMessage.

(() => {
  const statusEl = document.getElementById('status');
  const setStatus = (msg, isErr) => {
    statusEl.textContent = msg;
    statusEl.classList.toggle('error', !!isErr);
  };

  if (typeof SharedArrayBuffer === 'undefined' || !self.crossOriginIsolated) {
    console.error(
      'SAB unavailable. typeof SAB =',
      typeof SharedArrayBuffer,
      'crossOriginIsolated =',
      self.crossOriginIsolated,
    );
    setStatus(
      '此頁面缺少 Cross-Origin Isolation。請重新整理一次（service worker 第一次載入需要刷新）。如果重整後仍看到此訊息，請檢查瀏覽器是否支援 SharedArrayBuffer。',
      true,
    );
    return;
  }

  const term = new Terminal({
    fontSize: 14,
    fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    cursorBlink: true,
    convertEol: false,
    theme: {
      background: '#000000',
      foreground: '#e6e6e6',
      cursor: '#b87fff',
    },
    rows: 32,
    cols: 90,
  });

  const fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(document.getElementById('terminal'));
  try { fitAddon.fit(); } catch {}
  window.addEventListener('resize', () => { try { fitAddon.fit(); } catch {} });

  // ---- Stdin SAB protocol ----
  // Layout: [Int32 length, ...Uint8 bytes (UTF-8)]
  // Worker stdin loop: Atomics.wait until length > 0, read bytes, reset to 0.
  const STDIN_CAP = 4096;
  const stdinBuf = new SharedArrayBuffer(4 + STDIN_CAP);
  const stdinLen = new Int32Array(stdinBuf, 0, 1);
  const stdinData = new Uint8Array(stdinBuf, 4, STDIN_CAP);

  // Line buffering on the main side: only complete lines are pushed to worker.
  let lineBuf = '';

  term.onData((data) => {
    for (const ch of data) {
      const code = ch.charCodeAt(0);
      if (ch === '\r') {
        term.write('\r\n');
        const bytes = new TextEncoder().encode(lineBuf + '\n');
        if (bytes.length > STDIN_CAP) {
          // truncate just in case
          stdinData.set(bytes.subarray(0, STDIN_CAP));
          Atomics.store(stdinLen, 0, STDIN_CAP);
        } else {
          stdinData.set(bytes);
          Atomics.store(stdinLen, 0, bytes.length);
        }
        Atomics.notify(stdinLen, 0, 1);
        lineBuf = '';
      } else if (ch === '\x7f' || ch === '\b') {
        if (lineBuf.length > 0) {
          lineBuf = lineBuf.slice(0, -1);
          term.write('\b \b');
        }
      } else if (ch === '\x03') {
        // Ctrl-C: send empty line (worker game treats KeyboardInterrupt softly)
        term.write('^C\r\n');
        lineBuf = '';
      } else if (code >= 32 || code === 9) {
        lineBuf += ch;
        term.write(ch);
      }
    }
  });

  // ---- Worker setup ----
  const worker = new Worker('worker.js');
  worker.postMessage({ type: 'init', stdinBuf });

  worker.onmessage = (e) => {
    const msg = e.data;
    if (msg.type === 'stdout') {
      term.write(msg.data);
    } else if (msg.type === 'status') {
      setStatus(msg.data);
    } else if (msg.type === 'ready') {
      setStatus('遊戲執行中。輸入後按 Enter。');
    } else if (msg.type === 'error') {
      term.write(`\r\n\x1b[31m[Error] ${msg.data}\x1b[0m\r\n`);
      setStatus('遊戲錯誤，請看終端機訊息。', true);
    } else if (msg.type === 'done') {
      term.write('\r\n\x1b[2m(遊戲結束。重新整理頁面再玩一次)\x1b[0m\r\n');
      setStatus('遊戲結束。');
    }
  };

  worker.onerror = (e) => {
    setStatus(`Worker 錯誤：${e.message}`, true);
  };
})();
