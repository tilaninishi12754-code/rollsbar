import { test, expect } from '@playwright/test';

function deep(page) {
  return page.frameLocator('#stage').frameLocator('#site');
}

async function waitForSite(page) {
  await page.goto('/demo.html', { waitUntil: 'domcontentloaded' });
  const site = deep(page);
  await expect(site.locator('body')).toHaveAttribute('data-client-fixes-v3', '1');
  await expect(site.locator('.product-card').first()).toBeVisible();
  return site;
}

async function dismissCookieNotice(site) {
  const banner = site.locator('#cookieBanner');
  if (await banner.count() && await banner.evaluate(el => el.classList.contains('show'))) {
    await site.locator('#cookieAccept').click();
    await expect(banner).not.toHaveClass(/show/);
  }
}

async function openVisibleCart(site) {
  const clientBar = site.locator('.client-order-bar').first();
  const desktopCart = site.locator('.cart-button[data-cart-open]').first();
  const mobileCart = site.locator('.mobile-cart[data-cart-open]').first();

  await expect.poll(async () => {
    if (await clientBar.isVisible()) return 'client';
    if (await desktopCart.isVisible()) return 'desktop';
    if (await mobileCart.isVisible()) return 'mobile';
    return '';
  }, { timeout: 5000 }).not.toBe('');

  if (await clientBar.isVisible()) {
    await clientBar.click();
  } else if (await desktopCart.isVisible()) {
    await desktopCart.click();
  } else {
    await mobileCart.click();
  }

  await expect(site.locator('#cartDrawer')).toHaveClass(/open/);
}

