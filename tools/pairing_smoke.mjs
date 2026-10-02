import { createRequire } from 'node:module';
import { mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'frontend/package.json'));
const { chromium } = require('playwright');
const [host, port, token] = process.argv.slice(2);
if (!/^com\.smartflow\.next\.smoke_[a-f0-9]{32}$/.test(host)) throw Error('Isolated host required');
const extension = path.join(root, 'browser_extension/.output/chrome-mv3');
const profile = await mkdtemp(path.join(tmpdir(), 'smartflow-pairing-browser-'));
const context = await chromium.launchPersistentContext(profile, { channel: 'chromium', headless: true,
  args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`] });
async function api(route, data) {
  const response = await fetch(`http://127.0.0.1:${port}/api${route}`, { method: data ? 'POST' : 'GET',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    ...(data ? { body: JSON.stringify(data) } : {}) });
  if (!response.ok) throw Error(`Fixture API: ${response.status}`);
  return response.json();
}
try {
  const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker', { timeout: 15000 });
  const extensionId = new URL(worker.url()).host;
  const info = await api('/browser');
  if (extensionId !== info.extension_id) throw Error('Stable extension ID mismatch');
  const native = async (kind, code) => {
    const message = { protocol_version: 1, message_id: crypto.randomUUID(), kind,
      extension_version: info.extension_version, ...(code ? { code } : {}) };
    const response = await worker.evaluate(async ({ host, message }) => chrome.runtime.sendNativeMessage(host, message), { host, message });
    if (response.message_id !== message.message_id) throw Error('Native correlation mismatch');
    return response;
  };
  if ((await native('hello')).state !== 'unpaired') throw Error('Expected isolated credential');
  const pair = await api('/browser/pairings', { extension_id: extensionId });
  if ((await native('pair', pair.code)).state !== 'paired') throw Error('Pairing failed');
  if ((await native('hello')).state !== 'paired') throw Error('Credential did not survive host restart');
  if (!(await api('/browser')).pairings.some(row => row.id === pair.id && row.connected)) throw Error('Desktop did not confirm connection');
  await api(`/browser/pairings/${pair.id}/revoke`, {});
  if ((await native('hello')).state !== 'revoked') throw Error('Revoked credential was accepted');
  console.log('Chrome -> packaged native host -> local API: pairing, new-process reconnect and revocation passed.');
} finally { await context.close(); }
