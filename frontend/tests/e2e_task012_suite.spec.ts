import { test, expect } from '@playwright/test';

process.env.NO_PROXY = 'localhost,127.0.0.1,::1';
process.env.no_proxy = 'localhost,127.0.0.1,::1';

/**
 * Playwright End-to-End Verification Suite for IOL Task 012:
 * - Real Model Inference vs Test Synthesized Plan Provenance
 * - Unfamiliar Task 1: Comparative Tradeoffs Matrix (Rust vs Go)
 * - Unfamiliar Task 2: Mission Trajectory & Telemetry Tracker
 * - Truthful Unconfigured Fallback (RECIPE_ADAPTED / MODEL_GENERATION_BLOCKED)
 */

test.describe('IOL Task 012 - Model Inference & End-to-End Generative Experience Suite', () => {

  test('Demo 1: Unfamiliar Comparative Matrix displays TEST_SYNTHESIZED badge and criteria rows', async ({ page }) => {
    // 1. Create task with test_mock provider metadata
    const res = await page.request.post('http://127.0.0.1:8000/api/tasks', {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'iol_demo_operator_key',
      },
      data: {
        intent: 'Analyze comparative tradeoffs between Rust memory safety and Go garbage collection concurrency runtimes',
        metadata: { model_provider: 'test_mock' },
      },
    });
    expect(res.ok()).toBeTruthy();
    const taskData = await res.json();
    const taskId = taskData.task_id;

    // 2. Open dashboard loaded directly with task
    await page.goto(`/?task_id=${taskId}`);
    await expect(page.locator(`text=${taskId}`).first()).toBeVisible({ timeout: 15000 });

    // Switch to Adaptive Workspace tab
    const workspaceTab = page.locator('[data-testid="tab-workspace"]');
    await expect(workspaceTab).toBeVisible({ timeout: 15000 });
    await workspaceTab.click();

    // Verify Workspace rendered
    const workspaceRoot = page.locator('[data-testid="experience-workspace-root"]');
    await expect(workspaceRoot).toBeVisible({ timeout: 10000 });

    // Verify Provenance Badge is TEST_SYNTHESIZED (never falsely labeled as MODEL_GENERATED without live model)
    const originBadge = page.locator('[data-testid="plan-origin-badge"]');
    await expect(originBadge).toBeVisible();
    await expect(originBadge).toHaveText('TEST_SYNTHESIZED');

    // Verify Comparison Matrix component is rendered
    const matrixTitle = page.locator('text=Comparative Intelligence: Rust vs Go');
    await expect(matrixTitle).toBeVisible();

    // Verify columns
    await expect(page.locator('th:has-text("Rust")')).toBeVisible();
    await expect(page.locator('th:has-text("Go")')).toBeVisible();
    await expect(page.locator('th:has-text("Architectural Advantage")')).toBeVisible();
  });

  test('Demo 2: Unfamiliar Trajectory Tracker displays orbital stages and telemetry metrics', async ({ page }) => {
    // 1. Create task with test_mock provider metadata
    const res = await page.request.post('http://127.0.0.1:8000/api/tasks', {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'iol_demo_operator_key',
      },
      data: {
        intent: 'Track orbital insertion stages and delta-v telemetry for interplanetary spacecraft trajectory',
        metadata: { model_provider: 'test_mock' },
      },
    });
    expect(res.ok()).toBeTruthy();
    const taskData = await res.json();
    const taskId = taskData.task_id;

    await page.goto(`/?task_id=${taskId}`);
    await expect(page.locator(`text=${taskId}`).first()).toBeVisible({ timeout: 15000 });

    // Switch to Adaptive Workspace tab
    const workspaceTab = page.locator('[data-testid="tab-workspace"]');
    await expect(workspaceTab).toBeVisible({ timeout: 15000 });
    await workspaceTab.click();

    // Verify Workspace rendered
    const workspaceRoot = page.locator('[data-testid="experience-workspace-root"]');
    await expect(workspaceRoot).toBeVisible({ timeout: 15000 });

    // Verify Provenance Badge
    const originBadge = page.locator('[data-testid="plan-origin-badge"]');
    await expect(originBadge).toBeVisible();
    await expect(originBadge).toHaveText('TEST_SYNTHESIZED');

    // Verify Timeline View displays orbital stages
    await expect(page.locator('text=Stage 1: Launch & Trans-Atmospheric Ascent')).toBeVisible();
    await expect(page.locator('text=Stage 4: Orbital Insertion Main Engine Burn (JOI/MOI)')).toBeVisible();

    // Verify Telemetry metric
    await expect(page.locator('text=Target Delta-V')).toBeVisible();
    await expect(page.locator('text=1,240 m/s')).toBeVisible();
  });

  test('Demo 3: Unconfigured Intent safely adapts recipe with RECIPE_ADAPTED badge without false claims', async ({ page }) => {
    // 1. Create task without any model provider credentials/metadata
    const res = await page.request.post('http://127.0.0.1:8000/api/tasks', {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'iol_demo_operator_key',
      },
      data: {
        intent: 'Find AI infrastructure startups in India and build an interactive research database',
        metadata: {},
      },
    });
    expect(res.ok()).toBeTruthy();
    const taskData = await res.json();
    const taskId = taskData.task_id;

    await page.goto(`/?task_id=${taskId}`);
    await expect(page.locator(`text=${taskId}`).first()).toBeVisible({ timeout: 25000 });

    const workspaceTab = page.locator('[data-testid="tab-workspace"]');
    await expect(workspaceTab).toBeVisible({ timeout: 15000 });
    await workspaceTab.click();

    const workspaceRoot = page.locator('[data-testid="experience-workspace-root"]');
    await expect(workspaceRoot).toBeVisible({ timeout: 35000 });

    // Must be RECIPE_ADAPTED
    const originBadge = page.locator('[data-testid="plan-origin-badge"]');
    await expect(originBadge).toBeVisible();
    await expect(originBadge).toHaveText('RECIPE_ADAPTED');
  });

});
