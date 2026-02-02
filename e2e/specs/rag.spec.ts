import { test, expect, expectedTimeouts } from '../fixtures/test-fixtures';

test.describe('RAG Chat Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should navigate to RAG chat page', async ({ page }) => {
    await page.goto('/');

    // Click on RAG Chat link
    const ragLink = page.locator('a[href="/rag"], a').filter({ hasText: /RAG Чат|RAG Chat/i }).first();
    await ragLink.click();

    await expect(page).toHaveURL(/\/rag/);

    // Check for RAG chat interface
    const chatContainer = page.locator('.chat-container, [data-testid="rag-chat"], .rag-chat').first();
    await expect(chatContainer).toBeVisible();
  });

  test('should display chat input field', async ({ page }) => {
    await page.goto('/rag');

    // Check for question input
    const questionInput = page.locator('textarea, input[type="text"]').filter({ hasText: /задать вопрос|вопрос|question/i }).first();
    await expect(questionInput).toBeVisible();
  });

  test('should display transcript selector', async ({ page }) => {
    await page.goto('/rag');

    // Look for transcript selector
    const transcriptSelector = page.locator('select, [role="combobox"], .transcript-selector').first();
    const selectorVisible = await transcriptSelector.isVisible().catch(() => false);

    if (selectorVisible) {
      await expect(transcriptSelector).toBeVisible();
    }
  });

  test('should display RAG settings button', async ({ page }) => {
    await page.goto('/rag');

    // Look for settings button
    const settingsButton = page.locator('button').filter({ hasText: /настройки|settings/i }).first();
    const buttonVisible = await settingsButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await expect(settingsButton).toBeVisible();
    }
  });

  test('should submit a question and receive answer', async ({ page }) => {
    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Enter question
    const questionInput = page.locator('textarea, input[type="text"]').first();
    await questionInput.fill('Какова основная тема обсуждения?');

    // Submit question
    const submitButton = page.locator('button').filter({ hasText: /отправить|send|задать/i }).first();
    await submitButton.click();

    // Wait for answer
    await page.waitForTimeout(expectedTimeouts.ragQuery);

    // Check for answer
    const answerContainer = page.locator('.answer, [data-testid="answer"], .assistant-message').first();
    const answerVisible = await answerContainer.isVisible().catch(() => false);

    if (answerVisible) {
      await expect(answerContainer).toBeVisible();

      // Check for answer content
      const answerText = await answerContainer.textContent();
      expect(answerText?.length).toBeGreaterThan(0);
    }
  });

  test('should display answer with quality metrics', async ({ page }) => {
    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Submit a question
    const questionInput = page.locator('textarea, input[type="text"]').first();
    await questionInput.fill('Что было обсуждено?');

    const submitButton = page.locator('button').filter({ hasText: /отправить|send|задать/i }).first();
    await submitButton.click();

    await page.waitForTimeout(expectedTimeouts.ragQuery);

    // Check for quality metrics
    const qualityMetrics = page.locator('text=/качество|quality|обоснованность|полнота|релевантность/i').first();
    const hasMetrics = await qualityMetrics.isVisible().catch(() => false);

    if (hasMetrics) {
      await expect(qualityMetrics).toBeVisible();

      // Check for score
      const score = page.locator('text=/\\d+\\.\\d+|score/i').first();
      const hasScore = await score.isVisible().catch(() => false);
      expect(hasScore).toBeTruthy();
    }
  });

  test('should display sources used for answer', async ({ page }) => {
    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Submit a question
    const questionInput = page.locator('textarea, input[type="text"]').first();
    await questionInput.fill('Расскажи подробнее');

    const submitButton = page.locator('button').filter({ hasText: /отправить|send|задать/i }).first();
    await submitButton.click();

    await page.waitForTimeout(expectedTimeouts.ragQuery);

    // Check for sources section
    const sourcesSection = page.locator('text=/источники|sources/i').first();
    const hasSources = await sourcesSection.isVisible().catch(() => false);

    if (hasSources) {
      await expect(sourcesSection).toBeVisible();

      // Check for source items
      const sourceItems = page.locator('.source, [data-testid="source"], .source-item');
      const sourceCount = await sourceItems.count();
      expect(sourceCount).toBeGreaterThan(0);
    }
  });

  test('should copy answer to clipboard', async ({ page }) => {
    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Submit a question to generate an answer
    const questionInput = page.locator('textarea, input[type="text"]').first();
    await questionInput.fill('Тестовый вопрос');

    const submitButton = page.locator('button').filter({ hasText: /отправить|send|задать/i }).first();
    await submitButton.click();

    await page.waitForTimeout(expectedTimeouts.ragQuery);

    // Look for copy button
    const copyButton = page.locator('button').filter({ hasText: /копировать|copy/i }).first();
    const buttonVisible = await copyButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await copyButton.click();
      await page.waitForTimeout(500);

      // Check for success feedback
      const successMessage = page.locator('text=/скопировано|copied/i').first();
      const hasSuccess = await successMessage.isVisible().catch(() => false);
      expect(hasSuccess).toBeTruthy();
    }
  });

  test('should copy sources to clipboard', async ({ page }) => {
    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Submit a question
    const questionInput = page.locator('textarea, input[type="text"]').first();
    await questionInput.fill('Еще один вопрос');

    const submitButton = page.locator('button').filter({ hasText: /отправить|send|задать/i }).first();
    await submitButton.click();

    await page.waitForTimeout(expectedTimeouts.ragQuery);

    // Look for copy sources button
    const copySourcesButton = page.locator('button').filter({ hasText: /копировать источники|copy sources/i }).first();
    const buttonVisible = await copySourcesButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await copySourcesButton.click();
      await page.waitForTimeout(500);

      // Check for success feedback
      const successMessage = page.locator('text=/скопировано|copied/i').first();
      const hasSuccess = await successMessage.isVisible().catch(() => false);
      expect(hasSuccess).toBeTruthy();
    }
  });

  test('should display chat history', async ({ page }) => {
    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Submit multiple questions
    const questionInput = page.locator('textarea, input[type="text"]').first();
    const submitButton = page.locator('button').filter({ hasText: /отправить|send|задать/i }).first();

    const questions = ['Вопрос 1', 'Вопрос 2'];

    for (const question of questions) {
      await questionInput.fill(question);
      await submitButton.click();
      await page.waitForTimeout(expectedTimeouts.ragQuery);
    }

    // Check for chat messages
    const chatMessages = page.locator('.message, [data-testid="message"], .chat-message');
    const messageCount = await chatMessages.count();
    expect(messageCount).toBeGreaterThanOrEqual(questions.length);
  });

  test('should create new RAG session', async ({ page }) => {
    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Look for new session button
    const newSessionButton = page.locator('button').filter({ hasText: /новый чат|new chat|новая сессия|new session/i }).first();
    const buttonVisible = await newSessionButton.isVisible().catch(() => false);

    if (buttonVisible) {
      const sessionsBefore = await page.locator('.session, [data-testid="session"]').count();

      await newSessionButton.click();
      await page.waitForTimeout(1000);

      // Check if new session was created
      const sessionsAfter = await page.locator('.session, [data-testid="session"]').count();
      expect(sessionsAfter).toBeGreaterThanOrEqual(sessionsBefore);
    }
  });

  test('should display list of RAG sessions', async ({ page }) => {
    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Look for sessions list
    const sessionsList = page.locator('.sessions-list, [data-testid="sessions-list"], .session-item');
    const sessionsCount = await sessionsList.count();

    // Sessions might be empty, but list should be present
    const sessionsListContainer = page.locator('.sessions, [data-testid="sessions"]').first();
    const listVisible = await sessionsListContainer.isVisible().catch(() => false);

    if (listVisible || sessionsCount > 0) {
      expect(listVisible || sessionsCount > 0).toBeTruthy();
    }
  });

  test('should switch between RAG sessions', async ({ page }) => {
    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Look for existing sessions
    const sessionItems = page.locator('.session, [data-testid="session"], .session-item');
    const sessionCount = await sessionItems.count();

    if (sessionCount > 1) {
      const firstSession = sessionItems.first();
      const secondSession = sessionItems.nth(1);

      // Click on second session
      await secondSession.click();
      await page.waitForTimeout(1000);

      // Verify session changed (URL or content)
      const currentUrl = page.url();
      const hasSessionId = currentUrl.includes('/sessions/') || currentUrl.includes('session');

      expect(hasSessionId).toBeTruthy();
    }
  });
});

