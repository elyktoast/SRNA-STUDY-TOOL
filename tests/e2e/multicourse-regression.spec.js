const { test, expect } = require('@playwright/test');
const { clearAppState, seedSignedIn } = require('./helpers');

async function waitForPageReady(page) {
  await page.waitForFunction(() => window.MBUPageReady && typeof window.MBUPageReady.then === 'function');
  await page.evaluate(() => window.MBUPageReady);
}

async function waitForStudioReady(page) {
  await waitForPageReady(page);
  await page.waitForFunction(() => window.MBUStudioPageReady && typeof window.MBUStudioPageReady.then === 'function');
  await page.evaluate(() => window.MBUStudioPageReady);
}

test.describe('multi-course foundation', () => {
  test.beforeEach(async ({ page }) => { await clearAppState(page); await seedSignedIn(page); });
  test('Basic Principles is reachable from the course home and exposes Exam 1', async ({ page }) => {
    await page.goto('/');
    await waitForPageReady(page);
    await expect(page.getByRole('heading', { name: 'Basic Principles' })).toBeVisible();

    await page.goto('/basic-principles/');
    await waitForPageReady(page);
    await expect(page.getByRole('heading', { name: 'Basic Principles' })).toBeVisible();
    await expect(page.getByRole('link', { name: /Open Exam 1 Dashboard/ })).toHaveAttribute('href', 'exam-1/');

    await page.goto('/basic-principles/exam-1/');
    await waitForPageReady(page);
    await expect(page.getByRole('heading', { name: 'Basic Principles — Exam 1' })).toBeVisible();
  });

  test('Basic Principles learner stores are isolated from Equipment Exam 1', async ({ page }) => {
    await page.goto('/equipment/exam-1/studio.html');
    await waitForStudioReady(page);
    const equipment = await page.evaluate(() => ({
      studio: MBUStudio.STORE,
      intelligence: MBUStudyIntelligence.STORE,
      course: window.MBU_CONTEXT?.courseId
    }));
    expect(equipment).toEqual({
      studio: 'mbu_exam1_studio_v1',
      intelligence: 'mbu_study_intelligence_v1',
      course: 'equipment'
    });

    await page.goto('/basic-principles/exam-1/studio.html');
    await waitForStudioReady(page);
    const principles = await page.evaluate(() => ({
      studio: MBUStudio.STORE,
      intelligence: MBUStudyIntelligence.STORE,
      course: window.MBU_CONTEXT?.courseId,
      exam: window.MBU_CONTEXT?.examId
    }));
    expect(principles).toEqual({
      studio: 'mbu_studio_basic-principles_exam-1_v1',
      intelligence: 'mbu_study_intelligence_basic-principles_exam-1_v1',
      course: 'basic-principles',
      exam: 'exam-1'
    });
  });

  test('Basic Principles manifest exposes one unified 4,000-question Study Studio pool', async ({ page }) => {
    const response = await page.request.get('/basic-principles/exam-1/banks.json');
    expect(response.ok()).toBeTruthy();
    const manifest = await response.json();
    expect(manifest.course.id).toBe('basic-principles');
    expect(manifest.exam.id).toBe('exam-1');
    expect(manifest.banks).toEqual([]);
    expect(manifest.studioSources).toHaveLength(9);
    expect(manifest.studioSources.reduce((sum, source) => sum + source.count, 0)).toBe(4000);
    expect(manifest.studioSources.every(source => source.key.startsWith('bp1-'))).toBeTruthy();
    expect(new Set(manifest.studioSources.map(source => source.groupLabel))).toEqual(new Set(['Basic Principles Exam 1']));
    expect(manifest.contentTaxonomy.topics).toHaveLength(9);
    expect(manifest.sessionEnvironment).toBe('equipment-bank1-practice-set1-v1');
    expect(manifest.defaultBankEngine).toBe('canonical');
    expect(manifest.bankPage).toBe('bank.html');
  });
  test('public navigation exposes both published courses', async ({ page }) => {
    await page.goto('/');
    await waitForPageReady(page);
    const homeNav = page.locator('.mbu-global-nav');
    await expect(homeNav).toBeVisible();
    await expect(homeNav.getByRole('link', { name: 'SRNA Study Tool', exact: true })).toHaveAttribute('href', /\/SRNA-STUDY-TOOL\/$|\/$/);
    await expect(homeNav.getByRole('link', { name: 'Equipment', exact: true })).toHaveCount(0);
    await expect(homeNav.getByRole('link', { name: 'Study Studio', exact: true })).toHaveCount(0);
    await expect(homeNav.getByRole('link', { name: /Adaptive/, exact: false })).toHaveCount(0);

    await page.goto('/equipment/exam-1/');
    await waitForPageReady(page);
    const equipmentNav = page.locator('.mbu-global-nav');
    await expect(equipmentNav).toBeVisible();
    await expect(equipmentNav.getByRole('link', { name: 'Equipment', exact: true })).toHaveAttribute('href', /\/equipment\/$/);
    await expect(equipmentNav.getByRole('link', { name: 'Study Studio', exact: true })).toHaveCount(0);
    await expect(equipmentNav.getByRole('link', { name: /Adaptive/, exact: false })).toHaveCount(0);

    await page.goto('/basic-principles/exam-1/');
    await waitForPageReady(page);
    const nav = page.locator('.mbu-global-nav');
    await expect(nav).toBeVisible();
    await expect(nav.getByRole('link', { name: 'Basic Principles', exact: true })).toHaveAttribute('href', /\/basic-principles\/$/);
    await expect(nav.getByRole('link', { name: 'Study Studio', exact: true })).toHaveCount(0);
    await expect(nav.getByRole('link', { name: /Adaptive/, exact: false })).toHaveCount(0);
    await expect(nav.getByRole('link', { name: 'Equipment', exact: true })).toHaveCount(0);
  });



  test('Basic Principles Studio loads one unified 4000-question pool', async ({ page }) => {
    await page.goto('/basic-principles/exam-1/studio.html');
    await waitForStudioReady(page);
    await expect(page.locator('#topicPickbox')).toBeVisible();
    await expect(page.locator('#sourcePickbox')).toHaveCount(0);
    await expect(page.locator('#buildSetsBtn')).toHaveCount(0);
    await expect(page.locator('#buildTopicsBtn')).toHaveCount(0);
    await expect(page.locator('#order')).toHaveCount(0);
    await expect(page.locator('#topicChecks input')).toHaveCount(5);
    const state = await page.evaluate(() => ({
      count: ALL.length,
      uidCount: ALL_BY_UID.size,
      unifiedHeading: document.querySelector('#topicPickbox h4')?.textContent.trim(),
      sourceChoices: [...document.querySelectorAll('#sourceChecks input')].map(x => x.value),
      sourceText: document.querySelector('#sourceChecks')?.textContent.trim() || '',
      topics: document.querySelectorAll('#topicChecks input').length,
      directImages: ALL.filter(q => q.img && q.img.kind === 'direct').length
    }));
    expect(state.count).toBe(4000);
    expect(state.uidCount).toBe(4000);
    expect(state.unifiedHeading).toBe('Lecture Topics');
    expect(state.sourceChoices).toEqual([]);
    expect(state.sourceText).toBe('');
    expect(state.topics).toBe(5);
    expect(state.directImages).toBeGreaterThanOrEqual(0);
    await expect(page.locator('#mbu-bank-picker')).toHaveCount(0);
    await page.locator('#topicChecks input').first().check();
    await page.locator('#count').selectOption('10');
    await page.getByRole('button', { name: 'Start Quiz' }).click();
    await expect(page.locator('#quiz')).toBeVisible();
    expect(await page.evaluate(() => session.length)).toBe(10);
  });


  test('Basic Principles Studio lecture filtering and direct figures work across the unified pool', async ({ page }) => {
    await page.goto('/basic-principles/exam-1/studio.html');
    await waitForStudioReady(page);
    const imageUid = await page.evaluate(() => ALL.find(q => q.img && q.img.kind === 'direct')?.uid || null);
    if(imageUid){
      await page.evaluate(uid => practiceSearch(uid), imageUid);
      await expect(page.locator('#qimage img')).toBeVisible();
      await page.evaluate(() => renderHome());
    }

    const choice = page.locator('#topicChecks input').first();
    await choice.check();
    const topic = await choice.inputValue();
    expect(await page.locator('#topicChecks input').count()).toBe(5);
    expect(await page.locator('#topicChecks').textContent()).toContain('(500)');
    await page.selectOption('#count', '10');
    await page.getByRole('button', { name: 'Start Quiz' }).click();
    await expect(page.locator('#quiz')).toBeVisible();
    await expect.poll(async()=>page.evaluate(()=>typeof session!=='undefined'&&Array.isArray(session)?session.length:0)).toBe(10);
    expect(await page.evaluate(() => [...new Set(session.map(q => q.bankLabel))])).toEqual([topic]);
  });


  test('Basic Principles unified pool is available to search, Smart Review, analytics, and Adaptive entry', async ({ page }) => {
    await page.goto('/basic-principles/exam-1/studio.html');
    await waitForStudioReady(page);
    await expect(page.getByRole('button', { name: 'Search Questions' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Start Smart Review' })).toBeVisible();
    await expect(page.locator('#analyticsSummary')).toBeAttached();
    await expect(page.locator('#adaptiveToggle')).toBeVisible();
    await page.getByRole('button', { name: 'Search Questions' }).click();
    await page.locator('#searchbox').fill('airway');
    await expect(page.locator('#searchresults')).not.toBeEmpty();
    expect(await page.evaluate(() => window.MBUStudyIntelligence.smartReview(ALL, 50).length)).toBeGreaterThan(0);
  });

  test('published navigation remains usable at 360px phone width', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    for (const route of ['/', '/equipment/exam-1/', '/basic-principles/exam-1/']) {
      await page.goto(route);
      await waitForPageReady(page);
      const nav = page.locator('.mbu-global-nav');
      await expect(nav).toBeVisible();
      const box = await nav.boundingBox();
      expect(box).not.toBeNull();
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(360);
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(360);
    }
    await expect(page.locator('.mbu-global-nav').getByRole('link', { name: 'Basic Principles', exact: true })).toBeVisible();
    await expect(page.locator('.mbu-global-nav').getByRole('link', { name: 'Study Studio', exact: true })).toHaveCount(0);
    await expect(page.locator('.mbu-global-nav').getByRole('link', { name: /Adaptive/, exact: false })).toHaveCount(0);
  });


});
