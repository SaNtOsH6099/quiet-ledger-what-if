// capture.js — generic per-item particle capture for the GitHub render farm.
// Ported from the proven local capture-16.js (Short 16, three 0.187.0).
//
// Env (required):
//   CFG_FILE   path to the job's cfg file (base64 JSON, same format as cfg-16-<ITEM>.txt)
//   SCENE_URL  base URL of render/scene.html WITHOUT the ?cfg= (e.g. http://127.0.0.1:8123/render/scene.html)
//   OUT_DIR    directory to write frames into (created if missing)
// Env (optional):
//   CHROME_BIN path to a headless Chrome binary (default: /usr/bin/google-chrome)
//   PORT       CDP port (default: 9224)
//   START      resume frame index (default: 0)
//
// The cfg JSON carries `frames` (count) and `bg` (server-root-relative still URL),
// so the only per-job inputs are the cfg file + the still it references.
// Writes p_%03d.png frames into OUT_DIR. No npm dependencies (Node built-ins only).
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const CHROME = process.env.CHROME_BIN || '/usr/bin/google-chrome';
const PORT = parseInt(process.env.PORT || '9224', 10);
const CFG_FILE = process.env.CFG_FILE;
const SCENE_URL = process.env.SCENE_URL;
const OUT_DIR = process.env.OUT_DIR;
const START = parseInt(process.env.START || '0', 10);
if (!CFG_FILE || !SCENE_URL || !OUT_DIR) {
  console.error('CFG_FILE, SCENE_URL and OUT_DIR env vars are required');
  process.exit(2);
}
const CFG = fs.readFileSync(CFG_FILE, 'utf8').trim();
const cfgObj = JSON.parse(Buffer.from(CFG, 'base64').toString('utf8'));
const FRAMES = cfgObj.frames;
const URL = SCENE_URL + '?cfg=' + CFG;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function waitForPort(tries = 60) {
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/json/version`);
      if (r.ok) return await r.json();
    } catch (e) {}
    await sleep(500);
  }
  throw new Error('chrome debugging port never came up');
}

(async () => {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const chrome = spawn(CHROME, [
    '--headless', '--remote-debugging-port=' + PORT,
    '--no-sandbox', '--disable-dev-shm-usage',
    '--enable-unsafe-swiftshader',
    '--window-size=1080,1920', '--force-device-scale-factor=1',
    '--hide-scrollbars', 'about:blank'
  ], { stdio: ['ignore', 'ignore', 'ignore'] });

  let ws, nextId = 1;
  const pending = new Map();
  let loadFired = false;
  let sessionId = null;

  function send(method, params = {}, sess) {
    return new Promise((resolve, reject) => {
      const id = nextId++;
      pending.set(id, { resolve, reject });
      const msg = { id, method, params };
      if (typeof sess === 'string' && sess) msg.sessionId = sess;
      ws.send(JSON.stringify(msg));
      setTimeout(() => {
        if (pending.has(id)) { pending.delete(id); reject(new Error('CDP timeout: ' + method)); }
      }, 60000);
    });
  }

  try {
    const version = await waitForPort();
    ws = new WebSocket(version.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id && pending.has(msg.id)) {
        const { resolve, reject } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      } else if (msg.method === 'Page.loadEventFired') {
        loadFired = true;
      }
    };

    const { targetId } = await send('Target.createTarget', { url: URL });
    const { sessionId: sid } = await send('Target.attachToTarget', { targetId, flatten: true });
    sessionId = sid;
    await send('Page.enable', {}, sessionId);
    for (let i = 0; i < 40 && !loadFired; i++) await sleep(250);
    await sleep(1500);
    const ready = await send('Runtime.evaluate', { expression: 'window.__ready === true', returnByValue: true }, sessionId);
    if (!ready || !ready.result || !ready.result.value) throw new Error('page never became ready (three.js module failed?)');

    for (let n = START; n < FRAMES; n++) {
      const ev = await send('Runtime.evaluate', { expression: `window.renderFrame(${n})`, returnByValue: true }, sessionId);
      if (ev && ev.exceptionDetails) throw new Error('renderFrame(' + n + ') threw: ' + JSON.stringify(ev.exceptionDetails).slice(0, 500));
      const shot = await send('Page.captureScreenshot', { format: 'png' }, sessionId);
      fs.writeFileSync(path.join(OUT_DIR, 'p_' + String(n).padStart(3, '0') + '.png'), Buffer.from(shot.data, 'base64'));
      if (n % 20 === 0 || n === FRAMES - 1) console.log('frame', n, 'done');
    }
    console.log('CAPTURE DONE:', FRAMES, 'frames ->', OUT_DIR);
  } catch (err) {
    console.error('CAPTURE FAILED:', err.message);
    process.exitCode = 1;
  } finally {
    try { ws && ws.close(); } catch (e) {}
    chrome.kill('SIGKILL');
  }
})();
