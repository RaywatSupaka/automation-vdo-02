import { z } from 'zod';
import { HOST_NAME, MAX_MESSAGE_BYTES } from './index';

export const Task = z.strictObject({ operation_id: z.uuid(), request_id: z.uuid(), job_id: z.uuid(),
  revision_id: z.uuid(), trace_id: z.string().max(80), connection_id: z.uuid(),
  lease_epoch: z.number().int().positive(), lease_until: z.number(), mode: z.enum(['dispatch', 'inspect']),
  simulation: z.literal(true), topic: z.string().max(2000) });
export type WorkTask = z.infer<typeof Task>;
const Data = z.strictObject({ task: Task.nullable().default(null), granted: z.boolean().default(false),
  lease_until: z.number().nullable().default(null), persisted: z.boolean().default(false),
  sha256: z.string().regex(/^[a-f0-9]{64}$/).nullable().default(null) });
const Reply = z.discriminatedUnion('ok', [
  z.strictObject({ protocol_version: z.literal(1), message_id: z.uuid(), kind: z.literal('work.result'),
    helper_version: z.literal('0.2.0'), ok: z.literal(true), data: Data }),
  z.strictObject({ protocol_version: z.literal(1), message_id: z.uuid(), kind: z.literal('work.result'),
    helper_version: z.literal('0.2.0'), ok: z.literal(false), code: z.string().regex(/^[A-Z_]+$/) }),
]);
export type WorkData = z.infer<typeof Data>;
export type NativeWorkSend = (host: string, message: object) => Promise<unknown>;
export async function requestWork(send: NativeWorkSend, command: Record<string, unknown>, host = HOST_NAME): Promise<WorkData> {
  const id = crypto.randomUUID();
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    const raw = await Promise.race([send(host, { protocol_version: 1, message_id: id, kind: 'work',
      extension_version: '0.2.0', command }), new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('EXTENSION_DISCONNECTED')), 7000);
      })]);
    if (new TextEncoder().encode(JSON.stringify(raw)).length > MAX_MESSAGE_BYTES) throw Error('PROTOCOL_INVALID');
    const reply = Reply.parse(raw);
    if (reply.message_id !== id) throw Error('PROTOCOL_INVALID');
    if (!reply.ok) throw Error(reply.code);
    return reply.data;
  } finally { clearTimeout(timer); }
}
