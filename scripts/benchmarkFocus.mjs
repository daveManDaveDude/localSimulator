/**
 * Tracks focus and visibility for one timed browser benchmark run.
 *
 * Blur events are recorded even when focus returns between animation frames,
 * because that interruption can affect frame cadence without being visible to
 * frame-by-frame document.hasFocus() samples.
 */
export function createFocusMonitor(windowTarget, documentState, now) {
  const clock = now ?? (() => performance.now());
  const startedAt = clock();
  const hiddenAtStart = Boolean(documentState.hidden);
  const focusedAtStart = Boolean(documentState.hasFocus());
  let hiddenDuringRun = hiddenAtStart;
  let focusLostDuringRun = !focusedAtStart;
  let frameSampleCount = 0;
  let disposed = false;
  const stateEvents = [];

  const recordEvent = (type) => {
    const hidden = Boolean(documentState.hidden);
    const focused = Boolean(documentState.hasFocus());
    if (hidden) hiddenDuringRun = true;
    if (!focused || type === 'blur') focusLostDuringRun = true;
    stateEvents.push({
      type,
      elapsedMs: Math.max(0, Number((clock() - startedAt).toFixed(2))),
      hidden,
      focused,
    });
  };
  const handleBlur = () => recordEvent('blur');
  const handleFocus = () => recordEvent('focus');
  const handleVisibilityChange = () => recordEvent('visibilitychange');

  windowTarget.addEventListener('blur', handleBlur);
  windowTarget.addEventListener('focus', handleFocus);
  documentState.addEventListener('visibilitychange', handleVisibilityChange);

  return {
    sampleFrame() {
      frameSampleCount += 1;
      if (documentState.hidden) hiddenDuringRun = true;
      if (!documentState.hasFocus()) focusLostDuringRun = true;
    },
    snapshot() {
      const hiddenAtEnd = Boolean(documentState.hidden);
      const focusedAtEnd = Boolean(documentState.hasFocus());
      if (hiddenAtEnd) hiddenDuringRun = true;
      if (!focusedAtEnd) focusLostDuringRun = true;
      return {
        hiddenAtStart,
        hiddenDuringRun,
        hiddenAtEnd,
        focusedAtStart,
        focusedAtEnd,
        focusLostDuringRun,
        frameSampleCount,
        stateEvents: stateEvents.map((event) => ({ ...event })),
        validForVisibleFocusedBenchmark:
          !hiddenAtStart &&
          !hiddenDuringRun &&
          !hiddenAtEnd &&
          focusedAtStart &&
          focusedAtEnd &&
          !focusLostDuringRun,
      };
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      windowTarget.removeEventListener('blur', handleBlur);
      windowTarget.removeEventListener('focus', handleFocus);
      documentState.removeEventListener(
        'visibilitychange',
        handleVisibilityChange,
      );
    },
  };
}
