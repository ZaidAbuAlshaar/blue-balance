import { test, expect, type Page } from '@playwright/test';
import { mkdirSync } from 'node:fs';

const OUT = process.env.BB_SCREENS ?? 'E:/blue-balance-data/screens';
mkdirSync(OUT, { recursive: true });
// Writes (field results, work orders, reports) change the live demo DB, so they only run when asked.
const MUTATE = process.env.E2E_MUTATE === '1';

// No login screen: the app starts as Engineer A, and the top role bar switches demo roles.
async function login(page: Page, id: string) {
  await page.goto('/');
  await expect(page.locator('.sidebar')).toBeVisible();
  const opt = page.locator(`.rb-opt[data-user=${id}]`);
  if ((await opt.getAttribute('aria-pressed')) !== 'true') await opt.click();
  await expect(opt).toHaveAttribute('aria-pressed', 'true');
}

async function shot(page: Page, name: string) {
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${OUT}\\${name}.png`, fullPage: false });
}

test('screens', async ({ page }) => {
  await login(page, 'eng_a');
  await shot(page, '01_rolebar');

  await page.goto('/#/overview');
  await expect(page.locator('.qitem').first()).toBeVisible();
  await page.waitForSelector('.map-label-case');
  await shot(page, '02_overview');

  await page.goto('/#/case/KRK-T-002');
  await expect(page.locator('.fusion')).toBeVisible();
  await page.waitForSelector('.chips img');
  await shot(page, '03_case_fusion');
  await page.locator('.case-grid .col').first().locator('.card').nth(1).scrollIntoViewIfNeeded();
  if (MUTATE) {
    await page.locator('[data-outcome=no_anomaly_found]').click();
    await expect(page.locator('.fr-result')).toBeVisible();
    await page.waitForTimeout(1200);
  }
  await shot(page, '04_verify_field_result');

  await page.goto('/#/case/KRK-F-001');
  await page.waitForSelector('.chips img');
  await shot(page, '05_case_field_cropland');

  await page.goto('/#/ask');
  await page.getByRole('button', { name: 'مين صاحب المزرعة KRK-F-001؟' }).click();
  await expect(page.locator('.answer')).toBeVisible({ timeout: 120_000 });
  await shot(page, '06_ask_refusal');
  if (process.env.E2E_ASK_LLM === '1') {
    await page.getByRole('button', { name: 'ليش KRK-T-002 بأول القائمة؟' }).click();
    await expect(page.locator('.toolcard').first()).toBeVisible({ timeout: 170_000 });
    await shot(page, '06b_ask_answer');
  }

  await page.goto('/#/crew');
  await page.waitForSelector('.ph-select');
  await page.locator('.ph-select').selectOption({ index: 2 });
  await page.locator('[data-action=extract]').click();
  await expect(page.locator('.xfields')).toBeVisible();
  await shot(page, '07_crew_report');

  await page.goto('/#/work-orders?case=KRK-T-002');
  await page.getByRole('button', { name: /عبّي نص مقترح|Fill suggested text/ }).click();
  if (MUTATE) {
    await page.getByRole('button', { name: /أنشئ المسودة|Create draft/ }).click();
    await page.waitForTimeout(800);
    await page.getByRole('button', { name: /موافقة|Approve/ }).first().click(); // same engineer -> backend 403
    await page.waitForTimeout(800);
  }
  await shot(page, '08_work_orders');

  await page.goto('/#/map-edits');
  await shot(page, '09_map_edits');

  await page.goto('/#/transparency');
  await expect(page.locator('.counts')).toBeVisible();
  await shot(page, '10_transparency');

  // English toggle flips dir
  await page.getByRole('button', { name: 'toggle language' }).click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'ltr');
  await page.goto('/#/overview');
  await page.waitForSelector('.qitem');
  await shot(page, '11_overview_en');
  await page.getByRole('button', { name: 'toggle language' }).click();
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl');
});

test('crew phone 390', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page, 'insp_1');
  await page.goto('/#/crew');
  await page.waitForSelector('.ph-select');
  await page.locator('.ph-select').selectOption({ index: 2 });
  await page.locator('[data-action=extract]').click();
  await expect(page.locator('.xfields')).toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}\\12_crew_phone_390.png`, fullPage: true });
});
