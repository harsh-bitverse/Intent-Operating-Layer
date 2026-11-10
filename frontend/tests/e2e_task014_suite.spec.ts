import { test, expect } from '@playwright/test';

process.env.NO_PROXY = 'localhost,127.0.0.1,::1';
process.env.no_proxy = 'localhost,127.0.0.1,::1';

/**
 * Playwright End-to-End Verification Suite for IOL Task 014:
 * - Model Providers & Routing UI inspection and modal navigation
 * - SSRF Protection Enforcement: UI blocks attempts to register internal system ports
 * - Local Weights Discovery: Inspection of pre-installed ~/.ollama models
 * - Functional Role Routing: Inspection and policy update verification
 * - Secret Isolation: Verification that API keys are strictly masked in client presentation
 */

test.describe('IOL Task 014 - Universal Model Provider Layer & Routing Architecture', () => {

  test('Probe 1: Open Model Runtimes modal and verify security safeguards & masked keys', async ({ page }) => {
    await page.goto('/');

    // Locate and click the Model Runtimes button in the header
    const modelBtn = page.locator('button:has-text("Model Runtimes")');
    await expect(modelBtn).toBeVisible({ timeout: 15000 });
    await modelBtn.click();

    // Verify modal title and SSRF security banner
    await expect(page.locator('h2:has-text("Universal Model Provider & Routing Architecture")')).toBeVisible();
    await expect(page.locator('text=SSRF Boundary Active')).toBeVisible();
    await expect(page.locator('text=Key Masking Enforced')).toBeVisible();

    // Verify registered providers are listed
    await expect(page.locator('h3:has-text("Google Gemini API")')).toBeVisible();
    await expect(page.locator('h3:has-text("Ollama Local Daemon")')).toBeVisible();
    await expect(page.locator('h3:has-text("Deterministic Test Synthesizer")')).toBeVisible();

    // Verify raw keys are NEVER present in DOM
    const htmlContent = await page.content();
    expect(htmlContent).not.toContain('AIzaSy');
  });

  test('Probe 2: Test connection diagnostics on Mock provider returns HEALTHY status', async ({ page }) => {
    await page.goto('/');
    await page.locator('button:has-text("Model Runtimes")').click();

    // Find the Mock provider card and click its Test Connection button
    const mockCard = page.locator('[data-testid="provider-card-mock"]');
    await expect(mockCard).toBeVisible();

    const testBtn = mockCard.locator('[data-testid="test-btn-mock"]');
    await expect(testBtn).toBeVisible();
    await testBtn.click();

    // Diagnostic result banner should appear with HEALTHY status
    await expect(mockCard.locator('text=[HEALTHY]')).toBeVisible({ timeout: 10000 });
    await expect(mockCard.locator('text=Deterministic mock provider ready')).toBeVisible();
  });

  test('Probe 3: Local weights on disk tab displays pre-installed ~/.ollama GGUF assets', async ({ page }) => {
    await page.goto('/');
    await page.locator('button:has-text("Model Runtimes")').click();

    // Switch to Local Weights On Disk tab
    const localTab = page.locator('button:has-text("Local Weights On Disk")');
    await expect(localTab).toBeVisible();
    await localTab.click();

    // Verify pre-installed models appear
    await expect(page.locator('text=Pre-downloaded GGUF Model Assets')).toBeVisible();
    // Check for presence of llama3.2:1b or qwen2.5 models discovered from disk
    const modelTag = page.locator('span:has-text("llama3.2:1b")');
    await expect(modelTag).toBeVisible({ timeout: 5000 });
  });

  test('Probe 4: Functional role routing tab displays all 6 subsystem roles', async ({ page }) => {
    await page.goto('/');
    await page.locator('button:has-text("Model Runtimes")').click();

    // Switch to Functional Role Routing tab
    const routingTab = page.locator('button:has-text("Functional Role Routing")');
    await expect(routingTab).toBeVisible();
    await routingTab.click();

    // Verify all 6 functional roles are listed via testids
    await expect(page.locator('[data-testid="routing-role-experience_synthesis"]')).toBeVisible();
    await expect(page.locator('[data-testid="routing-role-planning"]')).toBeVisible();
    await expect(page.locator('[data-testid="routing-role-browser_reasoning"]')).toBeVisible();
    await expect(page.locator('[data-testid="routing-role-intent_understanding"]')).toBeVisible();
    await expect(page.locator('[data-testid="routing-role-verification"]')).toBeVisible();
    await expect(page.locator('[data-testid="routing-role-knowledge_extraction"]')).toBeVisible();
  });

  test('Probe 5: SSRF security boundary rejects attempts to configure forbidden system ports', async ({ page }) => {
    await page.goto('/');
    await page.locator('button:has-text("Model Runtimes")').click();

    // Open configuration modal for Gemini provider
    const geminiCard = page.locator('[data-testid="provider-card-gemini"]');
    await geminiCard.locator('[data-testid="config-btn-gemini"]').click();

    // Attempt to point base URL to internal port 8000
    const urlInput = page.locator('[data-testid="edit-base-url-input"]');
    await urlInput.fill('http://127.0.0.1:8000/internal-api');

    // Click Save Configuration
    await page.locator('[data-testid="save-provider-btn"]').click();

    // Expect SSRF error message to be displayed and block configuration
    await expect(page.locator('text=Security SSRF Violation')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=system port 8000')).toBeVisible();
  });
});
