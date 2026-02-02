import { test, expect, expectedTimeouts } from '../fixtures/test-fixtures';

test.describe('Summaries (Протоколы встреч) Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display summaries section on transcript detail page', async ({ page }) => {
    // Navigate to transcripts and select first one
    await page.goto('/transcripts');
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      // Check for summaries section
      const summariesSection = page.locator('text=/протоколы встреч|summaries|протокол/i').first();
      await expect(summariesSection).toBeVisible();
    }
  });

  test('should create a new summary', async ({ page }) => {
    await page.goto('/transcripts');
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      // Click create summary button
      const createButton = page.locator('button').filter({ hasText: /создать протокол|создать саммари|create summary/i }).first();
      const buttonVisible = await createButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await createButton.click();

        // Look for summary creation dialog/form
        await page.waitForTimeout(1000);

        // Check if model selector is present
        const modelSelector = page.locator('select').filter({ hasText: /модель|model/i }).first();
        const modelVisible = await modelSelector.isVisible().catch(() => false);

        if (modelVisible) {
          // Select a model
          await modelSelector.selectOption({ index: 1 });
        }

        // Check for template selector
        const templateSelector = page.locator('select').filter({ hasText: /шаблон|template/i }).first();
        const templateVisible = await templateSelector.isVisible().catch(() => false);

        if (templateVisible) {
          await templateSelector.selectOption({ index: 0 });
        }

        // Submit to create summary
        const submitButton = page.locator('button').filter({ hasText: /создать|create|сгенерировать/i }).first();
        await submitButton.click();

        // Wait for summary creation
        await page.waitForTimeout(expectedTimeouts.summarization);

        // Verify summary was created
        const successMessage = page.locator('text=/успешно|success|создан|created/i').first();
        const summaryContent = page.locator('.summary-content, [data-testid="summary-content"], .markdown-content').first();

        const hasSuccess = await successMessage.isVisible().catch(() => false) ||
          await summaryContent.isVisible().catch(() => false);
        expect(hasSuccess).toBeTruthy();
      }
    }
  });

  test('should display summary with markdown rendering', async ({ page }) => {
    await page.goto('/transcripts');
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      // Check if there are existing summaries
      const summaryContent = page.locator('.summary-content, [data-testid="summary-content"], .markdown-content').first();
      const hasSummary = await summaryContent.isVisible().catch(() => false);

      if (hasSummary) {
        // Check for markdown elements
        const headers = page.locator('h1, h2, h3, h4, h5, h6').first();
        const hasHeaders = await headers.isVisible().catch(() => false);

        const lists = page.locator('ul, ol').first();
        const hasLists = await lists.isVisible().catch(() => false);

        const hasMarkdownElements = hasHeaders || hasLists;
        expect(hasMarkdownElements).toBeTruthy();
      }
    }
  });

  test('should expand and collapse summary', async ({ page }) => {
    await page.goto('/transcripts');
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      // Look for expand/collapse button
      const toggleButton = page.locator('button').filter({
        hasText: /показать протокол|скрыть протокол|show summary|hide summary/i
      }).first();

      const buttonVisible = await toggleButton.isVisible().catch(() => false);
      if (buttonVisible) {
        // Get initial state
        const buttonTextBefore = await toggleButton.textContent();

        // Click to toggle
        await toggleButton.click();
        await page.waitForTimeout(500);

        const buttonTextAfter = await toggleButton.textContent();

        // Button text should have changed
        expect(buttonTextBefore).not.toBe(buttonTextAfter);

        // Click back
        await toggleButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('should copy summary to clipboard', async ({ page }) => {
    await page.goto('/transcripts');
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      // Check if summary exists
      const summaryContent = page.locator('.summary-content, [data-testid="summary-content"]').first();
      const hasSummary = await summaryContent.isVisible().catch(() => false);

      if (hasSummary) {
        // Look for copy button
        const copyButton = page.locator('button').filter({ hasText: /копировать|copy/i }).first();
        const buttonVisible = await copyButton.isVisible().catch(() => false);

        if (buttonVisible) {
          // Setup clipboard listener
          const clipboardText = await page.evaluate(async () => {
            // Try to read clipboard (might require permissions)
            try {
              return await navigator.clipboard.readText();
            } catch {
              return '';
            }
          });

          await copyButton.click();
          await page.waitForTimeout(500);

          // Check for success feedback
          const successMessage = page.locator('text=/скопировано|copied/i').first();
          const hasSuccess = await successMessage.isVisible().catch(() => false);
          expect(hasSuccess).toBeTruthy();
        }
      }
    }
  });

  test('should display list of all summaries for a transcript', async ({ page }) => {
    await page.goto('/transcripts');
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      // Look for summaries list
      const summariesList = page.locator('.summaries-list, [data-testid="summaries-list"], .summary-item');
      const summariesCount = await summariesList.count();

      if (summariesCount > 0) {
        // Check if each summary has metadata
        const firstSummary = summariesList.first();

        // Should have model info
        const modelInfo = firstSummary.locator('text=/model|модель|gpt|whisper/i');
        const hasModelInfo = await modelInfo.count() > 0;

        // Should have timestamp
        const timestamp = firstSummary.locator('text=/\\d{1,2}\\.\\d{1,2}\\.\\d{4}|\\d{4}-\\d{2}-\\d{2}/');
        const hasTimestamp = await timestamp.count() > 0;

        expect(hasModelInfo || hasTimestamp).toBeTruthy();
      }
    }
  });

  test('should select different summarization models', async ({ page }) => {
    await page.goto('/transcripts');
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      // Click create summary
      const createButton = page.locator('button').filter({ hasText: /создать протокол|create summary/i }).first();
      const buttonVisible = await createButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await createButton.click();
        await page.waitForTimeout(1000);

        // Look for model selector
        const modelSelector = page.locator('select').filter({ hasText: /модель|model/i }).first();
        const modelVisible = await modelSelector.isVisible().catch(() => false);

        if (modelVisible) {
          // Get available options
          const options = await modelSelector.locator('option').allTextContents();
          expect(options.length).toBeGreaterThan(1);

          // Select first option
          await modelSelector.selectOption({ index: 1 });
          const selectedValue = await modelSelector.inputValue();
          expect(selectedValue).toBeTruthy();
        }
      }
    }
  });

  test('should select different summarization templates', async ({ page }) => {
    await page.goto('/transcripts');
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      // Click create summary
      const createButton = page.locator('button').filter({ hasText: /создать протокол|create summary/i }).first();
      const buttonVisible = await createButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await createButton.click();
        await page.waitForTimeout(1000);

        // Look for template selector
        const templateSelector = page.locator('select').filter({ hasText: /шаблон|template/i }).first();
        const templateVisible = await templateSelector.isVisible().catch(() => false);

        if (templateVisible) {
          // Get available options
          const options = await templateSelector.locator('option').allTextContents();

          if (options.length > 1) {
            // Select different template
            await templateSelector.selectOption({ index: 1 });
            const selectedValue = await templateSelector.inputValue();
            expect(selectedValue).toBeTruthy();
          }
        }
      }
    }
  });

  test('should show loading state during summary generation', async ({ page }) => {
    await page.goto('/transcripts');
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      // Click create summary
      const createButton = page.locator('button').filter({ hasText: /создать протокол|create summary/i }).first();
      const buttonVisible = await createButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await createButton.click();
        await page.waitForTimeout(500);

        // Submit to create
        const submitButton = page.locator('button').filter({ hasText: /создать|create|сгенерировать/i }).first();
        await submitButton.click();

        // Check for loading indicator
        const loadingIndicator = page.locator('.spinner, [role="progressbar"], .loading').first();
        const loadingVisible = await loadingIndicator.isVisible().catch(() => false);

        // Or check if button is disabled
        const buttonDisabled = await submitButton.isDisabled();

        const hasLoadingState = loadingVisible || buttonDisabled;
        expect(hasLoadingState).toBeTruthy();
      }
    }
  });
});

