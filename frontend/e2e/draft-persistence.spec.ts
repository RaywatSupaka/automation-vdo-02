import { test, expect } from '@playwright/test';

const headers = { Authorization: 'Bearer e2e-fixture-session-not-a-real-secret' };
test.beforeEach(async ({ page, request }) => {
  await request.post('/api/story-drafts', { headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() }, data: {} });
  await page.goto('/#token=e2e-fixture-session-not-a-real-secret');
  await page.getByRole('button', { name: 'เรื่องเล่า Shorts', exact: true }).click();
  await expect(page.getByLabel('หัวข้อคลิป', { exact: true })).toBeVisible();
});

test('Autosave restores step, text and imported asset after reopening', async ({ page, request }) => {
  await page.getByLabel('หัวข้อคลิป', { exact: true }).fill('draft persistence fixture');
  await page.getByLabel('รูปหลัก / รูปอ้างอิงร่วม').setInputFiles({ name: 'reference.png', mimeType: 'image/png',
    buffer: Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]), Buffer.alloc(40)]) });
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await page.getByLabel('โทนเรื่อง', { exact: true }).selectOption('ลึกลับ');
  expect(await page.evaluate(() => window.smartflowFlush!())).toBe(true);
  await page.reload();
  await page.getByRole('button', { name: 'เรื่องเล่า Shorts', exact: true }).click();
  await expect(page.getByLabel('โทนเรื่อง', { exact: true })).toHaveValue('ลึกลับ');
  await page.getByRole('button', { name: '1. เรื่องที่จะเล่า · ผ่านแล้ว' }).click();
  await expect(page.getByLabel('หัวข้อคลิป', { exact: true })).toHaveValue('draft persistence fixture');
  await expect(page.locator('.story-workspace')).toContainText('reference.png');
  const rows = await (await request.get('/api/story-drafts', { headers })).json();
  const saved = await (await request.get(`/api/story-drafts/${rows[0].id}`, { headers })).json();
  expect(saved.config.mainImage).toHaveLength(1);
  const assets = await (await request.get(`/api/story-drafts/${rows[0].id}/assets`, { headers })).json();
  expect(assets[0].missing).toBe(false);
});

test('Autosave retains local changes after conflict and blocks close flush', async ({ page, request }) => {
  const rows = await (await request.get('/api/story-drafts', { headers })).json();
  const original = await (await request.get(`/api/story-drafts/${rows[0].id}`, { headers })).json();
  await request.patch(`/api/story-drafts/${rows[0].id}`,  { headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() },
    data: { expected_revision: rows[0].revision, config: { ...original.config, topic: 'another window' } } });
  await page.getByLabel('หัวข้อคลิป', { exact: true }).fill('keep local draft');
  await expect(page.locator('.draft-save-status')).toHaveText('พบข้อมูลจากอีกหน้าต่าง');
  expect(await page.evaluate(() => window.smartflowFlush!())).toBe(false);
  await expect(page.getByLabel('หัวข้อคลิป', { exact: true })).toHaveValue('keep local draft');
  const current = await (await request.get(`/api/story-drafts/${rows[0].id}`, { headers })).json();
  expect(current.config.topic).toBe('another window');
});

test('Autosave retries an interrupted save without losing edits', async ({ page }) => {
  let failures = 0;
  await page.route('**/api/story-drafts/*', route => {
    if (route.request().method() === 'PATCH' && failures++ < 1) return route.abort();
    return route.continue();
  });
  await page.getByLabel('หัวข้อคลิป', { exact: true }).fill('bounded retry fixture');
  await expect(page.locator('.draft-save-status')).toHaveText('บันทึกแล้วในเครื่อง');
  expect(failures).toBe(2);
  await page.reload();
  await page.getByRole('button', { name: 'เรื่องเล่า Shorts', exact: true }).click();
  await expect(page.getByLabel('หัวข้อคลิป', { exact: true })).toHaveValue('bounded retry fixture');
});
