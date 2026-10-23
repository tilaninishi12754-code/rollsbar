import { chromium } from '@playwright/test';
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';

// Inspect real fixture text, never substitute a font or inject presentation CSS.
export async function verifyEnvironment(config) {
  const use = { ...config.use, ...config.projects[0].use };
  const { browserName, headless, trace, ...contextOptions } = use;
  const require = createRequire(import.meta.url);
  const testRequire = createRequire(require.resolve('@playwright/test/package.json'));
  const playwrightRequire = createRequire(testRequire.resolve('playwright/package.json'));
  const core = dirname(playwrightRequire.resolve('playwright-core/package.json'));
  const revision = JSON.parse(readFileSync(join(core, 'browsers.json'))).browsers
    .find(b => b.name === 'chromium-headless-shell').revision;
  const evidence = {
    playwright: require('@playwright/test/package.json').version,
    revision,
    viewports: config.projects.map(p => p.use.viewport),
    dpr: use.deviceScaleFactor,
    fonts: [], status: 'FAIL'
  };
  let browser;
  try {
    browser = await chromium.launch({ headless });
    evidence.chromium = browser.version();
    const context = await browser.newContext(contextOptions);
    const page = await context.newPage();
    await page.route('**/*', r => new URL(r.request().url()).hostname === '127.0.0.1' ? r.continue() : r.abort());
    await page.goto('http://127.0.0.1:4178/current/');
    await page.locator('.rollsbar-product-grid').first().waitFor();
    await page.evaluate(() => document.fonts.ready);
    const cdp = await context.newCDPSession(page);
    await cdp.send('DOM.enable');
    await cdp.send('CSS.enable');
    const { root } = await cdp.send('DOM.getDocument');
    for (const [role, selector, weight] of [
      ['normal', '.rollsbar-footer p', '400'],
      ['price', '.rollsbar-price bdi', '700']
    ]) {
      const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector });
      if (!nodeId) throw Error(`Missing representative ${role} text: ${selector}`);
      const computed = await page.locator(selector).first().evaluate(n => {
        const s = getComputedStyle(n);
        return { stack: s.fontFamily, weight: s.fontWeight, text: n.textContent.trim().slice(0, 80) };
      });
      const { fonts } = await cdp.send('CSS.getPlatformFontsForNode', { nodeId });
      const selected = fonts.filter(f => f.glyphCount > 0);
      evidence.fonts.push({ role, selector, ...computed, selected });
      if (computed.weight !== weight || !selected.length || selected.some(f =>
        f.isCustomFont || !['Segoe UI', 'Segoe UI Black'].includes(f.familyName))) {
        throw Error(`Protected baseline requires Segoe UI rendering; ${role} selected ${selected.map(f => f.familyName).join(', ') || 'no platform font'} (weight ${computed.weight}). Run npm run visual-test through the canonical RollsBar Codex Windows sandbox profile (use_default), not the host-user/escalated profile. Do not change fonts or baselines.`);
      }
    }
    if (evidence.playwright !== '1.64.1' || evidence.chromium !== '156.0.8078.4' || revision !== '1248' || use.deviceScaleFactor !== 1 || evidence.viewports.some(v => v.height !== 900)) {
      throw Error('Protected runtime contract requires Playwright 1.64.1, Chromium 156.0.8078.4/revision 1248, height 900 and DPR 1.');
    }
    evidence.status = 'PASS';
  } catch (error) {
    evidence.error = error.message;
    throw Error(`VISUAL ENVIRONMENT FAIL: ${error.message}`);
  } finally {
    await browser?.close();
    mkdirSync('qa/visual-results/environment', { recursive: true });
    writeFileSync('qa/visual-results/environment/latest.json', JSON.stringify(evidence, null, 2) + '\n');
    console.log(`VISUAL ENVIRONMENT ${evidence.status}: Playwright ${evidence.playwright}; Chromium ${evidence.chromium ?? 'unavailable'}/r${revision}; widths ${evidence.viewports.map(v => v.width).join(',')} ×900/DPR${evidence.dpr}; ${evidence.fonts.map(f => `${f.role}=${f.selected.map(x => `${x.familyName}/${x.postScriptName}`).join('+')}`).join('; ')}`);
  }
}

// Global setup also protects direct Playwright CLI invocations, before workers start.
export default async function environmentSetup(config) {
  if (process.env.ROLLSBAR_BASELINE === '1') return; // Explicit, separate baseline generation.
  if (config.updateSnapshots !== 'none') throw Error('Protected test mode forbids snapshot updates.');
  await verifyEnvironment(config);
}
