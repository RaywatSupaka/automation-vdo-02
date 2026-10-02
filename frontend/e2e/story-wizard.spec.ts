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
  await expect(progress).toHaveAttribute('aria-valuenow', '0');
  await expect(page.getByRole('button', { name: '5. ตรวจรายละเอียด · ยังไม่ถึง' })).toBeDisabled();
  await next.click();
  await expect(page.getByRole('alert')).toContainText('หัวข้อคลิป');
  await expect(page.getByRole('alert')).toBeFocused();
  await page.getByLabel('หัวข้อคลิป').fill('แมวจรที่รอรถไฟกับเด็กน้อย');
  await next.click();
  await expect(page.getByRole('heading', { name: 'อยากให้เรื่องนี้รู้สึกแบบไหน?' })).toBeFocused();
  await page.getByLabel('โทนเรื่อง', { exact: true }).selectOption('ลึกลับ');
  await next.click();
  await page.getByLabel('จำนวนฉาก', { exact: true }).fill('0');
  await next.click();
  await expect(page.getByRole('alert')).toContainText('6 ถึง 15');
  await page.getByLabel('จำนวนฉาก', { exact: true }).fill('8');
  await next.click();
  await page.locator('.story-setting-group').filter({ has: page.locator('summary', { hasText: 'การทำงานอัตโนมัติ' }) }).locator('summary').click();
  await page.getByRole('checkbox', { name: 'พักให้ตรวจบทก่อนสร้างภาพ', exact: true }).check();
  await next.click();
  await expect(page.locator('.story-review')).toContainText('ลึกลับ');
  await expect(page.locator('.story-review')).toContainText('จำนวนฉาก');
  await expect(page.locator('.story-review')).toContainText('8');
  await expect(progress).toHaveAttribute('aria-valuenow', '4');
  await page.getByRole('button', { name: 'ยืนยันรายละเอียดแบบร่าง', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('ยังไม่เริ่มสร้างสื่อ');
  await expect(progress).toHaveAttribute('aria-valuenow', '5');
  // Merely viewing an earlier step must not trap navigation after confirmation.
  await page.getByRole('button', { name: '1. เรื่องที่จะเล่า · ผ่านแล้ว' }).click();
  await expect(page.getByLabel('หัวข้อคลิป')).toHaveValue('แมวจรที่รอรถไฟกับเด็กน้อย');
  await expect(next).toBeEnabled();
  await page.getByRole('button', { name: 'งานอัตโนมัติ', exact: true }).click();
  await page.getByRole('button', { name: 'เรื่องเล่า Shorts', exact: true }).click();
  await expect(page.getByLabel('หัวข้อคลิป')).toHaveValue('แมวจรที่รอรถไฟกับเด็กน้อย');
  await page.getByLabel('หัวข้อคลิป').fill('เรื่องฉบับแก้ไข');
  await expect(progress).toHaveAttribute('aria-valuenow', '0');
  await expect(page.getByRole('button', { name: '5. ตรวจรายละเอียด · ยังไม่ถึง' })).toBeDisabled();
  await next.click();
  await expect(page.getByLabel('โทนเรื่อง', { exact: true })).toHaveValue('ลึกลับ');
  expect(posts).toEqual([]);
});

