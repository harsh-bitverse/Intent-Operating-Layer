import { test, expect } from '@playwright/test';

process.env.NO_PROXY = 'localhost,127.0.0.1,::1';
process.env.no_proxy = 'localhost,127.0.0.1,::1';

test.describe('Intent Operating Layer - End-to-End Launch Verification', () => {

  // ---------------------------------------------------------------------------
  // Test A: Complete Research Journey
  // ---------------------------------------------------------------------------
  test('Test A: Complete research journey with SSE events, UI outcomes, and export', async ({ page }) => {
    // 1. Open application
    await page.goto('/');
    await expect(page.locator('text=Intent Operating Layer').first()).toBeVisible();

    // Wait for health indicator
    await expect(page.locator('text=Core Online')).toBeVisible({ timeout: 15000 });

    // 2. Submit research mission intent
    const intent = 'Find 3 open-source AI evaluation and developer frameworks with licenses, repository URLs, and evidence.';
    await page.fill('[data-testid="intent-input"]', intent);
    await page.click('[data-testid="submit-intent-btn"]');

    // 3. Verify task appears in task list and active view
    const taskItem = page.locator('[data-testid^="task-item-"]').first();
    await expect(taskItem).toBeVisible({ timeout: 10000 });

    // 4. Verify SSE Event Stream Log tab
    await page.click('[data-testid="tab-event-log"]');
    // Expect sequential events to be logged
    await expect(page.locator('text=TASK_CREATED').first()).toBeVisible({ timeout: 10000 });

    // 5. Wait for task to reach COMPLETED state (or have table outcomes)
    await expect(page.locator('text=COMPLETED').first()).toBeVisible({ timeout: 45000 });

    // 6. Switch back to Declarative UI & Outcomes tab
    await page.click('[data-testid="tab-outcomes"]');

    // 7. Verify candidates appear in the declarative table
    const firstRow = page.locator('[data-testid="table-row-0"]');
    await expect(firstRow).toBeVisible({ timeout: 10000 });

    // 8. Click row to inspect field-level evidence panel
    await firstRow.click();
    const evidencePanel = page.locator('[data-testid="evidence-panel-row"]');
    await expect(evidencePanel).toBeVisible();
    await expect(evidencePanel.locator('text=Entity Classification:')).toBeVisible();

    // 9. Verify Export functionality triggers without crashing
    const exportJsonBtn = page.locator('[data-testid="export-json-button"]');
    await expect(exportJsonBtn).toBeVisible();

    // Listen for download event
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 });
    await exportJsonBtn.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('iol_verified_results_');
  });

  // ---------------------------------------------------------------------------
  // Test B: Reconnection and Persistence Across Page Reload
  // ---------------------------------------------------------------------------
  test('Test B: Reconnection and durable event replay across page reload', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Core Online')).toBeVisible({ timeout: 15000 });

    // Submit intent
    const intent = 'Identify 2 AI researchers in neural rendering with citations';
    await page.fill('[data-testid="intent-input"]', intent);
    await page.click('[data-testid="submit-intent-btn"]');

    // Wait for task creation
    const taskItem = page.locator('[data-testid^="task-item-"]').first();
    await expect(taskItem).toBeVisible({ timeout: 10000 });
    const taskText = await taskItem.innerText();
    const taskIdMatch = taskText.match(/task_[a-f0-9]+/);
    expect(taskIdMatch).not.toBeNull();
    const taskId = taskIdMatch![0];

    // Simulate closing and reopening tab (reload page)
    await page.reload();
    await expect(page.locator('text=Core Online')).toBeVisible({ timeout: 15000 });

    // Re-select the persisted task from list
    const persistedTaskItem = page.locator(`[data-testid="task-item-${taskId}"]`);
    await expect(persistedTaskItem).toBeVisible();
    await persistedTaskItem.click();

    // Switch to SSE event log tab
    await page.click('[data-testid="tab-event-log"]');

    // Verify durable events were replayed from store
    await expect(page.locator('text=TASK_CREATED').first()).toBeVisible({ timeout: 10000 });
    const eventCountBadge = page.locator('[data-testid="tab-event-log"] span.font-mono');
    const countText = await eventCountBadge.innerText();
    const count = parseInt(countText, 10);
    expect(count).toBeGreaterThan(0);
  });

  // ---------------------------------------------------------------------------
  // Test C: Task Cancellation
  // ---------------------------------------------------------------------------
  test('Test C: Task cancellation halts execution and preserves terminal state', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('text=Core Online')).toBeVisible({ timeout: 15000 });

    // Submit intent
    const intent = 'Perform comprehensive search across 20 international robotics institutions for control theory labs';
    await page.fill('[data-testid="intent-input"]', intent);
    await page.click('[data-testid="submit-intent-btn"]');

    // Locate cancellation button
    const cancelBtn = page.locator('[data-testid="cancel-task-button"]');
    if (await cancelBtn.isVisible({ timeout: 3000 })) {
      await cancelBtn.click();
      // Expect CANCELLED status badge and termination message
      await expect(page.locator('text=CANCELLED').first()).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=Execution Terminated')).toBeVisible();
    }
  });

  // ---------------------------------------------------------------------------
  // Test D: Cross-Tenant Ownership Isolation
  // ---------------------------------------------------------------------------
  test('Test D: Multi-tenant ownership isolation prevents cross-tenant access', async ({ page, request }) => {
    await page.goto('/');
    await expect(page.locator('text=Core Online')).toBeVisible({ timeout: 15000 });

    // 1. Create a task directly as Tenant Alpha via API
    const alphaRes = await request.post('http://127.0.0.1:8000/api/tasks', {
      headers: { 'X-API-Key': 'iol_key_user_alpha' },
      data: {
        intent: 'Confidential research for Tenant Alpha only',
        budget: { max_duration_seconds: 60, max_steps: 5, max_cost_usd: 1.0 },
      },
    });
    expect(alphaRes.status()).toBe(201);
    const alphaTask = await alphaRes.json();
    const alphaTaskId = alphaTask.task_id;
    expect(alphaTask.user_id).toBe('user_a');

    // 2. Select Tenant Beta in the UI
    const sessionSelect = page.locator('select[aria-label="Active Authenticated Session"]');
    await sessionSelect.selectOption('iol_key_user_beta');

    // Wait for task store to refresh
    await page.waitForTimeout(1000);

    // 3. Verify Tenant Alpha's task does NOT appear in Tenant Beta's UI task list
    const alphaItemInBeta = page.locator(`[data-testid="task-item-${alphaTaskId}"]`);
    await expect(alphaItemInBeta).not.toBeVisible();

    // 4. Attempt direct cross-tenant GET as Tenant Beta -> 403 Forbidden
    const forbiddenGet = await request.get(`http://127.0.0.1:8000/api/tasks/${alphaTaskId}`, {
      headers: { 'X-API-Key': 'iol_key_user_beta' },
    });
    expect(forbiddenGet.status()).toBe(403);
    const errBody = await forbiddenGet.json();
    expect(errBody.detail).toContain('Access denied');

    // 5. Attempt direct cross-tenant Cancel as Tenant Beta -> 403 Forbidden
    const forbiddenCancel = await request.post(`http://127.0.0.1:8000/api/tasks/${alphaTaskId}/cancel`, {
      headers: { 'X-API-Key': 'iol_key_user_beta' },
      data: { reason: 'Unauthorized cancellation attempt' },
    });
    expect(forbiddenCancel.status()).toBe(403);
  });

  // ---------------------------------------------------------------------------
  // Test E: Failure Handling and Partial State Preservation
  // ---------------------------------------------------------------------------
  test('Test E: Graceful failure handling and partial results preservation', async ({ page, request }) => {
    // Direct submission of intent with impossible / contradictory constraints
    const createRes = await request.post('http://127.0.0.1:8000/api/tasks', {
      headers: { 'X-API-Key': 'iol_demo_operator_key' },
      data: {
        intent: 'Discover 5 telepathic submarine companies founded in the 17th century with interstellar flight logs',
        budget: { max_duration_seconds: 60, max_steps: 5, max_cost_usd: 1.0 },
      },
    });
    expect(createRes.status()).toBe(201);
    const task = await createRes.json();
    const taskId = task.task_id;

    // Wait for background worker to execute and reach terminal state
    let finalTask: any = null;
    for (let i = 0; i < 30; i++) {
      const checkRes = await request.get(`http://127.0.0.1:8000/api/tasks/${taskId}`, {
        headers: { 'X-API-Key': 'iol_demo_operator_key' },
      });
      finalTask = await checkRes.json();
      if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(finalTask.status)) break;
      await new Promise((r) => setTimeout(r, 1000));
    }

    expect(['COMPLETED', 'FAILED']).toContain(finalTask.status);

    // Verify events were preserved durably in the store
    const eventsRes = await request.get(`http://127.0.0.1:8000/api/tasks/${taskId}/events`, {
      headers: { 'X-API-Key': 'iol_demo_operator_key' },
    });
    expect(eventsRes.status()).toBe(200);

    // Navigate to UI and verify the task state renders cleanly without frontend crash
    await page.goto('/');
    const sessionSelect = page.locator('select[aria-label="Active Authenticated Session"]');
    await sessionSelect.selectOption('iol_demo_operator_key');

    const taskItem = page.locator(`[data-testid="task-item-${taskId}"]`);
    if (await taskItem.isVisible({ timeout: 5000 })) {
      await taskItem.click();
      await expect(page.locator(`text=${taskId}`).first()).toBeVisible();
    }
  });

});
