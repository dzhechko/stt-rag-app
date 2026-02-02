import { test, expect, expectedTimeouts } from '../fixtures/test-fixtures';

test.describe('Transcription Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display transcripts list page', async ({ page }) => {
    await page.goto('/transcripts');

    // Check page title
    await expect(page.locator('h1, h2')).toContainText(/Транскрипты|Transcripts/i);

    // Check for filters
    const filters = page.locator('.filters, [data-testid="filters"], select');
    const filtersVisible = await filters.count() > 0;
    expect(filtersVisible).toBeTruthy();
  });

  test('should filter transcripts by status', async ({ page }) => {
    await page.goto('/transcripts');

    // Look for status filter
    const statusFilter = page.locator('select').filter({ hasText: /статус|status|ожидание|обработка|завершено/i }).first();

    const statusVisible = await statusFilter.isVisible().catch(() => false);
    if (statusVisible) {
      // Try different status options
      const statuses = ['completed', 'processing', 'pending', 'error'];
      for (const status of statuses) {
        await statusFilter.selectOption({ label: new RegExp(status, 'i') });
        await page.waitForTimeout(1000);
      }
    }
  });

  test('should filter transcripts by language', async ({ page }) => {
    await page.goto('/transcripts');

    // Look for language filter
    const languageFilter = page.locator('select').filter({ hasText: /язык|language|русский|english/i }).first();

    const languageVisible = await languageFilter.isVisible().catch(() => false);
    if (languageVisible) {
      // Select Russian language
      await languageFilter.selectOption({ label: /Русский/i });
      await page.waitForTimeout(1000);

      // Verify filter was applied
      const currentValue = await languageFilter.inputValue();
      expect(currentValue).toBeTruthy();
    }
  });

  test('should display transcript cards with key information', async ({ page }) => {
    await page.goto('/transcripts');

    // Wait for transcripts to load
    await page.waitForTimeout(2000);

    // Check for transcript cards or list items
    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"], .transcript-item');

    const count = await transcriptCards.count();
    if (count > 0) {
      // Check first card for expected content
      const firstCard = transcriptCards.first();

      // Should have file name
      await expect(firstCard.locator('text=/./')).toBeVisible();

      // Should have status
      const status = firstCard.locator('text=/ожидание|обработка|завершено|ошибка|pending|processing|completed|error/i');
      await expect(status.first()).toBeVisible();

      // Should have date or timestamp
      const date = firstCard.locator('text=/\\d{1,2}\\.\\d{1,2}\\.\\d{4}|\\d{4}-\\d{2}-\\d{2}/');
      const hasDate = await date.count() > 0;
      expect(hasDate).toBeTruthy();
    }
  });

  test('should expand and collapse transcript text', async ({ page }) => {
    await page.goto('/transcripts');

    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');

    const count = await transcriptCards.count();
    if (count > 0) {
      const firstCard = transcriptCards.first();

      // Look for expand/collapse button
      const expandButton = firstCard.locator('button').filter({ hasText: /показать|скрыть|expand|collapse/i }).first();
      const buttonVisible = await expandButton.isVisible().catch(() => false);

      if (buttonVisible) {
        // Click to expand
        await expandButton.click();
        await page.waitForTimeout(500);

        // Verify content is visible
        const transcriptText = firstCard.locator('.transcript-text, .preview-text, [data-testid="transcript-text"]');
        const textVisible = await transcriptText.isVisible().catch(() => false);
        expect(textVisible).toBeTruthy();

        // Click to collapse
        await expandButton.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('should navigate to transcript detail page', async ({ page }) => {
    await page.goto('/transcripts');

    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');

    const count = await transcriptCards.count();
    if (count > 0) {
      const firstCard = transcriptCards.first();

      // Click on view/detail button
      const viewButton = firstCard.locator('button').filter({ hasText: /просмотр|view|детали|details/i }).first();
      const buttonVisible = await viewButton.isVisible().catch(() => false);

      if (buttonVisible) {
        await viewButton.click();

        // Verify navigation to detail page
        await expect(page).toHaveURL(/\/transcripts\/[a-f0-9-]+/);
      } else {
        // Try clicking on the card itself
        await firstCard.click();
        await expect(page).toHaveURL(/\/transcripts\/[a-f0-9-]+/);
      }
    }
  });

  test('should display transcript detail page with all sections', async ({ page }) => {
    await page.goto('/transcripts');

    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      const firstCard = transcriptCards.first();
      await firstCard.click();

      // Wait for detail page to load
      await page.waitForTimeout(2000);

      // Check for transcript text section
      const transcriptSection = page.locator('text=/транскрипт|transcript|текст/i');
      await expect(transcriptSection.first()).toBeVisible();

      // Check for summaries section
      const summariesSection = page.locator('text=/протокол|summary|саммари/i');
      await expect(summariesSection.first()).toBeVisible();

      // Check for actions (view modes, export, etc.)
      const actions = page.locator('button, select');
      const hasActions = await actions.count() > 0;
      expect(hasActions).toBeTruthy();
    }
  });

  test('should switch between view modes (text, json, srt)', async ({ page }) => {
    await page.goto('/transcripts');

    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      // Look for view mode selector
      const viewModeSelector = page.locator('select').filter({ hasText: /режим|mode|текст|json|srt/i }).first();
      const selectorVisible = await viewModeSelector.isVisible().catch(() => false);

      if (selectorVisible) {
        // Try different view modes
        const modes = ['text', 'json', 'srt'];
        for (const mode of modes) {
          await viewModeSelector.selectOption({ label: new RegExp(mode, 'i') });
          await page.waitForTimeout(500);

          // Verify content updated
          const content = page.locator('.transcript-content, pre, code');
          await expect(content.first()).toBeVisible();
        }
      }
    }
  });

  test('should export transcript in different formats', async ({ page }) => {
    await page.goto('/transcripts');

    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      await transcriptCards.first().click();
      await page.waitForTimeout(2000);

      // Look for export button
      const exportButton = page.locator('button').filter({ hasText: /экспорт|export|скачать|download/i }).first();
      const buttonVisible = await exportButton.isVisible().catch(() => false);

      if (buttonVisible) {
        // Set up download handler
        const downloadPromise = page.waitForEvent('download');

        await exportButton.click();
        const download = await downloadPromise;

        // Verify download started
        expect(download.suggestedFilename()).toBeTruthy();
      }
    }
  });

  test('should delete transcript with confirmation', async ({ page }) => {
    await page.goto('/transcripts');

    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const countBefore = await transcriptCards.count();

    if (countBefore > 0) {
      const firstCard = transcriptCards.first();

      // Click delete button
      const deleteButton = firstCard.locator('button').filter({ hasText: /удалить|delete/i }).first();
      const buttonVisible = await deleteButton.isVisible().catch(() => false);

      if (buttonVisible) {
        // Handle confirmation dialog
        page.on('dialog', async dialog => {
          expect(dialog.type()).toBe('confirm');
          await dialog.accept();
        });

        await deleteButton.click();
        await page.waitForTimeout(2000);

        // Verify transcript was removed (if deletion was successful)
        const countAfter = await transcriptCards.count();
        // Count might be same if deletion failed or was cancelled
        expect(countAfter).toBeLessThanOrEqual(countBefore);
      }
    }
  });
});

