import { HOST_NAME, parseReply, type BridgeStatus, Hello } from './index';
import type { z } from 'zod';

export type NativeSend = (host: string, message: z.infer<typeof Hello>) => Promise<unknown>;
export async function probe(send: NativeSend, version: string, timeoutMs = 5000): Promise<BridgeStatus> {
  const messageId = crypto.randomUUID();
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const result = await Promise.race([
      send(HOST_NAME, Hello.parse({ protocol_version: 1, message_id: messageId, kind: 'hello', extension_version: version })),
      new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error('TIMEOUT')), timeoutMs); }),
    ]);
    try { parseReply(result, messageId); return 'unpaired'; }
    catch { return 'protocol_error'; }
  } catch { return 'disconnected'; }
  finally { if (timer !== undefined) clearTimeout(timer); }
}