test.describe('Rolls Bar pre-WordPress approved/static audit', () => {
  test('catalog invariant and four utility cards are present', async ({ page }) => {
    const site = await waitForSite(page);

    const stats = await site.locator('body').evaluate(() => {
      const products = window.rollsBarProducts || [];
      const sourceRows = products.reduce((sum, p) => sum + (Array.isArray(p.variants) && p.variants.length ? p.variants.length : 1), 0);
      return { cards: products.length, sourceRows };
    });

    expect(stats).toEqual({ cards: 118, sourceRows: 131 });
    await expect(site.locator('.client-story')).toHaveCount(4);
    await expect(site.locator('.client-story--work')).toContainText('Работа в Rolls Bar');
  });

  test('missing-image product detail never covers purchase controls', async ({ page }) => {
    const site = await waitForSite(page);
    await dismissCookieNotice(site);

    const product = await site.locator('body').evaluate(() => {
      const products = window.rollsBarProducts || [];
      return products.find(p =>
        !p.img &&
        typeof p.vkRow !== 'number' &&
        !(Array.isArray(p.variants) && p.variants.length) &&
        !(Array.isArray(p.options) && p.options.length)
      ) || null;
    });

    expect(product, 'Need at least one simple product without an image to exercise the regression').not.toBeNull();

    const original = site.locator('[data-original-add="' + product.id + '"]').first();
    const card = original.locator('xpath=ancestor::article[contains(@class,"product-card")]');
    await card.locator('h3').click();

    const modal = site.locator('#productDetailModal');
    await expect(modal).toHaveClass(/open/);
    await expect(site.locator('#productDetailTitle')).toHaveText(product.name);
    const detailAdd = site.locator('#productDetailAdd');
    await detailAdd.scrollIntoViewIfNeeded();
    await expect(detailAdd).toBeVisible();

    const geometry = await modal.evaluate((root) => {
      const media = root.querySelector('.product-detail-modal__media');
      const fallback = root.querySelector('.product-fallback');
      const add = root.querySelector('#productDetailAdd');
      if (!media || !fallback || !add) return null;
      const m = media.getBoundingClientRect();
      const f = fallback.getBoundingClientRect();
      const a = add.getBoundingClientRect();
      const cx = a.left + a.width / 2;
      const cy = a.top + a.height / 2;
      const top = document.elementFromPoint(cx, cy);
      return {
        fallbackContained: f.left >= m.left - 1 && f.right <= m.right + 1 && f.top >= m.top - 1 && f.bottom <= m.bottom + 1,
        purchaseControlOnTop: !!top && (top === add || add.contains(top))
      };
    });

    expect(geometry).not.toBeNull();
    expect(geometry.fallbackContained).toBeTruthy();
    expect(geometry.purchaseControlOnTop).toBeTruthy();
  });

  test('simple product can be added and cart opens', async ({ page }) => {
    const site = await waitForSite(page);
    await dismissCookieNotice(site);
    const plus = site.locator('[data-client-plus]').first();
    await expect(plus).toBeVisible();
    await plus.click();

    await expect.poll(async () => site.locator('body').evaluate(() => {
      const count = document.querySelector('.cart-count');
      return Number(String(count?.textContent || '0').replace(/\D/g, '') || 0);
    })).toBeGreaterThan(0);

    await openVisibleCart(site);
    await expect(site.locator('#checkoutOpen')).toBeVisible();
  });

  test('checkout preserves latest client corrections', async ({ page }) => {
    const site = await waitForSite(page);
    await dismissCookieNotice(site);

    await site.locator('[data-client-plus]').first().click();
    await openVisibleCart(site);
    await site.locator('#checkoutOpen').click();

    await expect(site.locator('#checkoutModal')).toHaveClass(/open/);

    const phone = site.locator('#phoneField');
    await expect(phone).toHaveValue(/^\+7/);

    await expect(site.locator('#clientDeliveryZone')).toHaveCount(0);
    await expect(site.locator('select').filter({ hasText: 'Выберите зону' })).toHaveCount(0);

    for (const name of ['address', 'entrance', 'door_code', 'floor', 'apartment']) {
      await expect(site.locator('[name="' + name + '"]')).toHaveCount(1);
    }

    await expect(site.locator('#checkoutSchematicMap')).toBeVisible();
    await expect(site.locator('#checkoutMapMarker')).toBeVisible();
  });

  test('mobile sticky cart does not cover cart or checkout UI', async ({ page }) => {
    const viewport = page.viewportSize();
    test.skip(!viewport || viewport.width > 700, 'mobile-only regression');

    const site = await waitForSite(page);
    await dismissCookieNotice(site);
    await site.locator('[data-client-plus]').first().click();

    const bar = site.locator('.client-order-bar');
    await expect(bar).toHaveClass(/show/);

    await bar.click();
    await expect(site.locator('#cartDrawer')).toHaveClass(/open/);
    await expect(bar).not.toHaveClass(/show/);

    await site.locator('#checkoutOpen').click();
    await expect(site.locator('#checkoutModal')).toHaveClass(/open/);
    await expect(bar).not.toHaveClass(/show/);
  });

  test('search finds known product', async ({ page }) => {
    const site = await waitForSite(page);
    await site.locator('[data-search-open]').click();
    await expect(site.locator('#productSearch')).toHaveClass(/open/);

    const input = site.locator('#productSearchInput');
    await input.fill('Филадельфия');
    await expect(site.locator('.search-result').first()).toBeVisible();
  });

  test('core local pages return successful HTTP responses', async ({ request }) => {
    const pages = [
      '/vacancies.html',
      '/reviews.html',
      '/delivery-payment.html',
      '/offer.html',
      '/payment-refund.html',
      '/payment-security.html',
      '/privacy.html',
      '/consent.html',
      '/cookies.html',
      '/requisites.html'
    ];

    for (const path of pages) {
      const response = await request.get(path);
      expect(response.ok(), path + ' should return 2xx').toBeTruthy();
    }
  });

  test('cookie notice can be dismissed and stays out of critical controls', async ({ page }) => {
    const site = await waitForSite(page);
    const banner = site.locator('#cookieBanner');
    await expect(banner).toHaveClass(/show/);
    await site.locator('#cookieAccept').click();
    await expect(banner).not.toHaveClass(/show/);
  });

  test('no uncaught page errors during initial render', async ({ page }) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await waitForSite(page);
    await page.waitForTimeout(1500);
    expect(errors).toEqual([]);
  });
});
