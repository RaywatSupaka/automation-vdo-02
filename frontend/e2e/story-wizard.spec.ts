import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/#token=e2e-fixture-session-not-a-real-secret');
  await page.getByRole('button', { name: 'เรื่องเล่า Shorts', exact: true }).click();
});

test('Story wizard validates, preserves draft and requires review again after edits', async ({ page }) => {
  const posts: string[] = [];
  page.on('request', request => { if (request.method() === 'POST') posts.push(request.url()); });
  const next = page.getByRole('button', { name: 'ถัดไป', exact: true });
  const progress = page.getByRole('progressbar', { name: 'ขั้นตอนที่ผ่านแล้ว' });
  await expect(progress).toHaveAttribute('value', '0');
  await expect(page.getByRole('button', { name: '5. ตรวจรายละเอียด · ยังไม่ถึง' })).toBeDisabled();
  await next.click();
  await expect(page.getByRole('alert')).toContainText('ใส่หัวข้อ');
  await expect(page.getByRole('alert')).toBeFocused();
  await page.getByLabel('หัวข้อหรือเรื่องย่อ').fill('แมวจรที่รอรถไฟกับเด็กน้อย');
  await next.click();
  await expect(page.getByRole('heading', { name: 'อยากให้เรื่องนี้รู้สึกแบบไหน?' })).toBeFocused();
  await page.getByRole('radio', { name: 'ลึกลับ', exact: true }).check();
  await next.click();
  await page.getByLabel('จำนวนฉาก', { exact: true }).fill('0');
  await next.click();
  await expect(page.getByRole('alert')).toContainText('1 ถึง 12');
  await page.getByLabel('จำนวนฉาก', { exact: true }).fill('4');
  await next.click();
  await page.getByRole('checkbox', { name: 'พักให้ตรวจบทก่อนสร้างภาพ', exact: true }).check();
  await next.click();
  await expect(page.locator('.story-review')).toContainText('ลึกลับ');
  await expect(page.locator('.story-review')).toContainText('4 ฉาก');
  await expect(progress).toHaveAttribute('value', '4');
  await page.getByRole('button', { name: 'ยืนยันรายละเอียดแบบร่าง', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('ยังไม่เริ่มสร้างสื่อ');
  await expect(progress).toHaveAttribute('value', '5');
  // Merely viewing an earlier step must not trap navigation after confirmation.
  await page.getByRole('button', { name: '1. เรื่องที่จะเล่า · ผ่านแล้ว' }).click();
  await expect(page.getByLabel('หัวข้อหรือเรื่องย่อ')).toHaveValue('แมวจรที่รอรถไฟกับเด็กน้อย');
  await expect(next).toBeEnabled();
  await page.getByRole('button', { name: 'งานอัตโนมัติ', exact: true }).click();
  await page.getByRole('button', { name: 'เรื่องเล่า Shorts', exact: true }).click();
  await expect(page.getByLabel('หัวข้อหรือเรื่องย่อ')).toHaveValue('แมวจรที่รอรถไฟกับเด็กน้อย');
  await page.getByLabel('หัวข้อหรือเรื่องย่อ').fill('เรื่องฉบับแก้ไข');
  await expect(progress).toHaveAttribute('value', '0');
  await expect(page.getByRole('button', { name: '5. ตรวจรายละเอียด · ยังไม่ถึง' })).toBeDisabled();
  await next.click();
  await expect(page.getByRole('radio', { name: 'ลึกลับ', exact: true })).toBeChecked();
  expect(posts).toEqual([]);
});

test('Story wizard fits desktop and narrow screens with visible footer and internal scrolling', async ({ page }) => {
  for (const viewport of [{ width: 1366, height: 768 }, { width: 1024, height: 600 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await expect(page.getByRole('button', { name: 'ถัดไป', exact: true })).toBeInViewport();
    await expect(page.getByRole('progressbar')).toBeInViewport();
    const fits = await page.evaluate(() => ({
      width: document.documentElement.scrollWidth <= innerWidth,
      height: document.documentElement.scrollHeight <= innerHeight,
    }));
    expect(fits).toEqual({ width: true, height: true });
    await page.screenshot({ animations: 'disabled', path: `test-results/story-${viewport.width}.png` });
  }
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.getByLabel('หัวข้อหรือเรื่องย่อ').fill('ร้านกาแฟที่รับฟังความฝันแทนการรับเงิน');
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await page.screenshot({ animations: 'disabled', path: 'test-results/story-style.png' });
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await page.screenshot({ animations: 'disabled', path: 'test-results/story-scenes.png' });
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await page.screenshot({ animations: 'disabled', path: 'test-results/story-audio.png' });
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await page.screenshot({ animations: 'disabled', path: 'test-results/story-review.png' });
  await page.getByRole('button', { name: '1. เรื่องที่จะเล่า · ผ่านแล้ว' }).click();
  await page.getByLabel('หัวข้อหรือเรื่องย่อ').fill('เรื่องราวที่มีรายละเอียด\n'.repeat(80));
  for (let index = 0; index < 4; index++) await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  expect(await page.locator('.wizard-body').evaluate(element => element.scrollHeight > element.clientHeight)).toBe(true);
  await expect(page.getByRole('button', { name: 'ยืนยันรายละเอียดแบบร่าง' })).toBeInViewport();
});

test('Story wizard is unavailable to a support session and clears on session expiry', async ({ page }) => {
  await page.getByLabel('หัวข้อหรือเรื่องย่อ').fill('ข้อมูลส่วนตัวในแบบร่าง');
  await page.route('**/api/session', route => route.fulfill({ status: 401, contentType: 'application/json',
    body: JSON.stringify({ error: { code: 'UNAUTHORIZED', message: 'หมดอายุ', trace_id: 'fixture' } }) }));
  await expect(page.getByLabel('Session token สำหรับนักพัฒนา')).toBeVisible();
  await expect(page.locator('.story-workspace')).toHaveCount(0);
  await page.unroute('**/api/session');
  await page.getByLabel('Session token สำหรับนักพัฒนา').fill('e2e-support-session-not-a-real-secret');
  await page.getByRole('button', { name: 'เชื่อมต่อ', exact: true }).click();
  await expect(page.getByRole('button', { name: 'ตรวจฐานข้อมูล', exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'เรื่องเล่า Shorts', exact: true })).toHaveCount(0);
});
