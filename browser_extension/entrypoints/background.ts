import { browser } from 'wxt/browser';
import { defineBackground } from 'wxt/utils/define-background';
import { allowedPopup } from '../protocol';
import { StoryRunner, SimulatedProvider, safeStorage } from '../protocol/runner';
import { requestWork } from '../protocol/work';
import { probe } from '../protocol/probe';

export default defineBackground(() => {
  let runner: Promise<StoryRunner> | undefined;
  const initialize = async () => {
    await browser.storage.local.setAccessLevel({ accessLevel: 'TRUSTED_CONTEXTS' });
    const saved = await browser.storage.session.get('connection_id');
    const connection = typeof saved.connection_id === 'string' ? saved.connection_id : crypto.randomUUID();
    await browser.storage.session.set({ connection_id: connection });
    const storage = safeStorage({ get: async (key: string) => (await browser.storage.local.get(key))[key],
      set: async (key: string, value: unknown) => { await browser.storage.local.set({ [key]: value }); } });
    return new StoryRunner(command => requestWork((host, message) => browser.runtime.sendNativeMessage(host, message), command),
      storage, new SimulatedProvider(storage), connection);
  };
  const tick = async () => {
    try { runner ??= initialize().catch(error => { runner = undefined; throw error; }); await (await runner).tick(); }
    catch { /* Backend persists operation stage/reason; never log private native payloads. */ }
  };
  browser.alarms.onAlarm.addListener(alarm => { if (alarm.name === 'story-worker') void tick(); });
  const wake = async () => { try { await browser.alarms.create('story-worker', { periodInMinutes: 0.5 }); await tick(); } catch { /* Retry on next browser wake. */ } };
  browser.runtime.onStartup.addListener(() => { void wake(); });
  browser.runtime.onInstalled.addListener(() => { void wake(); });
  void wake();
  browser.runtime.onMessage.addListener((message, sender) => {
    if (!allowedPopup(sender, browser.runtime.id)) return Promise.resolve({ state: 'protocol_error' });
    if (!message || (message.kind !== 'probe' && message.kind !== 'pair') ||
      (message.kind === 'probe' && Object.keys(message).length !== 1) ||
      (message.kind === 'pair' && (Object.keys(message).length !== 2 || typeof message.code !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(message.code))))
      return Promise.resolve({ state: 'protocol_error' });
    return probe((host, payload) => browser.runtime.sendNativeMessage(host, payload), browser.runtime.getManifest().version, 7000, message.code)
      .then(state => { if (state === 'paired') void tick(); return { state }; });
  });
});
