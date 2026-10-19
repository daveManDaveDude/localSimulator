import { describe, expect, it } from 'vitest';
import { createFocusMonitor } from '../scripts/benchmarkFocus.mjs';

type EventName = 'blur' | 'focus' | 'visibilitychange';
type Listener = () => void;

function makeEventTarget() {
  const listeners = new Map<EventName, Set<Listener>>();
  return {
    addEventListener(type: EventName, listener: Listener) {
      const registered = listeners.get(type) ?? new Set<Listener>();
      registered.add(listener);
      listeners.set(type, registered);
    },
    removeEventListener(type: EventName, listener: Listener) {
      listeners.get(type)?.delete(listener);
    },
    dispatch(type: EventName) {
      for (const listener of listeners.get(type) ?? []) listener();
    },
    listenerCount(type: EventName) {
      return listeners.get(type)?.size ?? 0;
    },
  };
}

describe('benchmark focus monitor', () => {
  it('invalidates a run after transient blur and refocus between frame samples', () => {
    const windowTarget = makeEventTarget();
    const documentEvents = makeEventTarget();
    let focused = true;
    let elapsedMs = 0;
    const documentState = {
      hidden: false,
      hasFocus: () => focused,
      addEventListener: documentEvents.addEventListener,
      removeEventListener: documentEvents.removeEventListener,
    };
    const monitor = createFocusMonitor(
      windowTarget,
      documentState,
      () => elapsedMs,
    );

    elapsedMs = 20;
    focused = false;
    windowTarget.dispatch('blur');
    elapsedMs = 34;
    focused = true;
    windowTarget.dispatch('focus');
    monitor.sampleFrame();

    const snapshot = monitor.snapshot();
    expect(snapshot.focusedAtStart).toBe(true);
    expect(snapshot.focusedAtEnd).toBe(true);
    expect(snapshot.focusLostDuringRun).toBe(true);
    expect(snapshot.stateEvents.map((event) => event.type)).toEqual([
      'blur',
      'focus',
    ]);
    expect(snapshot.validForVisibleFocusedBenchmark).toBe(false);

    monitor.dispose();
    expect(windowTarget.listenerCount('blur')).toBe(0);
    expect(windowTarget.listenerCount('focus')).toBe(0);
    expect(documentEvents.listenerCount('visibilitychange')).toBe(0);
  });

  it('records visibility loss that occurs and clears between sampled frames', () => {
    const windowTarget = makeEventTarget();
    const documentEvents = makeEventTarget();
    let hidden = false;
    const documentState = {
      get hidden() {
        return hidden;
      },
      hasFocus: () => true,
      addEventListener: documentEvents.addEventListener,
      removeEventListener: documentEvents.removeEventListener,
    };
    const monitor = createFocusMonitor(windowTarget, documentState, () => 0);

    hidden = true;
    documentEvents.dispatch('visibilitychange');
    hidden = false;
    documentEvents.dispatch('visibilitychange');
    monitor.sampleFrame();

    expect(monitor.snapshot()).toMatchObject({
      hiddenDuringRun: true,
      hiddenAtEnd: false,
      validForVisibleFocusedBenchmark: false,
    });
    monitor.dispose();
  });
});