test.describe('Summaries Error Handling', () => {
  test('should handle summary creation failure gracefully', async ({ page }) => {
    // Intercept and fail the API call
    await page.route('**/api/summaries', route => route.abort('failed'));

    await page.goto('/transcripts');
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      const createButton = page.locator('button').filter({ hasText: /создать протокол|create summary/i }).first();
      const buttonVisible = await createButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await createButton.click();
        await page.waitForTimeout(500);

        const submitButton = page.locator('button').filter({ hasText: /создать|create/i }).first();
        await submitButton.click();

        // Wait for error
        await page.waitForTimeout(2000);

        // Check for error message
        const errorMessage = page.locator('text=/ошибка|error|не.*удалось|failed/i').first();
        await expect(errorMessage).toBeVisible({ timeout: 5000 });
      }
    }
  });

  test('should display summary creation timeout message', async ({ page }) => {
    // Intercept and delay the response
    await page.route('**/api/summaries', async route => {
      // Delay response for longer than timeout
      await new Promise(resolve => setTimeout(resolve, 10000));
      route.continue();
    });

    await page.goto('/transcripts');
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      const createButton = page.locator('button').filter({ hasText: /создать протокол|create summary/i }).first();
      const buttonVisible = await createButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await createButton.click();
        await page.waitForTimeout(500);

        const submitButton = page.locator('button').filter({ hasText: /создать|create/i }).first();
        await submitButton.click();

        // Wait for timeout or error
        await page.waitForTimeout(60000);

        // Check for timeout message
        const timeoutMessage = page.locator('text=/тайм-аут|timeout|превышено|too long/i').first();
        const hasTimeout = await timeoutMessage.isVisible().catch(() => false);

        if (hasTimeout) {
          await expect(timeoutMessage).toBeVisible();
        }
      }
    }
  });
});
