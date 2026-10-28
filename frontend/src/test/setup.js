import "@testing-library/jest-dom/vitest";

// Recharts measures its container; jsdom has no layout, so give it a fake size.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverStub;
