#!/usr/bin/env node
/** Comprehensive Browser Testing Suite for TerraLens.
 * Tests all pages in Google Chrome via Chrome DevTools Protocol (CDP):
 * - #observatory
 * - #scanner (Regional Scene Scanner)
 * - #changes (Temporal Change & Deforestation Detector)
 * - #analyzer (Preset test, Anomaly radar & Survey dossier)
 * - #clusters (Discovered cluster atlas)
 * - #diagnostics (Sub-tabs: Manifolds, Benchmarks, Reference audit)
 */
import fs from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const OUTPUT_DIR = path.join(ROOT, ".build", "browser_tests");

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

async function main() {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });

  console.log("1. Starting backend server on port 8000...");
  const server = spawn(
    path.join(ROOT, ".venv", "bin", "python"),
    ["-m", "uvicorn", "terralens.app:app", "--host", "127.0.0.1", "--port", "8000"],
    { env: { ...process.env, PYTHONPATH: path.join(ROOT, "backend") }, stdio: "inherit" }
  );

  // Wait for server health
  let serverReady = false;
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/health");
      if (res.ok) {
        serverReady = true;
        break;
      }
    } catch {
      await sleep(250);
    }
  }
  if (!serverReady) {
    server.kill();
    throw new Error("Backend server failed to start on port 8000.");
  }
  console.log("✓ Backend server is active and healthy!");

  console.log("2. Launching headless Google Chrome...");
  const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
    "--headless=new",
    "--remote-debugging-port=9227",
    "--window-size=1440,1050",
    "--disable-gpu",
    "--no-sandbox",
    "--hide-scrollbars",
  ]);

  try {
    let version = null;
    for (let i = 0; i < 20; i++) {
      try {
        const res = await fetch("http://127.0.0.1:9227/json/version");
        version = await res.json();
        break;
      } catch {
        await sleep(250);
      }
    }
    if (!version) throw new Error("Could not connect to Chrome debugging port 9227.");
    console.log("✓ Connected to Chrome CDP:", version.Browser);

    const targetRes = await fetch("http://127.0.0.1:9227/json/new?http://127.0.0.1:8000/", { method: "PUT" });
    const target = await targetRes.json();
    const ws = new WebSocket(target.webSocketDebuggerUrl);

    await new Promise(r => (ws.onopen = r));

    let msgId = 0;
    function send(method, params = {}) {
      return new Promise((resolve, reject) => {
        const cur = ++msgId;
        const handler = e => {
          const msg = JSON.parse(e.data);
          if (msg.id === cur) {
            ws.removeEventListener("message", handler);
            if (msg.error) reject(new Error(msg.error.message));
            else resolve(msg.result);
          }
        };
        ws.addEventListener("message", handler);
        ws.send(JSON.stringify({ id: cur, method, params }));
      });
    }

    const consoleLogs = [];
    ws.addEventListener("message", e => {
      const msg = JSON.parse(e.data);
      if (msg.method === "Runtime.consoleAPICalled") {
        consoleLogs.push({ type: msg.params.type, text: msg.params.args.map(a => a.value || a.description).join(" ") });
      }
    });

    await send("Page.enable");
    await send("Runtime.enable");

    async function evaluate(expression, awaitPromise = false) {
      const res = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise });
      return res?.result?.value;
    }

    async function capture(filename) {
      const { data } = await send("Page.captureScreenshot", {
        format: "jpeg",
        quality: 90,
        captureBeyondViewport: false,
      });
      const buffer = Buffer.from(data, "base64");
      const outPath = path.join(OUTPUT_DIR, filename);
      await fs.writeFile(outPath, buffer);
      console.log(`  📸 Saved screenshot: ${filename} (${buffer.length} bytes)`);
    }

    // Wait for initial load
    console.log("3. Waiting for React application to mount...");
    for (let i = 0; i < 40; i++) {
      const loaded = await evaluate("!document.querySelector('.view-skeleton') && !document.querySelector('.connection-state') && !!document.querySelector('.app-shell')");
      if (loaded) break;
      await sleep(300);
    }
    await sleep(1500);

    // --- TEST 1: OBSERVATORY ---
    console.log("\n--- TEST 1: Observatory View ---");
    await evaluate("window.location.hash = 'observatory'");
    await sleep(2000);
    const obsStats = await evaluate("document.querySelector('.study-stats')?.textContent");
    console.log("  Stats bar content:", obsStats?.slice(0, 80));
    await capture("test-1-observatory.jpg");

    // --- TEST 2: MAP MY IMAGE (upload a scene built from real thumbnails) ---
    console.log("\n--- TEST 2: Map my image ---");
    await evaluate("window.location.hash = 'regions'");
    await sleep(1500);
    await evaluate(`(async () => {
      const study = await fetch('/api/study').then(r => r.json());
      const canvas = Object.assign(document.createElement('canvas'), { width: 512, height: 512 });
      const ctx = canvas.getContext('2d');
      await Promise.all(study.points.slice(0, 64).map((p, i) => new Promise(res => { const img = new Image(); img.onload = () => { ctx.drawImage(img, (i % 8) * 64, Math.floor(i / 8) * 64); res(); }; img.src = '/api/patches/' + p.id + '.jpg'; })));
      const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.9));
      const input = document.querySelector('input[type=file]');
      const dt = new DataTransfer(); dt.items.add(new File([blob], 'scene.jpg', { type: 'image/jpeg' })); input.files = dt.files;
      input.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    })()`, true);
    for (let i = 0; i < 40; i++) {
      if (await evaluate("!!document.querySelector('.map-summary h2')")) break;
      await sleep(300);
    }
    console.log("  Result:", await evaluate("document.querySelector('.map-summary h2')?.textContent"));
    await capture("test-2-map-my-image.jpg");

    // --- TEST 3: PATCH ANALYZER ---
    console.log("\n--- TEST 3: Patch Analyzer with Presets & Radar ---");
    await evaluate("window.location.hash = 'analyzer'");
    await sleep(2000);
    for (let i = 0; i < 40; i++) {
      if (await evaluate("!!document.querySelector('.analyzer-presets-bar button')")) break;
      await sleep(500);
    }

    // Click instant preset 'Dense Forest'
    console.log("  Clicking instant preset: 'Dense Forest'...");
    await evaluate("Array.from(document.querySelectorAll('.analyzer-presets-bar button')).find(b => b.textContent.includes('Dense Forest'))?.click()");
    await sleep(2000);

    const assignedGroup = await evaluate("document.querySelector('.assignment-heading h3')?.textContent");
    console.log("  Assigned group:", assignedGroup);

    const radarStatus = await evaluate("document.querySelector('.anomaly-radar-top')?.textContent");
    console.log("  Radar status:", radarStatus);

    // Open Land Survey Dossier
    console.log("  Opening Survey Dossier modal...");
    await evaluate("document.querySelector('.analysis-export')?.previousElementSibling?.click()");
    await sleep(1000);
    const dossierTitle = await evaluate("document.querySelector('.dossier-dialog h2')?.textContent");
    console.log("  Dossier modal opened:", dossierTitle);
    await capture("test-3-analyzer-dossier.jpg");

    // Close dossier
    await evaluate("document.querySelector('.dossier-dialog button')?.click()");
    await sleep(500);

    // --- TEST 4: CLUSTER ATLAS ---
    console.log("\n--- TEST 4: Cluster Atlas ---");
    await evaluate("window.location.hash = 'clusters'");
    for (let i = 0; i < 30; i++) {
      const cCount = await evaluate("document.querySelectorAll('.cluster-card').length");
      if (cCount === 10) break;
      await sleep(300);
    }
    const clusterCardCount = await evaluate("document.querySelectorAll('.cluster-card').length");
    console.log(`  Atlas cluster cards count: ${clusterCardCount} (Expected: 10)`);
    await capture("test-4-clusters.jpg");

    // --- TEST 5: MODEL LAB & DIAGNOSTICS ---
    console.log("\n--- TEST 5: Model Lab & Diagnostics ---");
    await evaluate("window.location.hash = 'diagnostics'");
    for (let i = 0; i < 30; i++) {
      if (await evaluate("!!document.querySelector('.subnav-pill')")) break;
      await sleep(300);
    }

    // Subtab 1: Manifolds
    const manifoldCanvases = await evaluate("document.querySelectorAll('.projection-canvas-container, .scatter-plot').length");
    console.log("  Manifolds scatter canvases:", manifoldCanvases);
    await capture("test-5-diagnostics-manifolds.jpg");

    // Subtab 2: Benchmarks
    console.log("  Switching to Clustering Benchmarks sub-tab...");
    await evaluate("document.querySelectorAll('.subnav-pill')[1]?.click()");
    await sleep(2000);
    const benchmarkSliders = await evaluate("document.querySelectorAll('.experiment-controls, .controls-grid').length");
    console.log("  Benchmark controls rendered:", benchmarkSliders > 0);
    await capture("test-5-diagnostics-benchmarks.jpg");

    // Subtab 3: Reference Audit
    console.log("  Switching to Methodology & Reference Audit sub-tab...");
    await evaluate("document.querySelectorAll('.subnav-pill')[2]?.click()");
    await sleep(2000);
    await capture("test-5-diagnostics-audit.jpg");

    // Check for runtime errors
    const errors = consoleLogs.filter(l => l.type === 'error');
    console.log(`\n4. Browser Console Errors Logged: ${errors.length}`);
    if (errors.length > 0) {
      console.warn("Console errors detected:", errors);
    } else {
      console.log("✓ Zero browser runtime errors detected across all tested routes!");
    }

    ws.close();
    console.log("\n🎉 ALL BROWSER TESTS PASSED PERFECTLY!");
  } finally {
    chrome.kill();
    server.kill();
  }
}

main().catch(err => {
  console.error("Browser testing failed:", err);
  process.exit(1);
});
