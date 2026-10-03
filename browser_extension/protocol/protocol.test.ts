import { afterEach, describe, expect, it, vi } from 'vitest';
import { allowedPopup, Hello, parseReply } from './index';
import { probe } from './probe';

const messageId = '624ff25b-97a3-4b21-8a13-62ffde2f327b';
const reply = (id = messageId) => ({ protocol_version: 1, message_id: id, kind: 'bridge.result', helper_version: '0.2.0', state: 'unpaired', capabilities: [] });
afterEach(() => vi.useRealTimers());
describe('bridge boundary', () => {
  it('accepts hello but cannot advertise pairing or provider capabilities', () => {
    expect(Hello.parse({ protocol_version: 1, message_id: messageId, kind: 'hello', extension_version: '0.2.0' })).toBeTruthy();
    expect(parseReply(reply(), messageId).state).toBe('unpaired');
    expect(() => parseReply({ ...reply(), state: 'ready' }, messageId)).toThrow();
    expect(() => parseReply({ ...reply(), capabilities: ['dispatch'] }, messageId)).toThrow();
  });
  it('rejects stale, unknown and incompatible messages', () => {
    expect(() => parseReply(reply(), crypto.randomUUID())).toThrow();
    for (const extra of [{ protocol_version: 2 }, { shell: 'arbitrary' }, { helper_version: '9.0.0' }])
      expect(() => parseReply({ ...reply(), ...extra }, messageId)).toThrow();
  });
  it('only accepts requests from the own popup', () => {
    const id = 'a'.repeat(32), url = `chrome-extension://${id}/popup.html`;
    expect(allowedPopup({ id, url }, id)).toBe(true);
    expect(allowedPopup({ id, url, tab: {} }, id)).toBe(true);
    for (const sender of [{ id, url: 'https://chatgpt.com/', tab: {} }, { id, url: 'https://chatgpt.com/' }, { id: 'other', url }, {}])
      expect(allowedPopup(sender, id)).toBe(false);
  });
  it('bounds missing native responses without retrying a send', async () => {
    vi.useFakeTimers();
    const send = vi.fn(() => new Promise<unknown>(() => {}));
    const pending = probe(send, '0.2.0');
    await vi.advanceTimersByTimeAsync(7000);
    expect(await pending).toBe('disconnected');
    expect(send).toHaveBeenCalledTimes(1);
  });
  it('does not trust previous service-worker state after reconnect', async () => {
    const send = vi.fn(async (_host: string, msg: unknown) => reply((msg as { message_id: string }).message_id));
    expect(await probe(send, '0.2.0')).toBe('unpaired');
    expect(await probe(async () => { throw new Error('unavailable'); }, '0.2.0')).toBe('disconnected');
    expect(await probe(send, '0.2.0')).toBe('unpaired');
    expect(send.mock.calls[0]![1]).not.toEqual(send.mock.calls[1]![1]);
  });
});
