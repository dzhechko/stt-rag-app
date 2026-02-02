import { test as base } from '@playwright/test';

export const expectedTimeouts = {
  upload: 60000, // 60 seconds for file upload
  transcription: 300000, // 5 minutes for transcription
  summarization: 120000, // 2 minutes for summarization
  ragQuery: 60000, // 60 seconds for RAG query
  navigation: 5000, // 5 seconds for page navigation
  apiCall: 30000, // 30 seconds for API calls
};

export interface TestFixtures {
  baseURL: string;
  apiURL: string;
}

export const test = base.extend<TestFixtures>({
  baseURL: async ({}, use) => {
    await use(process.env.BASE_URL || 'http://localhost:5173');
  },
  apiURL: async ({}, use) => {
    await use(process.env.API_URL || 'http://localhost:8000/api');
  },
});

export { expect } from '@playwright/test';