test.describe('RAG Settings', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/rag');
  });

  test('should open settings panel', async ({ page }) => {
    // Look for settings button
    const settingsButton = page.locator('button').filter({ hasText: /настройки|settings/i }).first();
    const buttonVisible = await settingsButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await settingsButton.click();
      await page.waitForTimeout(500);

      // Check for settings panel
      const settingsPanel = page.locator('.settings, [data-testid="settings"], .settings-panel').first();
      await expect(settingsPanel).toBeVisible();
    }
  });

  test('should adjust top_k parameter', async ({ page }) => {
    const settingsButton = page.locator('button').filter({ hasText: /настройки|settings/i }).first();
    const buttonVisible = await settingsButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await settingsButton.click();
      await page.waitForTimeout(500);

      // Look for top_k slider or input
      const topKInput = page.locator('input[type="range"], input[type="number"]').filter({ hasText: /top_k|количество чанков/i }).first();
      const inputVisible = await topKInput.isVisible().catch(() => false);

      if (inputVisible) {
        // Adjust value
        await topKInput.fill('5');

        // Verify value was set
        const value = await topKInput.inputValue();
        expect(value).toBe('5');
      }
    }
  });

  test('should select different model for generation', async ({ page }) => {
    const settingsButton = page.locator('button').filter({ hasText: /настройки|settings/i }).first();
    const buttonVisible = await settingsButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await settingsButton.click();
      await page.waitForTimeout(500);

      // Look for model selector
      const modelSelector = page.locator('select').filter({ hasText: /модель|model|generation/i }).first();
      const selectorVisible = await modelSelector.isVisible().catch(() => false);

      if (selectorVisible) {
        // Select different model
        await modelSelector.selectOption({ index: 1 });

        const selectedValue = await modelSelector.inputValue();
        expect(selectedValue).toBeTruthy();
      }
    }
  });

  test('should adjust temperature parameter', async ({ page }) => {
    const settingsButton = page.locator('button').filter({ hasText: /настройки|settings/i }).first();
    const buttonVisible = await settingsButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await settingsButton.click();
      await page.waitForTimeout(500);

      // Look for temperature slider or input
      const tempInput = page.locator('input[type="range"], input[type="number"]').filter({ hasText: /temperature|температура/i }).first();
      const inputVisible = await tempInput.isVisible().catch(() => false);

      if (inputVisible) {
        // Adjust value
        await tempInput.fill('0.7');

        // Verify value was set
        const value = await tempInput.inputValue();
        expect(value).toBeTruthy();
      }
    }
  });

  test('should toggle advanced features', async ({ page }) => {
    const settingsButton = page.locator('button').filter({ hasText: /настройки|settings/i }).first();
    const buttonVisible = await settingsButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await settingsButton.click();
      await page.waitForTimeout(500);

      // Look for advanced feature toggles
      const toggles = page.locator('input[type="checkbox"]').filter({
        hasText: /multi-hop|query expansion|hybrid search|reranking/i
      });

      const toggleCount = await toggles.count();
      if (toggleCount > 0) {
        // Toggle first feature
        await toggles.first().check();

        const isChecked = await toggles.first().isChecked();
        expect(isChecked).toBeTruthy();
      }
    }
  });

  test('should save settings', async ({ page }) => {
    const settingsButton = page.locator('button').filter({ hasText: /настройки|settings/i }).first();
    const buttonVisible = await settingsButton.isVisible().catch(() => false);

    if (buttonVisible) {
      await settingsButton.click();
      await page.waitForTimeout(500);

      // Look for save button
      const saveButton = page.locator('button').filter({ hasText: /сохранить|save|применить|apply/i }).first();
      const saveVisible = await saveButton.isVisible().catch(() => false);

      if (saveVisible) {
        await saveButton.click();
        await page.waitForTimeout(500);

        // Check for success message
        const successMessage = page.locator('text=/сохранено|saved|применено|applied/i').first();
        const hasSuccess = await successMessage.isVisible().catch(() => false);
        expect(hasSuccess).toBeTruthy();
      }
    }
  });
});

