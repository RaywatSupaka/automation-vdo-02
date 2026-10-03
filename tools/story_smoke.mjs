import { isolatedExtension } from './extension_fixture.mjs';
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
const extension = await isolatedExtension(root, host);
const profile = await mkdtemp(path.join(tmpdir(), 'smartflow-pairing-browser-'));
const context = await chromium.launchPersistentContext(profile, { channel: 'chromium', headless: true,
  args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`] });
async function api(route, data, key, method) {
  const response = await fetch(`http://127.0.0.1:${port}/api${route}`, { method: method || (data ? 'POST' : 'GET'),
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', ...(key ? { 'Idempotency-Key': key } : {}) },
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
  const draft = await api('/story-drafts', { config: { topic: 'Owned frozen simulation' } }, 'owned-draft-key');
  const input = { draft_id: draft.id, expected_revision: draft.revision, mode: 'simulation' };
  const job = await api('/stories', input, 'owned-story-key');
  if ((await api('/stories', input, 'owned-story-key')).id !== job.id) throw Error('Duplicate job');
  await api(`/story-drafts/${draft.id}`, { expected_revision: draft.revision, config: { topic: 'Edited later' } },
    'owned-draft-edit', 'PATCH');
  // Probe from the real popup triggers the compiled background runner, not a reimplemented test runner.
  const popup = await context.newPage(); await popup.goto(`chrome-extension://${extensionId}/popup.html`);
  await popup.getByRole('button', { name: 'ตรวจการเชื่อมต่อ' }).click();
  let detail;
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    detail = await api(`/stories/${job.id}`);
    if (detail.status === 'completed') break;
    await new Promise(resolve => setTimeout(resolve, 200));
  }
  if (detail.status !== 'completed' || detail.result !== '[SIMULATION ONLY]\nOwned frozen simulation')
    throw Error(`Story failed: ${detail.status}/${detail.error_code}`);
  const ledger = await worker.evaluate(async () => chrome.storage.local.get(null));
  const sends = Object.entries(ledger).filter(([key]) => key.startsWith('simulation:'));
  if (sends.length !== 1 || sends[0][1].sends !== 1) throw Error('Simulation send count');
  const diagnostic = await api(`/diagnostics/stories/${job.id}`);
  const logs = await api('/diagnostics/logs');
  if (JSON.stringify({ diagnostic, logs }).includes('Owned frozen simulation')) throw Error('Private data in diagnostic');
  const events = await api(`/jobs/${job.id}/events`);
  if (events.filter(event => event.name === 'story.artifact_persisted').length !== 1) throw Error('Artifact ACK count');
  console.log('Actual compiled Extension runner -> native EXE -> API: immutable snapshot, one send, result ACK and privacy passed.');
  await api(`/browser/pairings/${pair.id}/revoke`, {});
  if ((await native('hello')).state !== 'revoked') throw Error('Revoked credential was accepted');
  console.log('Chrome -> packaged native host -> local API: pairing, new-process reconnect and revocation passed.');
} finally { await context.close(); }
