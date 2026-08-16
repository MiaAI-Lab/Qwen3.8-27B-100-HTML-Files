#!/usr/bin/env node
// Raw-CDP headless smoke test for a single-file HTML page. Zero dependencies
// (uses Node 22+'s built-in WebSocket), so it works where playwright isn't
// installed. Spawns chromium-browser with --remote-debugging-port, connects
// over WebSocket, captures Runtime.exceptionThrown + console.error, then runs
// the requested probe.
//
// Usage:
//   node headless-smoke.cjs probe   <file-url> <label>   # ticks + canvas size + errors (default)
//   node headless-smoke.cjs interact <file-url> <label>  # probe + dispatch clicks/drag/dblclick/space, re-probe errors
//   node headless-smoke.cjs shot    <file-url> <out.png> # screenshot after settling
//
// probe/interact print JSON: {file, ticks, canvas:[w,h], errors:[]}.
// `ticks` counts rAF callbacks over ~400ms — a healthy animation loop reports
// ~20–25 here (60fps-equivalent). If the loop died to a thrown error, ticks
// still counts (the probe owns its rAF) but errors will be non-empty.
//
// Note: chromium via snap cannot read/write /tmp (AppArmor) on some hosts —
// pass screenshot paths inside the workspace, not /tmp.

const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');

const mode = process.argv[2] || 'probe';
const url = process.argv[3];
const out = process.argv[4];
const label = process.argv[5] || (mode === 'shot' ? out : url);
const port = 9400 + (process.pid % 100);
const profile = '/tmp/cdp-' + Date.now() + '-' + process.pid;

const chrome = spawn('chromium-browser', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--enable-unsafe-swiftshader',
  '--window-size=900,600', '--force-device-scale-factor=1',
  '--remote-debugging-port=' + port, '--user-data-dir=' + profile,
  '--autoplay-policy=no-user-gesture-required', url
], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getWsUrl() {
  for (let i = 0; i < 40; i++) {
    try {
      const data = await new Promise((res, rej) => {
        http.get('http://127.0.0.1:' + port + '/json/list', r => { let b=''; r.on('data',d=>b+=d); r.on('end',()=>res(b)); }).on('error', rej);
      });
      const page = JSON.parse(data).find(p => p.type === 'page');
      if (page && page.webSocketDebuggerUrl) return page.webSocketDebuggerUrl;
    } catch (e) {}
    await sleep(150);
  }
  throw new Error('CDP endpoint not available (is chromium on PATH?)');
}

(async () => {
  const ws = new WebSocket(await getWsUrl());
  let id = 0; const pending = new Map(); const errors = [];
  const send = (method, params = {}) => new Promise((res, rej) => { const mid = ++id; pending.set(mid, { res, rej }); ws.send(JSON.stringify({ id: mid, method, params })); });
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id); pending.delete(m.id);
      m.error ? p.rej(new Error(JSON.stringify(m.error))) : p.res(m.result);
    } else if (m.method === 'Runtime.exceptionThrown') {
      errors.push('EXCEPTION: ' + ((m.params.exceptionDetails.exception && m.params.exceptionDetails.exception.description) || m.params.exceptionDetails.text).split('\n')[0]);
    } else if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      errors.push('CONSOLE.ERROR: ' + m.params.args.map(a => a.value || a.description || '').join(' ').slice(0, 160));
    }
  };
  await new Promise(res => ws.onopen = res);
  await send('Runtime.enable'); await send('Runtime.enable'); // idempotent
  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 900, height: 600, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url });
  await sleep(1100);

  if (mode === 'shot') {
    const shot = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(out, Buffer.from(shot.data, 'base64'));
    console.log('saved ' + out);
    ws.close(); chrome.kill(); process.exit(0);
  }

  const fire = async (type, x, y, b = 0, cc = 1) =>
    send('Input.dispatchMouseEvent', { type, x: Math.round(x), y: Math.round(y), button: 'left', buttons: b, clickCount: cc });

  if (mode === 'interact') {
    await fire('mousePressed', 260, 240); await fire('mouseReleased', 260, 240);
    await fire('mousePressed', 500, 320, 1);
    for (let i = 0; i < 5; i++) { await fire('mouseMoved', 170 + i * 40, 300 - i * 14, 1); await sleep(50); }
    await fire('mouseReleased', 330, 244);
    await fire('mousePressed', 430, 260); await fire('mouseReleased', 430, 260);
    await fire('mousePressed', 150, 150, 1, 2); await fire('mouseReleased', 150, 150, 0, 2);
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: ' ', code: 'Space', windowsVirtualKeyCode: 32, nativeVirtualKeyCode: 32 });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: ' ', code: 'Space', windowsVirtualKeyCode: 32, nativeVirtualKeyCode: 32 });
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: '2', code: 'Digit2', windowsVirtualKeyCode: 50, nativeVirtualKeyCode: 50 });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: '2', code: 'Digit2', windowsVirtualKeyCode: 50, nativeVirtualKeyCode: 50 });
    await sleep(1200);
  }

  const result = await send('Runtime.evaluate', {
    expression: `(async () => {
      const c = document.querySelector('canvas');
      const t0 = performance.now(); let ticks = 0;
      return new Promise(res => {
        function probe(){ ticks++; if (performance.now() - t0 < 400) requestAnimationFrame(probe); else res({ ticks, cw: c ? c.width : -1, ch: c ? c.height : -1 }); }
        requestAnimationFrame(probe);
      });
    })()`,
    awaitPromise: true, returnByValue: true
  });
  const r = result.result.value;
  await sleep(350);
  console.log(JSON.stringify({
    file: label, mode,
    ticks: r && r.ticks, canvas: r ? [r.cw, r.ch] : null,
    errors: errors.slice(0, 6)
  }));
  ws.close(); chrome.kill(); process.exit(0);
})().catch(e => { console.error('FATAL ' + e.message); chrome.kill(); process.exit(1); });
