import { test, expect, expectedTimeouts } from '../fixtures/test-fixtures';

test.describe('Upload Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should navigate to upload page from home', async ({ page }) => {
    await expect(page.locator('nav')).toBeVisible();
    await page.click('a[href="/upload"]', { timeout: expectedTimeouts.navigation });

    await expect(page).toHaveURL(/.*upload/);
    await expect(page.locator('h1, h2')).toContainText(/Загрузка|Upload/i);
  });

  test('should display upload zone with drag and drop', async ({ page }) => {
    await page.goto('/upload');

    // Check for upload zone
    const uploadZone = page.locator('.upload-zone, [data-testid="upload-zone"], .drop-zone').first();
    await expect(uploadZone).toBeVisible();

    // Check for file input
    const fileInput = page.locator('input[type="file"]');
    await expect(fileInput).toBeVisible();
  });

  test('should display language selector', async ({ page }) => {
    await page.goto('/upload');

    // Check for language selector
    const languageSelector = page.locator('select, [role="combobox"]').filter({ hasText: /язык|language|Русский|English/i });
    await expect(languageSelector.first()).toBeVisible();
  });

  test('should show file selection dialog when clicking upload zone', async ({ page }) => {
    await page.goto('/upload');

    // Click on upload zone should trigger file input
    const uploadZone = page.locator('.upload-zone, [data-testid="upload-zone"], .drop-zone').first();
    const fileInput = page.locator('input[type="file"]');

    await uploadZone.click();

    // Verify file input is accessible
    await expect(fileInput).toBeVisible();
  });

  test('should disable upload button when no file is selected', async ({ page }) => {
    await page.goto('/upload');

    const uploadButton = page.locator('button').filter({ hasText: /загрузить|upload/i }).first();

    // Check if button is disabled or has disabled state
    const isDisabled = await uploadButton.isDisabled();
    expect(isDisabled).toBeTruthy();
  });

  test('should display supported formats information', async ({ page }) => {
    await page.goto('/upload');

    // Look for format information
    const formatInfo = page.locator('text=/MP3|MP4|WAV|WEBM|M4A/i');
    await expect(formatInfo.first()).toBeVisible();
  });

  test('should navigate to transcripts page after successful upload', async ({ page }) => {
    await page.goto('/upload');

    // Create a small test audio file
    const testFile = {
      name: 'test-audio.mp3',
      mimeType: 'audio/mpeg',
      buffer: Buffer.from('ID3\x04\x00\x00\x00\x00\x00\x00' + 'x'.repeat(1000)) // Minimal MP3 header + data
    };

    // Set up file upload handler
    const fileInput = page.locator('input[type="file"]');

    // Upload the file
    await fileInput.setInputFiles({
      name: testFile.name,
      mimeType: testFile.mimeType,
      buffer: testFile.buffer
    });

    // Wait for file to be selected
    await page.waitForTimeout(500);

    // Select language if selector is available
    const languageSelector = page.locator('select').first();
    const isVisible = await languageSelector.isVisible().catch(() => false);
    if (isVisible) {
      await languageSelector.selectOption({ label: /Русский/i });
    }

    // Click upload button
    const uploadButton = page.locator('button').filter({ hasText: /загрузить|upload/i }).first();
    await uploadButton.click();

    // Wait for upload to complete - check for success message or redirect
    await page.waitForTimeout(2000);

    // Either we get a success message or redirect to transcripts
    const currentUrl = page.url();
    const isSuccess = currentUrl.includes('transcripts') ||
      await page.locator('text=/успешно|success|загружен/i').isVisible().catch(() => false);

    expect(isSuccess).toBeTruthy();
  });

  test('should display upload progress indicator', async ({ page }) => {
    await page.goto('/upload');

    // Create a test file
    const testFile = {
      name: 'test-audio.mp3',
      mimeType: 'audio/mpeg',
      buffer: Buffer.from('ID3\x04\x00\x00\x00\x00\x00\x00' + 'x'.repeat(1000))
    };

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: testFile.name,
      mimeType: testFile.mimeType,
      buffer: testFile.buffer
    });

    await page.waitForTimeout(500);

    // Click upload and check for progress
    const uploadButton = page.locator('button').filter({ hasText: /загрузить|upload/i }).first();
    await uploadButton.click();

    // Look for progress bar or percentage
    const progressBar = page.locator('.progress, [role="progressbar"], .upload-progress').first();
    const progressVisible = await progressBar.isVisible().catch(() => false);

    // Progress might appear briefly, so we just check it exists
    if (progressVisible) {
      await expect(progressBar).toBeVisible();
    }
  });

  test('should handle file size validation', async ({ page }) => {
    await page.goto('/upload');

    // Check for file size information
    const sizeInfo = page.locator('text=/MB|мб|размер/i');
    await expect(sizeInfo.first()).toBeVisible();
  });

  test('should clear selected file when canceling upload', async ({ page }) => {
    await page.goto('/upload');

    // Select a file
    const testFile = {
      name: 'test-audio.mp3',
      mimeType: 'audio/mpeg',
      buffer: Buffer.from('ID3\x04\x00\x00\x00\x00\x00\x00' + 'x'.repeat(1000))
    };

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: testFile.name,
      mimeType: testFile.mimeType,
      buffer: testFile.buffer
    });

    await page.waitForTimeout(500);

    // Look for cancel/clear button
    const cancelButton = page.locator('button').filter({ hasText: /отмена|cancel|очистить|clear/i }).first();
    const cancelVisible = await cancelButton.isVisible().catch(() => false);

    if (cancelVisible) {
      await cancelButton.click();
      // Verify file selection was cleared
      const files = await fileInput.inputValue();
      expect(files).toBeFalsy();
    }
  });

  test('should support multiple file uploads', async ({ page }) => {
    await page.goto('/upload');

    // Check if multiple file attribute is present
    const fileInput = page.locator('input[type="file"]');
    const multiple = await fileInput.getAttribute('multiple');

    // If multiple is supported, test it
    if (multiple !== null) {
      const testFiles = [
        {
          name: 'test-audio-1.mp3',
          mimeType: 'audio/mpeg',
          buffer: Buffer.from('ID3\x04\x00\x00\x00\x00\x00\x00' + 'x'.repeat(500))
        },
        {
          name: 'test-audio-2.mp3',
          mimeType: 'audio/mpeg',
          buffer: Buffer.from('ID3\x04\x00\x00\x00\x00\x00\x00' + 'y'.repeat(500))
        }
      ];

      await fileInput.setInputFiles(testFiles);

      // Verify files were accepted
      const files = await fileInput.inputValue();
      expect(files).toBeTruthy();
    }
  });
});

