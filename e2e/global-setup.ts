import { FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting E2E test setup...');
  console.log('Base URL:', process.env.BASE_URL || 'http://localhost:5173');
  console.log('Environment:', process.env.NODE_ENV || 'development');
}

export default globalSetup;
