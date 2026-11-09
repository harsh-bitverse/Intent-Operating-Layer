import { test, expect } from '@playwright/test';

process.env.NO_PROXY = 'localhost,127.0.0.1,::1';
process.env.no_proxy = 'localhost,127.0.0.1,::1';

test.describe('IOL v0.6 - Experience Engine Verification Suite', () => {

  // ---------------------------------------------------------------------------
  // Demo A: Autonomous Research Workspace
  // ---------------------------------------------------------------------------
  test('Demo A: Research Workspace with full-screen adaptive grid, search, and evidence drawer', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Core Online')).toBeVisible({ timeout: 15000 });

    // Submit Research Mission
    const intent = 'Find 3 AI infrastructure startups in India and build an interactive research database';
    await page.fill('[data-testid="intent-input"]', intent);
    await page.click('[data-testid="submit-intent-btn"]');

    // Wait for task creation
    const taskItem = page.locator('[data-testid^="task-item-"]').first();
    await expect(taskItem).toBeVisible({ timeout: 15000 });
    await taskItem.click();

    // Verify Adaptive Workspace Tab is active
    const workspaceTab = page.locator('[data-testid="tab-workspace"]');
    await expect(workspaceTab).toBeVisible({ timeout: 15000 });
    await workspaceTab.click();

    // Verify Full Workspace mode badge
    await expect(page.locator('[data-testid="workspace-mode-badge"]')).toContainText('FULL WORKSPACE', { timeout: 15000 });

    // Wait for completion or verified records
    await expect(page.locator('text=COMPLETED').first()).toBeVisible({ timeout: 45000 });

    // Verify Metric Strip
    const metricStrip = page.locator('[data-testid="experience-metric-strip"]');
    await expect(metricStrip).toBeVisible();

    // Verify Workspace Data Grid
    const dataGrid = page.locator('[data-testid="workspace-data-grid"]');
    await expect(dataGrid).toBeVisible();

    // Verify Search Filter in Data Grid
    const searchInput = page.locator('[data-testid="workspace-search-input"]');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('Sarvam');
    // Clear search
    await searchInput.fill('');

    // Inspect Field-Level Evidence Drawer on row click
    const firstRow = page.locator('[data-testid="row-0"]');
    await expect(firstRow).toBeVisible();
    await firstRow.click();

    const evidenceDrawer = page.locator('[data-testid="evidence-drawer"]');
    await expect(evidenceDrawer).toBeVisible();
    await expect(evidenceDrawer.locator('text=Field-Level Provenance & Verification')).toBeVisible();

    // Take screenshot of Demo A
    await page.screenshot({ path: '../docs/screenshots/v06_demo_a_research_workspace.png', fullPage: true });

    // Verify CSV Export Button
    const exportCsvBtn = page.locator('[data-testid="export-csv-btn"]');
    await expect(exportCsvBtn).toBeVisible();
    await expect(exportCsvBtn).toBeEnabled();
  });

  // ---------------------------------------------------------------------------
  // Demo B: Interactive 2D Neural Network Learning Simulation
  // ---------------------------------------------------------------------------
  test('Demo B: Educational explanation with interactive 2D node-edge canvas and step controller', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Core Online')).toBeVisible({ timeout: 15000 });

    // Submit Educational Mission
    const intent = 'Teach me how a neural network learns using an interactive 2D visualization';
    await page.fill('[data-testid="intent-input"]', intent);
    await page.click('[data-testid="submit-intent-btn"]');

    // Wait for task creation
    const taskItem = page.locator('[data-testid^="task-item-"]').first();
    await expect(taskItem).toBeVisible({ timeout: 10000 });

    // Switch to Adaptive Workspace tab
    const workspaceTab = page.locator('[data-testid="tab-workspace"]');
    await expect(workspaceTab).toBeVisible({ timeout: 10000 });
    await workspaceTab.click();

    // Wait for execution completion
    await expect(page.locator('text=COMPLETED').first()).toBeVisible({ timeout: 30000 });

    // Verify Interactive 2D Canvas is rendered
    const canvasContainer = page.locator('[data-testid="interactive-canvas-2d"]');
    await expect(canvasContainer).toBeVisible({ timeout: 10000 });

    // Verify SVG Architecture elements exist
    await expect(canvasContainer.getByText('INPUT LAYER', { exact: true })).toBeVisible();
    await expect(canvasContainer.getByText('HIDDEN LAYER', { exact: true })).toBeVisible();
    await expect(canvasContainer.getByText('OUTPUT LAYER', { exact: true })).toBeVisible();

    // Verify Step Controller buttons
    const stepForwardBtn = page.locator('[data-testid="sim-step-forward"]');
    const stepBackBtn = page.locator('[data-testid="sim-step-back"]');
    const autoPlayBtn = page.locator('[data-testid="sim-autoplay"]');
    const resetBtn = page.locator('[data-testid="sim-reset"]');

    await expect(stepForwardBtn).toBeVisible();
    await expect(autoPlayBtn).toBeVisible();

    // Step through the mathematical explanation
    await stepForwardBtn.click();
    await expect(canvasContainer.locator('text=Step 2 of 5')).toBeVisible();

    await stepForwardBtn.click();
    await expect(canvasContainer.locator('text=Step 3 of 5')).toBeVisible();

    // Verify mathematical formula is displayed
    await expect(canvasContainer.locator('text=Formula:')).toBeVisible();

    // Step backward
    await stepBackBtn.click();
    await expect(canvasContainer.locator('text=Step 2 of 5')).toBeVisible();

    // Reset to step 1
    await resetBtn.click();
    await expect(canvasContainer.locator('text=Step 1 of 5')).toBeVisible();

    // Take screenshot of Demo B
    await page.screenshot({ path: '../docs/screenshots/v06_demo_b_neural_simulation.png', fullPage: true });
  });

  // ---------------------------------------------------------------------------
  // Full-Screen Workspace Toggle
  // ---------------------------------------------------------------------------
  test('Full-Screen Workspace mode expands and collapses cleanly', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Core Online')).toBeVisible({ timeout: 15000 });

    // Submit intent
    const intent = 'Find AI infrastructure startups in India and build an interactive research database';
    await page.fill('[data-testid="intent-input"]', intent);
    await page.click('[data-testid="submit-intent-btn"]');

    // Switch to Adaptive Workspace tab
    await page.click('[data-testid="tab-workspace"]');
    await expect(page.locator('[data-testid="experience-workspace-root"]')).toBeVisible({ timeout: 15000 });

    // Toggle Fullscreen
    const toggleBtn = page.locator('[data-testid="workspace-fullscreen-toggle"]');
    await expect(toggleBtn).toBeVisible();
    await toggleBtn.click();
    await expect(toggleBtn).toContainText('Exit Fullscreen');

    // Toggle back
    await toggleBtn.click();
    await expect(toggleBtn).toContainText('Full Workspace');
  });

});
