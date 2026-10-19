export type FocusMonitorEventType = 'blur' | 'focus' | 'visibilitychange';

export interface FocusMonitorEvent {
  type: FocusMonitorEventType;
  elapsedMs: number;
  hidden: boolean;
  focused: boolean;
}

export interface FocusMonitorSnapshot {
  hiddenAtStart: boolean;
  hiddenDuringRun: boolean;
  hiddenAtEnd: boolean;
  focusedAtStart: boolean;
  focusedAtEnd: boolean;
  focusLostDuringRun: boolean;
  frameSampleCount: number;
  stateEvents: FocusMonitorEvent[];
  validForVisibleFocusedBenchmark: boolean;
}

export interface FocusEventTarget {
  addEventListener(type: 'blur' | 'focus', listener: () => void): void;
  removeEventListener(type: 'blur' | 'focus', listener: () => void): void;
}

export interface FocusDocumentState {
  readonly hidden: boolean;
  hasFocus(): boolean;
  addEventListener(type: 'visibilitychange', listener: () => void): void;
  removeEventListener(type: 'visibilitychange', listener: () => void): void;
}

export interface FocusMonitor {
  sampleFrame(): void;
  snapshot(): FocusMonitorSnapshot;
  dispose(): void;
}

export declare function createFocusMonitor(
  windowTarget: FocusEventTarget,
  documentState: FocusDocumentState,
  now?: () => number,
): FocusMonitor;
