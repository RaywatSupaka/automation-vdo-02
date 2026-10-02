import { z } from 'zod';

export const HOST_NAME = 'com.smartflow.next.dev';
export const PROTOCOL_VERSION = 1;
export const MAX_MESSAGE_BYTES = 64 * 1024;
const id = z.string().uuid();
const base = { protocol_version: z.literal(PROTOCOL_VERSION), message_id: id, extension_version: z.literal('0.1.1') };
export const Hello = z.discriminatedUnion('kind', [z.strictObject({ ...base, kind: z.literal('hello') }),
  z.strictObject({ ...base, kind: z.literal('pair'), code: z.string().regex(/^[A-Za-z0-9_-]{43}$/) })]);
export const HostReply = z.strictObject({
  protocol_version: z.literal(PROTOCOL_VERSION), message_id: id, kind: z.literal('bridge.result'),
  helper_version: z.literal('0.1.1'), state: z.enum(['unpaired', 'paired', 'revoked', 'unavailable', 'pairing_rejected']),
  capabilities: z.array(z.never()).max(0),
});
export type BridgeStatus = 'disconnected' | 'checking' | 'unpaired' | 'protocol_error' | 'paired' | 'revoked' | 'unavailable' | 'pairing_rejected';

export function parseReply(value: unknown, messageId: string) {
  if (new TextEncoder().encode(JSON.stringify(value)).length > MAX_MESSAGE_BYTES) throw new Error('PROTOCOL_INVALID');
  const reply = HostReply.parse(value);
  if (reply.message_id !== messageId) throw new Error('PROTOCOL_INVALID');
  return reply;
}

// Only the extension's own popup may initiate a probe. Content scripts and other
// extension pages cannot proxy privileged native messages through this handler.
export function allowedPopup(sender: { id?: string; url?: string; tab?: unknown }, extensionId: string) {
  return sender.id === extensionId && sender.url === `chrome-extension://${extensionId}/popup.html`;
}