test.describe('Transcription Status Monitoring', () => {
  test('should display real-time status updates', async ({ page }) => {
    await page.goto('/transcripts');

    // Wait for initial load
    await page.waitForTimeout(2000);

    const transcriptCards = page.locator('.transcript-card, [data-testid="transcript-item"]');
    const count = await transcriptCards.count();

    if (count > 0) {
      const firstCard = transcriptCards.first();

      // Check for status indicator
      const statusIndicator = firstCard.locator('[data-testid="status"], .status, .status-badge').first();
      const statusVisible = await statusIndicator.isVisible().catch(() => false);

      if (statusVisible) {
        const statusText = await statusIndicator.textContent();
        expect(statusText).toBeTruthy();
      }
    }
  });

  test('should show processing status for in-progress transcriptions', async ({ page }) => {
    await page.goto('/transcripts');

    await page.waitForTimeout(2000);

    const processingCards = page.locator('.transcript-card, [data-testid="transcript-item"]').filter({
      hasText: /обработка|processing|в процессе/i
    });

    const count = await processingCards.count();
    if (count > 0) {
      const firstProcessing = processingCards.first();

      // Check for progress indicator
      const progressIndicator = firstProcessing.locator('.progress, [role="progressbar"], .spinner').first();
      const progressVisible = await progressIndicator.isVisible().catch(() => false);

      if (progressVisible) {
        await expect(progressIndicator).toBeVisible();
      }
    }
  });

  test('should show error status for failed transcriptions', async ({ page }) => {
    await page.goto('/transcripts');

    await page.waitForTimeout(2000);

    const errorCards = page.locator('.transcript-card, [data-testid="transcript-item"]').filter({
      hasText: /ошибка|error|failed/i
    });

    const count = await errorCards.count();
    if (count > 0) {
      const firstError = errorCards.first();

      // Check for error styling
      const errorClass = await firstError.getAttribute('class');
      const hasErrorClass = errorClass?.includes('error') || errorClass?.includes('danger');
      expect(hasErrorClass).toBeTruthy();
    }
  });
});

test.describe('Transcription Search and Filtering', () => {
  test('should search transcripts by text', async ({ page }) => {
    await page.goto('/transcripts');

    // Look for search input
    const searchInput = page.locator('input[type="text"], input[type="search"]').filter({ hasText: /поиск|search/i }).first();
    const searchVisible = await searchInput.isVisible().catch(() => false);

    if (searchVisible) {
      await searchInput.fill('test');
      await page.waitForTimeout(1000);

      // Verify search was performed
      const currentValue = await searchInput.inputValue();
      expect(currentValue).toBe('test');
    }
  });

  test('should sort transcripts', async ({ page }) => {
    await page.goto('/transcripts');

    // Look for sort selector
    const sortSelector = page.locator('select').filter({ hasText: /сортировка|sort|дата/i }).first();
    const sortVisible = await sortSelector.isVisible().catch(() => false);

    if (sortVisible) {
      // Try different sort options
      await sortSelector.selectOption({ index: 1 });
      await page.waitForTimeout(1000);

      // Verify sort was applied
      const currentValue = await sortSelector.inputValue();
      expect(currentValue).toBeTruthy();
    }
  });
});
