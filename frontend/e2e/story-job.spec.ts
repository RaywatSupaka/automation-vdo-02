import { test, expect } from '@playwright/test';

const owner = 'e2e-fixture-session-not-a-real-secret';
const ownerHeaders = { Authorization: `Bearer ${owner}` };
type Task = { connection_id: string; operation_id: string; request_id: string; lease_epoch: number; topic: string };

test('story job starts from the review step and a simulated agent completes it once', async ({ page, request }) => {
  const draft = await request.post('/api/story-drafts', { headers: { ...ownerHeaders, 'Idempotency-Key': crypto.randomUUID() },
    data: { config: { topic: 'e2e story job' } } });
  expect(draft.status()).toBe(201);

  await page.goto(`/#token=${owner}`);
  await page.getByRole('button', { name: 'เรื่องเล่า Shorts', exact: true }).click();
  await expect(page.getByLabel('หัวข้อคลิป', { exact: true })).toHaveValue('e2e story job');
  for (let step = 0; step < 4; step++) await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  const start = page.getByRole('button', { name: 'เริ่มงานจำลอง', exact: true });
  await expect(start).toBeEnabled();
  await start.click();
  await expect(page.getByRole('status').filter({ hasText: 'รอ Extension' })).toContainText('รอ Extension', { timeout: 10000 });

  const browser = await request.get('/api/browser', { headers: ownerHeaders });
  expect(browser.ok()).toBeTruthy();
  const info = await browser.json() as { extension_id: string; extension_version: string; helper_version: string };
  const pairing = await request.post('/api/browser/pairings', { headers: ownerHeaders,
    data: { extension_id: info.extension_id } });
  expect(pairing.status()).toBe(200);
  const { code } = await pairing.json() as { code: string };
  const agentToken = crypto.randomUUID().replace(/-/g, '') + crypto.randomUUID().replace(/-/g, '');
  const paired = await request.post('/api/browser/pair', { headers: { Authorization: `Bearer ${code}` },
    data: { extension_id: info.extension_id, agent_token: agentToken,
      extension_version: info.extension_version, helper_version: info.helper_version } });
  expect(paired.ok()).toBeTruthy();

  const agentHeaders = { Authorization: `Bearer ${agentToken}` };
  const connection_id = crypto.randomUUID();
  const work = (data: object) => request.post('/api/browser/work', { headers: agentHeaders, data });
  let task: Task | null = null;
  await expect.poll(async () => {
    const response = await work({ action: 'sync', connection_id, extension_version: info.extension_version,
      helper_version: info.helper_version, capability: 'story_simulator_v1' });
    expect(response.ok()).toBeTruthy();
    task = (await response.json() as { task: Task | null }).task;
    return task;
  }, { timeout: 10000 }).not.toBeNull();
  if (!task) throw new Error('The paired agent received no simulated Story task');
  const command = { connection_id, operation_id: task.operation_id, request_id: task.request_id,
    lease_epoch: task.lease_epoch };
  const granted = await work({ action: 'grant', ...command });
  expect(granted.ok()).toBeTruthy();
  expect((await granted.json() as { granted: boolean }).granted).toBe(true);
  const duplicate = await work({ action: 'grant', ...command });
  expect(duplicate.ok()).toBeTruthy();
  expect((await duplicate.json() as { granted: boolean }).granted).toBe(false);
  const result = await work({ action: 'result', ...command, result: `[SIMULATION ONLY]\n${task.topic}` });
  expect(result.ok()).toBeTruthy();
  expect((await result.json() as { persisted: boolean }).persisted).toBe(true);

  await expect(page.getByRole('status').filter({ hasText: 'เสร็จ (จำลอง)' }))
    .toContainText('เสร็จ (จำลอง)', { timeout: 10000 });
  await expect(page.locator('.story-job-status')).toContainText('SIMULATION');
  await expect(page.locator('.story-simulation-result')).toContainText('[SIMULATION ONLY]');
});
