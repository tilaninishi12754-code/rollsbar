import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Rolls Bar storefront smoke', () => {
  test('homepage loads without uncaught errors', async ({ page }) => {
    const pageErrors = [];
    page.on('pageerror', error => pageErrors.push(error.message));

    await page.goto('/', { waitUntil: 'networkidle' });

    await expect(page.locator('body')).toBeVisible();
    expect(pageErrors).toEqual([]);
  });

  test('all visible product cards expose a purchase action', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const cards = page.locator('.rollsbar-product-card');
    const count = await cards.count();

    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < count; i += 1) {
      const card = cards.nth(i);
      await expect(card.locator('h3')).not.toHaveText('');
      await expect(card.locator('.rollsbar-price')).toBeVisible();
      await expect(card.locator('.rollsbar-product-action')).toBeVisible();
    }
  });

  test('product images either load or use a deliberate placeholder', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const images = page.locator('.rollsbar-product-card__media img');
    const count = await images.count();

    for (let i = 0; i < count; i += 1) {
      const img = images.nth(i);
      await img.scrollIntoViewIfNeeded();

      const result = await img.evaluate(node => ({
        src: node.currentSrc || node.src,
        complete: node.complete,
        naturalWidth: node.naturalWidth
      }));

      expect(result.complete, result.src).toBeTruthy();
      expect(result.naturalWidth, result.src).toBeGreaterThan(0);
    }
  });

  test('a simple product can reach the cart', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const add = page.locator('a.ajax_add_to_cart').first();

    if (await add.count() === 0) {
      test.skip(true, 'No simple product is currently available.');
    }

    await add.click();
    await expect(page.locator('.rollsbar-cart-count').first()).not.toHaveText('0');
  });

  test('search overlay opens', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const open = page.locator('[data-rollsbar-search-open]');
    await open.click();

    await expect(page.locator('#rollsbarProductSearch')).toHaveClass(/open/);
    await expect(page.locator('#rollsbarSearchInput')).toBeFocused();
  });

  test('homepage has no serious or critical axe violations', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const results = await new AxeBuilder({ page }).analyze();
    const blocking = results.violations.filter(item =>
      ['serious', 'critical'].includes(item.impact)
    );

    expect(blocking).toEqual([]);
  });
});

test.describe('Rolls Bar visual checkpoints', () => {
  test('header and utility cards', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    const header = page.locator('.rollsbar-header');
    const utilities = page.locator('.rollsbar-utilities');

    await expect(header).toHaveScreenshot('header.png');
    await expect(utilities).toHaveScreenshot('utilities.png');
  });
});
