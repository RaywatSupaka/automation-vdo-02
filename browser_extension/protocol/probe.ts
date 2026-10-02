import { HOST_NAME, parseReply, type BridgeStatus, Hello } from './index';
import type { z } from 'zod';

export type NativeSend = (host: string, message: z.infer<typeof Hello>) => Promise<unknown>;
export async function probe(send: NativeSend, version: string, timeoutMs = 7000, code?: string): Promise<BridgeStatus> {
  const messageId = crypto.randomUUID();
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const result = await Promise.race([
      send(HOST_NAME, Hello.parse({ protocol_version: 1, message_id: messageId, extension_version: version,
        ...(code ? { kind: 'pair', code } : { kind: 'hello' }) })),
      new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error('TIMEOUT')), timeoutMs); }),
    ]);
    try { return parseReply(result, messageId).state; }
    catch { return 'protocol_error'; }
  } catch { return 'disconnected'; }
  finally { if (timer !== undefined) clearTimeout(timer); }
}
