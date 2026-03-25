import "@testing-library/jest-dom/vitest";

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

class IntersectionObserverMock implements IntersectionObserver {
  readonly root: Element | Document | null;
  readonly rootMargin: string;
  readonly thresholds: ReadonlyArray<number>;

  constructor(
    _callback: IntersectionObserverCallback,
    options: IntersectionObserverInit = {},
  ) {
    this.root = options.root ?? null;
    this.rootMargin = options.rootMargin ?? "0px";
    const threshold = options.threshold;
    this.thresholds = Array.isArray(threshold)
      ? threshold
      : threshold !== undefined
        ? [threshold]
        : [0];
  }

  observe(_target: Element) {
    void _target;
  }
  unobserve(_target: Element) {
    void _target;
  }
  disconnect() {}
  takeRecords() {
    return [];
  }
}

global.ResizeObserver = ResizeObserverMock;
global.IntersectionObserver = IntersectionObserverMock;