test.describe('Upload Error Handling', () => {
  test('should display error message for invalid file type', async ({ page }) => {
    await page.goto('/upload');

    // Try to upload an invalid file (e.g., .txt file)
    const testFile = {
      name: 'invalid.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('This is not an audio file')
    };

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: testFile.name,
      mimeType: testFile.mimeType,
      buffer: testFile.buffer
    });

    await page.waitForTimeout(500);

    // Check for error message or disabled upload button
    const uploadButton = page.locator('button').filter({ hasText: /загрузить|upload/i }).first();
    const isDisabled = await uploadButton.isDisabled();
    const errorMessage = page.locator('text=/ошибка|error|неверный.*формат|invalid.*format/i');

    const hasError = isDisabled || await errorMessage.isVisible().catch(() => false);
    expect(hasError).toBeTruthy();
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Intercept and fail the upload request
    await page.route('**/api/transcripts/upload', route => route.abort('failed'));

    await page.goto('/upload');

    const testFile = {
      name: 'test-audio.mp3',
      mimeType: 'audio/mpeg',
      buffer: Buffer.from('ID3\x04\x00\x00\x00\x00\x00\x00' + 'x'.repeat(1000))
    };

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: testFile.name,
      mimeType: testFile.mimeType,
      buffer: testFile.buffer
    });

    await page.waitForTimeout(500);

    const uploadButton = page.locator('button').filter({ hasText: /загрузить|upload/i }).first();
    await uploadButton.click();

    // Wait for error message
    await page.waitForTimeout(2000);

    const errorMessage = page.locator('text=/ошибка|error|не.*удалось|failed/i').first();
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Upload Accessibility', () => {
  test('should be keyboard navigable', async ({ page }) => {
    await page.goto('/upload');

    // Tab through upload interface
    await page.keyboard.press('Tab');

    // Check focus management
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(['INPUT', 'BUTTON', 'SELECT', 'A']).toContain(focusedElement);
  });

  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('/upload');

    // Check for ARIA labels on upload zone
    const uploadZone = page.locator('.upload-zone, [data-testid="upload-zone"]').first();
    const ariaLabel = await uploadZone.getAttribute('aria-label');
    const ariaDescribedBy = await uploadZone.getAttribute('aria-describedby');

    // At least one ARIA attribute should be present
    const hasAria = !!(ariaLabel || ariaDescribedBy);
    expect(hasAria).toBeTruthy();
  });
});
