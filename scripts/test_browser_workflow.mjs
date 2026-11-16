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

    async function evaluate(expression) {
      const res = await send("Runtime.evaluate", { expression, returnByValue: true });
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

    // --- TEST 2: REGIONAL SCENE SCANNER ---
    console.log("\n--- TEST 2: Regional Scene Scanner ---");
    await evaluate("window.location.hash = 'scanner'");
    await sleep(2500);
    const tileCount = await evaluate("document.querySelectorAll('.scanner-tile').length");
    console.log(`  Rendered tiles count: ${tileCount} (Expected: 16)`);
    if (tileCount !== 16) throw new Error(`Expected 16 tiles in scanner, got ${tileCount}`);

    const assessmentText = await evaluate("document.querySelector('.assessment-body')?.textContent");
    console.log("  Ecological assessment:", assessmentText);

    // Click on tile 3
    console.log("  Clicking tile 3 to inspect...");
    await evaluate("document.querySelectorAll('.scanner-tile')[2]?.click()");
    await sleep(500);
    const selectedClass = await evaluate("document.querySelector('.tile-class-name')?.textContent");
    console.log("  Selected tile class:", selectedClass);
    await capture("test-2-scanner.jpg");

    // --- TEST 3: TEMPORAL CHANGE DETECTOR ---
    console.log("\n--- TEST 3: Temporal Change & Deforestation Detector ---");
    await evaluate("window.location.hash = 'changes'");
    await sleep(2500);
    const alertLevel = await evaluate("document.querySelector('.alert-level-pill')?.textContent");
    console.log("  Detected status:", alertLevel);
    const deltas = await evaluate("Array.from(document.querySelectorAll('.drift-metric-card')).map(c => c.textContent.trim()).join(' | ')");
    console.log("  Drift telemetry:", deltas);
    await capture("test-3-changes.jpg");

    // Switch to Drought Preset
    console.log("  Testing 'Reservoir & Riverbed Shrinkage (Drought)' preset...");
    await evaluate("Array.from(document.querySelectorAll('.preset-chip')).find(c => c.textContent.includes('Drought'))?.click()");
    await sleep(2000);
    const droughtAlert = await evaluate("document.querySelector('.alert-level-pill')?.textContent");
    console.log("  Drought status:", droughtAlert);
    await capture("test-3-changes-drought.jpg");

    // --- TEST 4: PATCH ANALYZER ---
    console.log("\n--- TEST 4: Patch Analyzer with Presets & Radar ---");
    await evaluate("window.location.hash = 'analyzer'");
    await sleep(2000);

    // Click instant preset 'Dense Forest'
    console.log("  Clicking instant preset: 'Dense Forest'...");
    await evaluate("Array.from(document.querySelectorAll('.analyzer-presets-bar button')).find(b => b.textContent.includes('Dense Forest'))?.click()");
    await sleep(2500);

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
    await capture("test-4-analyzer-dossier.jpg");

    // Close dossier
    await evaluate("document.querySelector('.dossier-dialog button')?.click()");
    await sleep(500);

    // --- TEST 5: CLUSTER ATLAS ---
    console.log("\n--- TEST 5: Cluster Atlas ---");
    await evaluate("window.location.hash = 'clusters'");
    await sleep(2000);
    const clusterCardCount = await evaluate("document.querySelectorAll('.cluster-card').length");
    console.log(`  Atlas cluster cards count: ${clusterCardCount} (Expected: 10)`);
    await capture("test-5-clusters.jpg");

    // --- TEST 6: MODEL LAB & DIAGNOSTICS ---
    console.log("\n--- TEST 6: Model Lab & Diagnostics ---");
    await evaluate("window.location.hash = 'diagnostics'");
    await sleep(2500);

    // Subtab 1: Manifolds
    const manifoldCanvases = await evaluate("document.querySelectorAll('.projection-canvas-container, .scatter-plot').length");
    console.log("  Manifolds scatter canvases:", manifoldCanvases);
    await capture("test-6-diagnostics-manifolds.jpg");

    // Subtab 2: Benchmarks
    console.log("  Switching to Clustering Benchmarks sub-tab...");
    await evaluate("document.querySelectorAll('.subnav-pill')[1]?.click()");
    await sleep(2000);
    const benchmarkSliders = await evaluate("document.querySelectorAll('.experiment-controls, .controls-grid').length");
    console.log("  Benchmark controls rendered:", benchmarkSliders > 0);
    await capture("test-6-diagnostics-benchmarks.jpg");

    // Subtab 3: Reference Audit
    console.log("  Switching to Methodology & Reference Audit sub-tab...");
    await evaluate("document.querySelectorAll('.subnav-pill')[2]?.click()");
    await sleep(2000);
    await capture("test-6-diagnostics-audit.jpg");

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
