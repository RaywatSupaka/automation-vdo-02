import { test, expect } from '@playwright/test';

const token = 'e2e-fixture-session-not-a-real-secret';
test.beforeEach(async ({ page }) => { await page.goto(`/#token=${token}`); });

test('create, inspect timeline, database, logs and export evidence', async ({ page }) => {
  await page.getByRole('button', { name: 'สร้างงานทดสอบ', exact: true }).first().click();
  await page.getByLabel('ชื่องาน', { exact: true }).fill('งานสำเร็จจาก UI');
  await page.getByRole('button', { name: 'เริ่มงานจำลอง' }).click();
  await expect(page.locator('.job-detail .status')).toHaveText('สำเร็จ');
  await expect(page.getByText('artifact.saved', { exact: true })).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'ข้อมูลวิเคราะห์', exact: true }).click();
  expect((await download).suggestedFilename()).toMatch(/^smartflow-.*\.zip$/);
  await page.screenshot({ path: 'test-results/dashboard.png', fullPage: true });
  await page.getByRole('button', { name: 'ตรวจฐานข้อมูล' }).click();
  await expect(page.locator('pre')).toContainText('completed');
  await page.getByRole('button', { name: 'บันทึกระบบ' }).click();
  await expect(page.locator('pre')).toContainText('trace_id');
});

test('unknown send explains reason and reads existing result', async ({ page }) => {
  await page.getByRole('button', { name: 'สร้างงานทดสอบ', exact: true }).first().click();
  await page.getByLabel('ชื่องาน', { exact: true }).fill('ตรวจผลโดยไม่ส่งซ้ำ');
  await page.getByLabel('สถานการณ์จำลอง').selectOption('unknown_send');
  await page.getByRole('button', { name: 'เริ่มงานจำลอง' }).click();
  await expect(page.locator('.job-error strong')).toHaveText('SEND_ACCEPTANCE_UNKNOWN');
  await expect(page.getByRole('button', { name: 'ทำต่อ', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'ตรวจผลเดิม', exact: true }).click();
  await expect(page.locator('.job-detail .status')).toHaveText('สำเร็จ');
});
