// Drives the running hangar-cv-optimizer app (backend + frontend must
// already be up - see SKILL.md) with headless Chromium and captures
// screenshots that prove each page actually rendered/worked.
//
// Usage: node driver.mjs <path-to-sample-jpg> [frontend-url] [out-dir]
//
// Requires playwright + a downloaded chromium build. If neither is set up:
//   mkdir -p /tmp/pw-run && cd /tmp/pw-run && npm init -y >/dev/null 2>&1
//   npm install --no-save playwright && npx playwright install chromium

import { chromium } from 'playwright';

const sampleImage = process.argv[2];
const baseUrl = process.argv[3] || 'http://127.0.0.1:5299';
const outDir = process.argv[4] || '.';

if (!sampleImage) {
  console.error('Usage: node driver.mjs <path-to-sample-jpg> [frontend-url] [out-dir]');
  process.exit(1);
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (err) => errors.push(String(err)));

  // --- Layout Planner: optimize a default 3-aircraft layout ---
  await page.goto(`${baseUrl}/`, { waitUntil: 'networkidle' });
  await page.waitForSelector('text=Hangar Layout Planner');
  await page.screenshot({ path: `${outDir}/01-home.png`, fullPage: true });

  await page.click('button:has-text("Optimize Layout")');
  await page.waitForSelector('text=Collision status', { timeout: 15000 });
  await page.waitForTimeout(500); // let the SVG finish rendering
  await page.screenshot({ path: `${outDir}/02-optimized.png`, fullPage: true });

  // --- Aircraft Detection: upload a real image, expect bbox overlays ---
  await page.goto(`${baseUrl}/detect`, { waitUntil: 'networkidle' });
  await page.waitForSelector('text=Aircraft Detection');
  const fileInput = await page.$('input[type=file]');
  await fileInput.setInputFiles(sampleImage);
  // First /detect call is slow: YOLO model lazy-loads on first request (~3-5s).
  await page.waitForSelector('svg image', { timeout: 30000 });
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${outDir}/03-detect.png`, fullPage: true });

  console.log('CONSOLE_ERRORS:', JSON.stringify(errors));
  if (errors.length > 0) {
    console.error('Driver found console errors - see above. Not a clean run.');
    process.exitCode = 1;
  } else {
    console.log('Clean run: 3 screenshots written, zero console errors.');
  }

  await browser.close();
})().catch((err) => { console.error('DRIVER_FAILED:', err); process.exit(1); });
