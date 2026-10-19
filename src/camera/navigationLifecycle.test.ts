import { describe, expect, it } from 'vitest';
import { NavigationLifecycle } from './navigationLifecycle';

describe('NavigationLifecycle', () => {
  it('suspends on blur and discards the first update after focus returns', () => {
    const lifecycle = new NavigationLifecycle(true, true);

    lifecycle.setWindowFocused(false);
    expect(lifecycle.isSuspended).toBe(true);
    expect(lifecycle.shouldSkipUpdate()).toBe(true);

    lifecycle.setWindowFocused(true);
    expect(lifecycle.isSuspended).toBe(false);
    expect(lifecycle.shouldSkipUpdate()).toBe(true);
    expect(lifecycle.shouldSkipUpdate()).toBe(false);
  });

  it('suspends while hidden and waits for both visibility and focus to resume', () => {
    const lifecycle = new NavigationLifecycle(true, true);

    lifecycle.setDocumentVisible(false);
    expect(lifecycle.shouldSkipUpdate()).toBe(true);
    lifecycle.setWindowFocused(false);
    lifecycle.setDocumentVisible(true);
    expect(lifecycle.isSuspended).toBe(true);
    expect(lifecycle.shouldSkipUpdate()).toBe(true);

    lifecycle.setWindowFocused(true);
    expect(lifecycle.shouldSkipUpdate()).toBe(true);
    expect(lifecycle.shouldSkipUpdate()).toBe(false);
  });

  it('does not repeatedly discard frames for duplicate active-state events', () => {
    const lifecycle = new NavigationLifecycle(true, true);
    lifecycle.setWindowFocused(false);
    lifecycle.setWindowFocused(true);
    lifecycle.setWindowFocused(true);

    expect(lifecycle.shouldSkipUpdate()).toBe(true);
    expect(lifecycle.shouldSkipUpdate()).toBe(false);
  });
});
