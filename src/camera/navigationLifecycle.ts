/** Tracks page activity and discards the first frame after a suspended period. */
export class NavigationLifecycle {
  private windowFocused: boolean;
  private documentVisible: boolean;
  private discardResumeFrame = false;

  constructor(windowFocused: boolean, documentVisible: boolean) {
    this.windowFocused = windowFocused;
    this.documentVisible = documentVisible;
  }

  get isSuspended(): boolean {
    return !this.windowFocused || !this.documentVisible;
  }

  setWindowFocused(focused: boolean): void {
    const wasSuspended = this.isSuspended;
    this.windowFocused = focused;
    this.noteResume(wasSuspended);
  }

  setDocumentVisible(visible: boolean): void {
    const wasSuspended = this.isSuspended;
    this.documentVisible = visible;
    this.noteResume(wasSuspended);
  }

  /** True means this animation update must not move the camera. */
  shouldSkipUpdate(): boolean {
    if (this.isSuspended) return true;
    if (!this.discardResumeFrame) return false;
    this.discardResumeFrame = false;
    return true;
  }

  private noteResume(wasSuspended: boolean): void {
    if (wasSuspended && !this.isSuspended) {
      this.discardResumeFrame = true;
    }
  }
}
