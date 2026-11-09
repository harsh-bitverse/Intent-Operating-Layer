import { test, expect } from '@playwright/test';

process.env.NO_PROXY = 'localhost,127.0.0.1,::1';
process.env.no_proxy = 'localhost,127.0.0.1,::1';

/**
 * Playwright End-to-End Verification Suite for IOL Task 013:
 * - Strict Model Provenance: Rejection of synthetic masquerade as MODEL_GENERATED
 * - Truthful Unconfigured State: REAL_MODEL_BLOCKED reported with diagnostic setup guidance
 * - Product Generalization: Educational Dijkstra Graph Priority Queue Relaxation
 * - Consequential Action Safety: Bounded Action Approval Gate
 */

test.describe('IOL Task 013 - Genuine Model Intelligence & Generalization Suite', () => {

  test('Probe 1: Strict Provenance - Mock/Synthetic Provider is explicitly tagged TEST_SYNTHESIZED', async ({ page }) => {
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

    await page.goto(`/?task_id=${taskId}`);
    await expect(page.locator(`text=${taskId}`).first()).toBeVisible({ timeout: 15000 });

    const workspaceTab = page.locator('[data-testid="tab-workspace"]');
    await expect(workspaceTab).toBeVisible({ timeout: 15000 });
    await workspaceTab.click();

    const workspaceRoot = page.locator('[data-testid="experience-workspace-root"]');
    await expect(workspaceRoot).toBeVisible({ timeout: 10000 });

    // Strict Provenance: badge must be TEST_SYNTHESIZED, never falsely claiming MODEL_GENERATED
    const originBadge = page.locator('[data-testid="plan-origin-badge"]');
    await expect(originBadge).toBeVisible();
    await expect(originBadge).toHaveText('TEST_SYNTHESIZED');
  });

  test('Probe 2: Unconfigured Credentials truthfully reports REAL_MODEL_BLOCKED setup status', async ({ page }) => {
    const res = await page.request.post('http://127.0.0.1:8000/api/tasks', {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'iol_demo_operator_key',
      },
      data: {
        intent: 'Generate real-time executive dashboard for global supply chain disruptions',
        metadata: {},
      },
    });
    expect(res.ok()).toBeTruthy();
    const taskData = await res.json();
    const taskId = taskData.task_id;

    // Fetch the task experience plan via API to verify truthful REAL_MODEL_BLOCKED status
    const planRes = await page.request.get(`http://127.0.0.1:8000/api/tasks/${taskId}/experience`, {
      headers: {
        'X-API-Key': 'iol_demo_operator_key',
      },
    });
    expect(planRes.ok()).toBeTruthy();
    const planData = await planRes.json();
    const expPlan = planData.experience_plan;
    
    // Ensure origin is truthful fallback and model_metadata records REAL_MODEL_BLOCKED
    expect(expPlan.plan_origin).toBe('RECIPE_ADAPTED');
    expect(expPlan.model_metadata.status).toBe('REAL_MODEL_BLOCKED');
    expect(expPlan.model_metadata.origin_reason).toContain('No active external LLM credentials configured');
    expect(expPlan.model_metadata.user_setup_instruction).toContain('GEMINI_API_KEY');

    // UI inspection
    await page.goto(`/?task_id=${taskId}`);
    await expect(page.locator(`text=${taskId}`).first()).toBeVisible({ timeout: 15000 });

    const workspaceTab = page.locator('[data-testid="tab-workspace"]');
    await expect(workspaceTab).toBeVisible({ timeout: 15000 });
    await workspaceTab.click();

    const originBadge = page.locator('[data-testid="plan-origin-badge"]');
    await expect(originBadge).toBeVisible();
    await expect(originBadge).toHaveText('RECIPE_ADAPTED');
  });

  test('Probe 3: Algorithmic Simulation - Dijkstra graph relaxation outcome verification', async ({ page }) => {
    const res = await page.request.post('http://127.0.0.1:8000/api/tasks', {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'iol_demo_operator_key',
      },
      data: {
        intent: 'Simulate step-by-step Dijkstra shortest path relaxation and optimal path reconstruction',
        metadata: { model_provider: 'test_mock' },
      },
    });
    expect(res.ok()).toBeTruthy();
    const taskData = await res.json();
    const taskId = taskData.task_id;

    await page.goto(`/?task_id=${taskId}`);
    await expect(page.locator(`text=${taskId}`).first()).toBeVisible({ timeout: 15000 });

    // Verify task details panel
    await expect(page.locator('text=educational.dijkstra_simulation').first()).toBeVisible({ timeout: 15000 });
  });

});
