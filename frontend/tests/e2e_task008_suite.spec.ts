import { test, expect } from '@playwright/test';

process.env.NO_PROXY = 'localhost,127.0.0.1,::1';
process.env.no_proxy = 'localhost,127.0.0.1,::1';

test.describe('IOL Task 008 - Browser Execution, Form Draft & Scoped Action Approvals', () => {

  // ---------------------------------------------------------------------------
  // Test 1: Real Browser Navigation, Extraction & Telemetry
  // ---------------------------------------------------------------------------
  test('Demo 1: Real Browser Navigation to public website with screenshot and element telemetry', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Core Online')).toBeVisible({ timeout: 15000 });

    // Submit Browser Navigation Mission
    const intent = 'Navigate to https://example.com and extract documentation links and headings';
    await page.fill('[data-testid="intent-input"]', intent);
    await page.click('[data-testid="submit-intent-btn"]');

    // Wait for task creation
    const taskItem = page.locator('[data-testid^="task-item-"]').first();
    await expect(taskItem).toBeVisible({ timeout: 10000 });

    // Switch to Adaptive Workspace tab
    const workspaceTab = page.locator('[data-testid="tab-workspace"]');
    await expect(workspaceTab).toBeVisible({ timeout: 10000 });
    await workspaceTab.click();

    // Wait for task completion
    await expect(page.locator('text=COMPLETED').first()).toBeVisible({ timeout: 45000 });

    // Verify Adaptive Workspace is rendered
    await expect(page.locator('[data-testid="experience-workspace-root"]')).toBeVisible();

    // Verify Data Grid or Telemetry rendered with extracted page links/elements
    const dataGrid = page.locator('[data-testid="workspace-data-grid"]');
    await expect(dataGrid).toBeVisible();

    // Take screenshot of verified Browser Demo
    await page.screenshot({ path: '../docs/screenshots/v08_demo1_browser_extraction.png', fullPage: true });

    // Verify Replay Bundle Export button is visible and active
    const replayBundleBtn = page.locator('[data-testid="export-replay-bundle-btn"]');
    await expect(replayBundleBtn).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // Test 2: Public Service Form Draft (OutcomeShape.FORM)
  // ---------------------------------------------------------------------------
  test('Demo 4: Public service form draft with LOCAL_DRAFT safety badge and official handoff', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Core Online')).toBeVisible({ timeout: 15000 });

    // Submit Form Draft Mission
    const intent = 'Draft a public passport renewal application form with required applicant fields';
    await page.fill('[data-testid="intent-input"]', intent);
    await page.click('[data-testid="submit-intent-btn"]');

    // Wait for task creation
    const taskItem = page.locator('[data-testid^="task-item-"]').first();
    await expect(taskItem).toBeVisible({ timeout: 10000 });

    // Switch to Adaptive Workspace tab
    const workspaceTab = page.locator('[data-testid="tab-workspace"]');
    await expect(workspaceTab).toBeVisible({ timeout: 10000 });
    await workspaceTab.click();

    // Wait for task completion
    await expect(page.locator('text=COMPLETED').first()).toBeVisible({ timeout: 35000 });

    // Verify Form Draft container rendered
    const formContainer = page.locator('[data-testid="form-draft-container"]');
    await expect(formContainer).toBeVisible({ timeout: 10000 });

    // Verify LOCAL_DRAFT safety status badge
    await expect(page.locator('[data-testid="form-draft-status-badge"]')).toContainText('LOCAL_DRAFT');

    // Verify Copy Draft button
    const copyBtn = page.locator('[data-testid="copy-form-draft-btn"]');
    await expect(copyBtn).toBeVisible();

    // Take screenshot of Form Draft Demo
    await page.screenshot({ path: '../docs/screenshots/v08_demo4_form_draft.png', fullPage: true });
  });

  // ---------------------------------------------------------------------------
  // Test 3: Scoped Consequential Action Approval Lifecycle
  // ---------------------------------------------------------------------------
  test('Action Approval: Pauses on consequential action, displays approval panel, and resumes on approve', async ({ page, request }) => {
    await page.goto('/');
    await expect(page.locator('text=Core Online')).toBeVisible({ timeout: 15000 });

    // 1. Create a task via API to test action approval interaction
    const createRes = await request.post('http://127.0.0.1:8000/api/tasks', {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'iol_demo_operator_key'
      },
      data: {
        intent: 'Test external write action approval lifecycle',
        budget: { max_duration_seconds: 60, max_steps: 5, max_cost_usd: 1.0, retry_limit: 1 },
        metadata: { user_id: 'test_operator' }
      }
    });
    expect(createRes.status()).toBe(201);
    const task = await createRes.json();
    const taskId = task.task_id;

    // 2. Request a consequential action requiring approval (EXTERNAL_WRITE)
    const actionRes = await request.post(`http://127.0.0.1:8000/api/tasks/${taskId}/actions`, {
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'iol_demo_operator_key'
      },
      data: {
        action_type: 'browser.submit_form',
        effect: 'EXTERNAL_WRITE',
        target_url: 'https://example.gov/apply',
        parameters: { applicant_id: 'APP-99812', expedite: true },
        explanation: 'Submitting external registration form to government portal'
      }
    });
    expect(actionRes.status()).toBe(200);
    const actionData = await actionRes.json();
    expect(actionData.approval_status).toBe('APPROVAL_REQUIRED');

    // 3. Navigate to task in frontend
    await page.goto(`/?task_id=${taskId}`);
    await expect(page.locator(`text=${taskId}`)).toBeVisible({ timeout: 15000 });

    // 4. Verify Action Approval Panel appears
    const approvalPanel = page.locator('[data-testid="action-approval-panel"]');
    await expect(approvalPanel).toBeVisible({ timeout: 10000 });

    // Verify consequence tier badge
    await expect(page.locator('[data-testid="action-effect-badge"]')).toContainText('EXTERNAL WRITE');

    // 5. Click Approve
    const approveBtn = page.locator('[data-testid="approve-action-btn"]');
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // Verify approved feedback
    await expect(page.locator('[data-testid="action-decision-status"]')).toContainText('Action approved', { timeout: 10000 });

    // Take screenshot of approved action state
    await page.screenshot({ path: '../docs/screenshots/v08_action_approval_verified.png', fullPage: true });

    // Verify task resumes to COMPLETED
    await expect(page.locator('text=COMPLETED').first()).toBeVisible({ timeout: 15000 });
  });

});