test('Story wizard fits desktop and narrow screens with visible footer and internal scrolling', async ({ page }) => {
  for (const viewport of [{ width: 1366, height: 768 }, { width: 1024, height: 600 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await expect(page.getByRole('button', { name: 'ถัดไป', exact: true })).toBeInViewport();
    await expect(page.locator('.wizard-progress')).toBeInViewport();
    await expect(page.locator('.wizard-progress')).not.toContainText('ขั้นที่');
    await expect(page.locator('.wizard-progress')).not.toContainText('ผ่านแล้ว');
    await expect(page.locator('.story-page-heading')).toHaveText('เรื่องเล่า short');
    const geometry = await page.locator('.wizard-steps').evaluate(list => {
      const circles = [...list.querySelectorAll('.wizard-step-number')].map(el => el.getBoundingClientRect());
      const labels = [...list.querySelectorAll('.wizard-step-copy')].map(el => el.getBoundingClientRect());
      const connectors = [...list.querySelectorAll('.wizard-connector')].map(el => el.getBoundingClientRect());
      return circles.every((circle, index) => circle.bottom <= labels[index].top) &&
        connectors.every((line, index) => Math.abs(line.left - circles[index].right) < 1 &&
          Math.abs(line.right - circles[index + 1].left) < 1 &&
          Math.abs(line.top + line.height / 2 - (circles[index].top + circles[index].height / 2)) < 1);
    });
    expect(geometry).toBe(true);
    await expect.poll(() => page.locator('.brand img').evaluate(img => (img as HTMLImageElement).complete && (img as HTMLImageElement).naturalWidth > 0)).toBe(true);
    const fits = await page.evaluate(() => ({
      width: document.documentElement.scrollWidth <= innerWidth,
      height: document.documentElement.scrollHeight <= innerHeight,
    }));
    expect(fits).toEqual({ width: true, height: true });
    await page.screenshot({ animations: 'disabled', path: `test-results/story-${viewport.width}.png` });
  }
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.getByLabel('หัวข้อคลิป').fill('ร้านกาแฟที่รับฟังความฝันแทนการรับเงิน');
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await page.screenshot({ animations: 'disabled', path: 'test-results/story-style.png' });
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await page.screenshot({ animations: 'disabled', path: 'test-results/story-scenes.png' });
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await page.screenshot({ animations: 'disabled', path: 'test-results/story-audio.png' });
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await page.screenshot({ animations: 'disabled', path: 'test-results/story-review.png' });
  await page.getByRole('button', { name: '1. เรื่องที่จะเล่า · ผ่านแล้ว' }).click();
  await page.getByLabel('หัวข้อคลิป').fill('เรื่องราวที่มีรายละเอียด\n'.repeat(80));
  for (let index = 0; index < 4; index++) await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  expect(await page.locator('.wizard-body').evaluate(element => element.scrollHeight > element.clientHeight)).toBe(true);
  await expect(page.getByRole('button', { name: 'ยืนยันรายละเอียดแบบร่าง' })).toBeInViewport();
});

test('Story wizard is unavailable to a support session and clears on session expiry', async ({ page }) => {
  await page.getByLabel('หัวข้อคลิป').fill('ข้อมูลส่วนตัวในแบบร่าง');
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

test('Story wizard exposes legacy details, conditional red stars and file drafts without provider requests', async ({ page }) => {
  const posts: string[] = [];
  page.on('request', request => { if (request.method() === 'POST') posts.push(request.url()); });
  await expect(page.getByLabel('หัวข้อคลิป', { exact: true })).toHaveAttribute('aria-required', 'true');
  await expect(page.locator('.story-setting-field').filter({ has: page.getByLabel('หัวข้อคลิป', { exact: true }) }).locator('.required-mark')).toHaveCSS('color', 'rgb(255, 102, 124)');
  await page.getByLabel('หัวข้อคลิป', { exact: true }).fill('หัวข้อเดี่ยวที่ต้องคงไว้');
  await page.getByLabel('รายละเอียดเรื่องและวิธีเล่าที่ต้องการ', { exact: true }).fill('ให้ตัวเอกค้นพบจดหมายลับ');
  await page.getByLabel('จำนวนคลิปที่ต้องการเตรียม').selectOption('batch');
  await page.getByLabel('หัวข้อคลิปในชุด', { exact: true }).fill('เรื่องที่หนึ่ง\nเรื่องที่สอง');
  await page.getByLabel('รูปหลัก / รูปอ้างอิงร่วม').setInputFiles({ name: 'reference.png', mimeType: 'image/png', buffer: Buffer.from('fixture metadata only') });
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await expect(page.getByLabel('โครงเรื่อง', { exact: true }).locator('option')).toHaveCount(12);
  await expect(page.getByLabel('สไตล์ภาพ', { exact: true }).locator('option')).toHaveCount(8);
  await page.getByLabel('ใครเป็นคนพูด').selectOption('dialogue');
  await page.getByLabel('สไตล์ภาพ', { exact: true }).selectOption('custom');
  await expect(page.getByLabel('แนวภาพที่กำหนดเอง')).toHaveAttribute('aria-required', 'true');
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('แนวภาพที่กำหนดเอง');
  await page.getByLabel('แนวภาพที่กำหนดเอง').fill('ภาพสีน้ำโทนม่วง');
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await page.getByLabel('สร้างภาพด้วย', { exact: true }).selectOption('gemini');
  await page.getByLabel('โมเดล Gemini', { exact: true }).selectOption('flash');
  await page.getByLabel('เปลี่ยนภาพเป็นวิดีโอด้วย', { exact: true }).selectOption('google_flow');
  await page.locator('summary').filter({ hasText: /^รายละเอียด Google Flow/ }).click();
  await page.getByLabel('โมเดลวิดีโอ Flow', { exact: true }).selectOption('Omni 1.1 Flash');
  await page.locator('summary').filter({ hasText: /^อินโทร/ }).click();
  await page.getByLabel('สุ่มแทรกอินโทรหลังเริ่มเล่าเรื่อง', { exact: true }).check();
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('วิดีโออินโทร');
  await page.getByLabel('วิดีโออินโทร', { exact: true }).setInputFiles({ name: 'intro.mp4', mimeType: 'video/mp4', buffer: Buffer.from('fixture metadata only') });
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await expect(page.getByLabel('เสียงจากระบบ API', { exact: true })).toBeDisabled();
  await page.locator('summary').filter({ hasText: /^คำบรรยายและรูปแบบซับ/ }).click();
  await expect(page.getByLabel('ธีมซับ', { exact: true }).locator('option')).toHaveCount(12);
  await page.getByLabel('ธีมซับ', { exact: true }).selectOption('neon_punch');
  await page.getByRole('button', { name: 'ถัดไป', exact: true }).click();
  await expect(page.locator('.story-review')).toContainText('reference.png');
  await expect(page.locator('.story-review')).toContainText('intro.mp4');
  await expect(page.locator('.story-review')).toContainText('Gemini Web');
  await expect(page.locator('.story-review')).toContainText('HOT Neon Punch');
  await page.getByRole('button', { name: '1. เรื่องที่จะเล่า · ผ่านแล้ว' }).click();
  await page.getByLabel('จำนวนคลิปที่ต้องการเตรียม').selectOption('single');
  await expect(page.getByLabel('หัวข้อคลิป', { exact: true })).toHaveValue('หัวข้อเดี่ยวที่ต้องคงไว้');
  await expect(page.getByLabel('รายละเอียดเรื่องและวิธีเล่าที่ต้องการ', { exact: true })).toHaveValue('ให้ตัวเอกค้นพบจดหมายลับ');
  expect(posts).toEqual([]);
});
