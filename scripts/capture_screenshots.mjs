#!/usr/bin/env node
/** Capture high-resolution screenshots of the running TerraLens application with headless Chrome (CDP).
 *
 * Start the app first (./scripts/start.sh), then:
 *   node scripts/capture_screenshots.mjs [http://127.0.0.1:8000]
 *
 * Writes to docs/screenshots/:
 *   observatory.jpg   - the 27,000-patch overview
 *   map-my-image.jpg  - examples/map-my-image/demo-scene.jpg mapped into named regions
 *   sort-my-photos.jpg- the 30 photos in examples/sort-my-photos sorted into groups
 *   cluster-atlas.jpg - the 10 discovered groups
 *   model-lab.jpg     - PCA scree, t-SNE and the audit
 *
 * Needs Google Chrome at its default macOS path (set CHROME to another binary path elsewhere).
 */
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const SHOTS = path.join(ROOT, "docs", "screenshots");
const BASE = process.argv[2] || "http://127.0.0.1:8000";
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9225;
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function main() {
  const profile = await fs.mkdtemp(path.join(os.tmpdir(), "terralens-shots-"));
  const chrome = spawn(CHROME, [
    "--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
    "--window-size=1440,1050", "--disable-gpu", "--no-sandbox", "--hide-scrollbars", "--force-device-scale-factor=1",
  ], { stdio: "ignore" });
  try {
    let version = null;
    for (let i = 0; i < 40 && !version; i++) {
      try { version = await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json(); } catch { await sleep(250); }
    }
    if (!version) throw new Error(`Could not connect to Chrome on port ${PORT}.`);
    const target = await (await fetch(`http://127.0.0.1:${PORT}/json/new?${BASE}/`, { method: "PUT" })).json();
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise(resolve => (ws.onopen = resolve));
    let id = 0;
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const current = ++id;
      const handler = event => {
        const message = JSON.parse(event.data);
        if (message.id !== current) return;
        ws.removeEventListener("message", handler);
        message.error ? reject(new Error(message.error.message)) : resolve(message.result);
      };
      ws.addEventListener("message", handler);
      ws.send(JSON.stringify({ id: current, method, params }));
    });
    const evaluate = async expression => (await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }))?.result?.value;
    const waitFor = async (expression, tries = 80) => { for (let i = 0; i < tries; i++) { if (await evaluate(expression)) return true; await sleep(250); } return false; };
    const capture = async filename => {
      const { data } = await send("Page.captureScreenshot", { format: "jpeg", quality: 92, captureBeyondViewport: false });
      await fs.writeFile(path.join(SHOTS, filename), Buffer.from(data, "base64"));
      console.log(`saved docs/screenshots/${filename}`);
    };
    const uploadTo = async (selector, files) => {
      const { root } = await send("DOM.getDocument", { depth: 0 });
      const { nodeId } = await send("DOM.querySelector", { nodeId: root.nodeId, selector });
      if (!nodeId) throw new Error(`No element matches ${selector}`);
      await send("DOM.setFileInputFiles", { nodeId, files });
    };
    const scrollTo = selector => evaluate(`document.querySelector(${JSON.stringify(selector)})?.scrollIntoView({block:'start'}), 0`);

    await send("Page.enable"); await send("Runtime.enable"); await send("DOM.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1050, deviceScaleFactor: 1, mobile: false });
    if (!await waitFor("!document.querySelector('.view-skeleton') && !document.querySelector('.connection-state') && !!document.querySelector('.app-shell')")) throw new Error("The app did not load. Is it running at " + BASE + "?");
    await sleep(1500);

    await evaluate("window.location.hash = 'observatory'"); await sleep(2500);
    await capture("observatory.jpg");

    await evaluate("window.location.hash = 'regions'"); await sleep(1500);
    await uploadTo("input[type=file]", [path.join(ROOT, "examples", "map-my-image", "demo-scene.jpg")]);
    if (!await waitFor("!!document.querySelector('.region-frame') && !document.querySelector('.is-updating')")) throw new Error("Map my image gave no result");
    await sleep(1200); await scrollTo(".map-summary"); await sleep(600);
    await capture("map-my-image.jpg");

    await evaluate("window.location.hash = 'sort'"); await sleep(1500);
    const photos = (await fs.readdir(path.join(ROOT, "examples", "sort-my-photos"))).filter(name => name.endsWith(".jpg")).sort().map(name => path.join(ROOT, "examples", "sort-my-photos", name));
    await uploadTo("input[aria-label='Choose satellite photos']", photos);
    await sleep(2500);
    await evaluate("[...document.querySelectorAll('button')].find(b => /sort photos/i.test(b.textContent))?.click(), 0");
    if (!await waitFor("!!document.querySelector('.sort-summary')", 120)) throw new Error("Sort my photos gave no result");
    await sleep(2500); await scrollTo(".sort-summary"); await sleep(600);
    await capture("sort-my-photos.jpg");

    await evaluate("window.location.hash = 'clusters'"); await sleep(2500);
    await capture("cluster-atlas.jpg");

    await evaluate("window.location.hash = 'diagnostics'"); await sleep(3000);
    await capture("model-lab.jpg");

    ws.close();
  } finally {
    chrome.kill();
    await fs.rm(profile, { recursive: true, force: true }).catch(() => {});
  }
}

main().catch(error => { console.error("Screenshot capture failed:", error.message); process.exit(1); });
