import { z } from 'zod';

export const HOST_NAME = 'com.smartflow.next.dev';
export const PROTOCOL_VERSION = 1;
export const MAX_MESSAGE_BYTES = 64 * 1024;
const id = z.string().uuid();
export const Hello = z.strictObject({
  protocol_version: z.literal(PROTOCOL_VERSION), message_id: id, kind: z.literal('hello'),
  extension_version: z.literal('0.1.0'),
});
export const HostReply = z.strictObject({
  protocol_version: z.literal(PROTOCOL_VERSION), message_id: id, kind: z.literal('hello.result'),
  helper_version: z.literal('0.1.0'), state: z.literal('unpaired'),
  capabilities: z.array(z.never()).max(0),
});
export type BridgeStatus = 'disconnected' | 'checking' | 'unpaired' | 'protocol_error';

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
