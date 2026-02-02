import { FullConfig } from '@playwright/test';

async function globalTeardown(config: FullConfig) {
  console.log('✅ E2E tests completed');
  console.log('Cleaning up test artifacts...');
}

export default globalTeardown;
