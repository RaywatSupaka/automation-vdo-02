// Owned temporary Chromium profile only; never attaches to the user's browser.
import { createRequire } from 'node:module';
import { mkdtemp, mkdir, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'frontend', 'package.json'));
const { chromium } = require('playwright');
const extension = path.join(root, 'browser_extension/.output/chrome-mv3');
const profile = await mkdtemp(path.join(tmpdir(), 'smartflow-next-extension-smoke-'));
const context = await chromium.launchPersistentContext(profile, { channel: 'chromium', headless: true,
  args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`] });
try {
  const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker', { timeout: 15000 });
  const id = new URL(worker.url()).host;
  const page = await context.newPage();
  await page.goto(`chrome-extension://${id}/popup.html`);
  await page.getByRole('heading', { name: 'การเชื่อมต่อโปรแกรม' }).waitFor();
  await page.getByRole('button', { name: 'ตรวจการเชื่อมต่อ' }).click();
  await page.getByRole('button', { name: 'ตรวจการเชื่อมต่อ' }).waitFor();
  await page.waitForFunction(() => !document.querySelector('button').disabled);
  const text = await page.getByRole('status').innerText();
  // P1 deliberately does not register a host. Probe must show disconnected,
  // never paired/ready based on the popup simply having loaded.
  if (text !== 'ยังไม่เชื่อมต่อ helper') throw new Error('Unexpected native host state');
  const evidence = path.join(root, 'build/extension-smoke');
  await mkdir(evidence, { recursive: true });
  await page.screenshot({ path: path.join(evidence, 'popup.png') });
  await writeFile(path.join(evidence, 'result.json'), JSON.stringify({ loaded: true, probe: 'disconnected',
    native_host_registered: false, paired: false, provider_tested: false }, null, 2));
  console.log('Extension loaded in owned Chromium profile; popup and unavailable-host behavior passed.');
} finally { await context.close(); }
