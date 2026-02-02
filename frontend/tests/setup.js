/**
 * Test setup configuration for Vitest
 *
 * This file sets up the testing environment with:
 * - jsdom for DOM simulation
 * - React Testing Library utilities
 * - Global test configuration
 * - Custom matchers and mocks
 *
 * @module tests/setup
 */

import { beforeAll, afterEach, afterAll, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom'

// =============================================================================
// Cleanup
// =============================================================================

afterEach(() => {
  cleanup()
})

// =============================================================================
// Web API Mocks
// =============================================================================

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
  takeRecords: vi.fn(() => []),
}))

// Mock ResizeObserver
global.ResizeObserver = vi.fn(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock scrollTo
window.scrollTo = vi.fn()

// Mock navigator.clipboard
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn(() => Promise.resolve()),
    readText: vi.fn(() => Promise.resolve('mock clipboard text')),
  },
})

// Mock URL API
global.URL.createObjectURL = vi.fn(() => 'mock-blob-url')
global.URL.revokeObjectURL = vi.fn()

// =============================================================================
// Storage Mocks
// =============================================================================

// Mock localStorage
const localStorageMock = (() => {
  let store = {}
  return {
    getItem: vi.fn(key => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = value.toString()
    }),
    removeItem: vi.fn(key => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    get length() {
      return Object.keys(store).length
    },
    key: vi.fn(index => Object.keys(store)[index] || null),
  }
})()

global.localStorage = localStorageMock

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store = {}
  return {
    getItem: vi.fn(key => store[key] || null),
    setItem: vi.fn((key, value) => {
      store[key] = value.toString()
    }),
    removeItem: vi.fn(key => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
  }
})()

global.sessionStorage = sessionStorageMock

// =============================================================================
// Canvas Mocks
// =============================================================================

HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
  fillRect: vi.fn(),
  clearRect: vi.fn(),
  fillText: vi.fn(),
  drawImage: vi.fn(),
  getImageData: vi.fn(),
  putImageData: vi.fn(),
  createImageData: vi.fn(),
  setTransform: vi.fn(),
  resetTransform: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  scale: vi.fn(),
  rotate: vi.fn(),
  translate: vi.fn(),
  transform: vi.fn(),
  beginPath: vi.fn(),
  closePath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  bezierCurveTo: vi.fn(),
  quadraticCurveTo: vi.fn(),
  arc: vi.fn(),
  arcTo: vi.fn(),
  ellipse: vi.fn(),
  rect: vi.fn(),
  clip: vi.fn(),
  fill: vi.fn(),
  stroke: vi.fn(),
  measureText: vi.fn(() => ({ width: 0 })),
  createLinearGradient: vi.fn(() => ({
    addColorStop: vi.fn(),
  })),
  createRadialGradient: vi.fn(() => ({
    addColorStop: vi.fn(),
  })),
  createPattern: vi.fn(),
}))

// =============================================================================
// Console Management
// =============================================================================

const originalError = console.error
const originalWarn = console.warn

// Suppress specific warnings in tests
beforeAll(() => {
  console.error = (...args) => {
    const errorMessage = args[0]
    if (
      typeof errorMessage === 'string' &&
      (errorMessage.includes('Warning: ReactDOM.render') ||
        errorMessage.includes('Not implemented:') ||
        errorMessage.includes('Warning: useLayoutEffect'))
    ) {
      return
    }
    originalError.call(console, ...args)
  }

  console.warn = (...args) => {
    const warnMessage = args[0]
    if (
      typeof warnMessage === 'string' &&
      (warnMessage.includes('componentWillReceiveProps') ||
        warnMessage.includes('componentWillMount'))
    ) {
      return
    }
    originalWarn.call(console, ...args)
  }
})

afterAll(() => {
  console.error = originalError
  console.warn = originalWarn
})

// =============================================================================
// Test Utilities
// =============================================================================

/**
 * Wait for a specified number of milliseconds
 * @param {number} ms - Milliseconds to wait
 */
export const wait = ms => new Promise(resolve => setTimeout(resolve, ms))

/**
 * Wait for the next tick
 */
export const tick = () => new Promise(resolve => setTimeout(resolve, 0))

/**
 * Flush all pending promises
 */
export const flushPromises = () => new Promise(resolve => setImmediate(resolve))

// =============================================================================
// Global Test Configuration
// =============================================================================

// Increase timeout for integration tests
vi.setConfig({
  testTimeout: 10000,
  hookTimeout: 10000,
})

// =============================================================================
// Mock Performance API
// =============================================================================

global.performance = {
  ...global.performance,
  now: vi.fn(() => Date.now()),
}

// =============================================================================
// Mock Animation Frame
// =============================================================================

global.requestAnimationFrame = callback => setTimeout(callback, 0)
global.cancelAnimationFrame = id => clearTimeout(id)

// =============================================================================
// Mock Fetch (can be overridden in specific tests)
// =============================================================================

global.fetch = vi.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: async () => ({}),
    text: async () => '',
    blob: async () => new Blob(),
    headers: new Headers(),
  })
)

// =============================================================================
// Export utilities for use in tests
// =============================================================================

export {
  localStorageMock,
  sessionStorageMock,
}