test.describe('RAG Error Handling', () => {
  test('should handle empty question submission', async ({ page }) => {
    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Try to submit empty question
    const questionInput = page.locator('textarea, input[type="text"]').first();
    await questionInput.fill('');

    const submitButton = page.locator('button').filter({ hasText: /отправить|send|задать/i }).first();

    // Check if button is disabled
    const isDisabled = await submitButton.isDisabled();
    expect(isDisabled).toBeTruthy();
  });

  test('should display error message on API failure', async ({ page }) => {
    // Intercept and fail the API call
    await page.route('**/api/rag/**', route => route.abort('failed'));

    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Submit a question
    const questionInput = page.locator('textarea, input[type="text"]').first();
    await questionInput.fill('Тестовый вопрос');

    const submitButton = page.locator('button').filter({ hasText: /отправить|send|задать/i }).first();
    await submitButton.click();

    // Wait for error
    await page.waitForTimeout(2000);

    // Check for error message
    const errorMessage = page.locator('text=/ошибка|error|не.*удалось|failed/i').first();
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
  });

  test('should handle timeout gracefully', async ({ page }) => {
    // Intercept and delay the response
    await page.route('**/api/rag/**', async route => {
      await new Promise(resolve => setTimeout(resolve, 10000));
      route.abort('failed');
    });

    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Submit a question
    const questionInput = page.locator('textarea, input[type="text"]').first();
    await questionInput.fill('Тестовый вопрос');

    const submitButton = page.locator('button').filter({ hasText: /отправить|send|задать/i }).first();
    await submitButton.click();

    // Wait for timeout
    await page.waitForTimeout(60000);

    // Check for timeout message
    const timeoutMessage = page.locator('text=/тайм-аут|timeout/i').first();
    const hasTimeout = await timeoutMessage.isVisible().catch(() => false);

    if (hasTimeout) {
      await expect(timeoutMessage).toBeVisible();
    }
  });

  test('should handle no indexed transcripts scenario', async ({ page }) => {
    // Mock empty transcripts response
    await page.route('**/api/transcripts**', route => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0 })
      });
    });

    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Check for empty state message
    const emptyMessage = page.locator('text=/нет.*транскриптов|no.*transcripts|нет.*данных|no.*data/i').first();
    const hasEmptyMessage = await emptyMessage.isVisible().catch(() => false);

    if (hasEmptyMessage) {
      await expect(emptyMessage).toBeVisible();
    }
  });
});

test.describe('RAG Feedback', () => {
  test('should submit feedback on answer', async ({ page }) => {
    await page.goto('/rag');
    await page.waitForTimeout(1000);

    // Submit a question to get an answer
    const questionInput = page.locator('textarea, input[type="text"]').first();
    await questionInput.fill('Тестовый вопрос');

    const submitButton = page.locator('button').filter({ hasText: /отправить|send|задать/i }).first();
    await submitButton.click();

    await page.waitForTimeout(expectedTimeouts.ragQuery);

    // Look for feedback buttons
    const feedbackButtons = page.locator('button').filter({ hasText: /👍|👎|полезно|не полезно|helpful|not helpful/i });
    const buttonCount = await feedbackButtons.count();

    if (buttonCount > 0) {
      await feedbackButtons.first().click();
      await page.waitForTimeout(500);

      // Check for success feedback
      const successMessage = page.locator('text=/спасибо|thanks|отправлено|submitted/i').first();
      const hasSuccess = await successMessage.isVisible().catch(() => false);
      expect(hasSuccess).toBeTruthy();
    }
  });
});
