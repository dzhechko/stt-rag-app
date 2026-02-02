# Frontend Tests

This directory contains comprehensive tests for the STT App frontend using Vitest and React Testing Library.

## Test Structure

```
tests/
├── __tests__/
│   ├── components/
│   │   ├── UploadPage.test.jsx
│   │   ├── TranscriptsPage.test.jsx
│   │   ├── TranscriptDetailPage.test.jsx
│   │   └── RAGChat.test.jsx
│   └── api/
│       └── client.test.js
├── utils/
│   └── test-utils.js
├── setup.js
└── README.md
```

## Test Coverage

### Components

#### UploadPage.test.jsx
- File drag and drop functionality
- File selection dialog
- Upload progress display
- Polling for transcription status
- Error states (upload errors, transcription failures)
- Language selection
- File format validation (mp3, mp4, mpeg, mpga, m4a, wav, webm)
- File removal
- Redirect on completion
- Accessibility checks
- Keyboard navigation

#### TranscriptsPage.test.jsx
- Transcript listing
- Filtering by status (pending, processing, completed, failed)
- Filtering by language
- Combined filters
- Search functionality
- Pagination
- Delete confirmation
- Summary modal trigger
- Transcript preview (expand/collapse)
- View modes (text, JSON, SRT)
- Progress display for processing transcripts
- Empty states
- Accessibility
- Responsive behavior

#### TranscriptDetailPage.test.jsx
- Transcript display
- Text editing navigation
- Summary display and management
- Translation functionality
  - Language switcher
  - Translation progress
  - Model selection
  - Time estimates
- RAG indexing
  - Index status display
  - Reindexing trigger
  - Progress tracking
- Download actions (text, JSON, SRT)
- Jobs display
- Copy to clipboard
- Navigation
- Polling for updates
- Error handling
- Loading states
- Accessibility

#### RAGChat.test.jsx
- Chat message display
  - User questions
  - Assistant answers
  - Quality scores
  - Quality metrics
  - Retrieved chunks
- Input handling
  - Send on Enter
  - Shift+Enter for new line
  - Disabled state during loading
  - Empty message validation
- Transcript selection
- Session management
  - Create session
  - Select session
  - Delete session
  - Clear history
- Session loading
- Settings (top_k, model, temperature, query expansion, etc.)
- Loading states
- Feedback buttons (positive/negative)
- Copy button
- Navigation
- Accessibility

### API Tests

#### client.test.js
- `uploadFile` - with/without language, progress tracking, error handling
- `getTranscripts` - pagination, filters, empty/null filter removal
- `getTranscript` - fetch by id, error handling
- `deleteTranscript` - delete by id, error handling
- `getJobs` / `getTranscriptJobs` - fetch transcript jobs
- `createSummary` - create summary with template/model
- `getSummaries` - fetch all summaries for transcript
- `getSummary` - fetch single summary
- `getRAGSessions` - fetch all sessions
- `createRAGSession` - create new session
- `deleteRAGSession` - delete session
- `getTranscriptIndexStatus` - check index status
- `reindexTranscript` - trigger reindexing
- `translateTranscript` - translate to target language, model selection
- Error handling (network, HTTP, timeout)
- Request/response format validation

## Running Tests

### Run all tests
```bash
npm test
```

### Run tests in watch mode
```bash
npm run test:watch
```

### Run tests with coverage
```bash
npm run test:coverage
```

### Run specific test file
```bash
npm test -- UploadPage.test.jsx
```

### Run tests matching a pattern
```bash
npm test -- --grep "drag and drop"
```

## Test Utilities

The `tests/utils/test-utils.js` file provides:

- **Mock data** - Sample transcripts, jobs, summaries, sessions, messages
- **renderWithProviders** - Custom render with React Query and Router
- **createMockFile** - Helper to create File objects
- **createMockProgressEvent** - Mock upload progress events
- **waitForAsync** - Helper for async operations
- **Global mocks** - IntersectionObserver, ResizeObserver, FormData

## Writing New Tests

1. Create test file in appropriate directory
2. Import necessary dependencies:
   ```jsx
   import { render, screen, fireEvent, waitFor } from '@testing-library/react'
   import { describe, it, expect, vi, beforeEach } from 'vitest'
   ```

3. Mock API calls:
   ```jsx
   vi.mock('../../../src/api/client', () => ({
     someFunction: vi.fn()
   }))
   ```

4. Write test cases:
   ```jsx
   describe('Component', () => {
     it('should do something', async () => {
       // Arrange
       const mockData = { ... }
       client.someFunction.mockResolvedValue(mockData)

       // Act
       render(<Component />)

       // Assert
       await waitFor(() => {
         expect(screen.getByText('Something')).toBeInTheDocument()
       })
     })
   })
   ```

## Best Practices

1. **Test user behavior, not implementation details**
   - Test what users see and interact with
   - Avoid testing internal state or methods

2. **Use waitFor for async operations**
   - Wrap assertions that depend on async state changes
   - Provide appropriate timeout if needed

3. **Mock external dependencies**
   - Mock API calls
   - Mock router/navigation
   - Mock browser APIs (clipboard, URL, etc.)

4. **Keep tests isolated**
   - Clear mocks in beforeEach
   - Use unique data for each test
   - Avoid shared state between tests

5. **Test accessibility**
   - Check ARIA labels and roles
   - Test keyboard navigation
   - Verify semantic HTML

6. **Test error states**
   - Test API failures
   - Test validation errors
   - Test edge cases

## Coverage Goals

- **Statements**: 80%+
- **Branches**: 75%+
- **Functions**: 80%+
- **Lines**: 80%+

## Troubleshooting

### Tests timing out
- Increase timeout: `it('test', async () => {}, { timeout: 10000 })`
- Check for pending promises
- Verify timers are cleaned up

### Mocks not working
- Clear mocks in beforeEach: `vi.clearAllMocks()`
- Mock before importing component
- Check mock path is correct

### React not defined
- Ensure @testing-library/react is installed
- Check vitest.config.js has correct environment (jsdom)

### Router/navigation issues
- Use MemoryRouter in tests
- Mock useNavigate if needed
- Provide initialEntries for routing tests

## Additional Resources

- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library Documentation](https://testing-library.com/docs/react-testing-library/intro/)
- [Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)
