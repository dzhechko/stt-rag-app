import { setupServer } from 'msw/node'
import { handlers } from './handlers'

// Setup MSW server for API mocking (optional, can be used instead of vi.mock)
export const server = setupServer(...handlers)

// Setup and teardown for MSW
export const setupMSW = () => {
  beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
  afterEach(() => server.resetHandlers())
  afterAll(() => server.close())
}
