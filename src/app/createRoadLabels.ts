import { PerspectiveCamera, Vector3 } from 'three';
import type { LoadedRoadPackage } from '../geo/roadSchema';
import {
  createRoadLabelCandidates,
  selectRoadLabelPlacements,
  type ProjectedRoadLabel,
  type RoadLabelCandidate,
} from '../geo/roadLabelCandidates';

interface LabelState {
  candidate: RoadLabelCandidate;
  anchor: Vector3;
  projected: ProjectedRoadLabel;
}

interface RoadLabelOverlayOptions {
  shell: HTMLElement;
  camera: PerspectiveCamera;
  toggle: HTMLButtonElement;
  status: HTMLOutputElement;
}

export interface RoadLabelOverlay {
  setPackage: (
    roadPackage: LoadedRoadPackage,
    sampleHeight: (x: number, z: number) => number | null,
  ) => void;
  clear: () => void;
  setRoadVisible: (visible: boolean) => void;
  toggle: () => void;
  update: () => void;
  dispose: () => void;
}

const LABEL_POOL_SIZE = 20;
const LABEL_PANEL_SELECTORS = [
  '.viewer-topline',
  '.world-selector',
  '.debug-hud',
  '.building-controls',
  '.road-controls',
  '.controls-help',
  '.overview-panel',
  '.start-card',
  '.corner-note',
] as const;

function createMutableRect(): {
  left: number;
  top: number;
  right: number;
  bottom: number;
} {
  return { left: 0, top: 0, right: 0, bottom: 0 };
}

/** A bounded DOM annotation layer. It has no pointer handlers and never owns the camera. */
export function createRoadLabelOverlay({
  shell,
  camera,
  toggle,
  status,
}: RoadLabelOverlayOptions): RoadLabelOverlay {
  const root = document.createElement('div');
  root.className = 'road-label-overlay';
  root.setAttribute('aria-hidden', 'true');
  const labelNodes = Array.from({ length: LABEL_POOL_SIZE }, () => {
    const label = document.createElement('span');
    label.className = 'road-name-label';
    label.hidden = true;
    root.append(label);
    return label;
  });
  const measureNode = document.createElement('span');
  measureNode.className = 'road-name-label road-name-measure';
  measureNode.setAttribute('aria-hidden', 'true');
  root.append(measureNode);
  const viewerUi = shell.querySelector('.viewer-ui');
  if (!viewerUi) throw new Error('Viewer UI is missing for road labels.');
  shell.insertBefore(root, viewerUi);

  const panelElements = LABEL_PANEL_SELECTORS.map((selector) =>
    shell.querySelector<HTMLElement>(selector),
  ).filter((element): element is HTMLElement => element !== null);
  const panelRects = panelElements.map(() => createMutableRect());
  const stateByCandidate: LabelState[] = [];
  const projectedCandidates: ProjectedRoadLabel[] = [];
  const placements: ProjectedRoadLabel[] = [];
  const seenNames = new Set<string>();
  const widthByName = new Map<string, number>();
  const heightByName = new Map<string, number>();
  const cameraPosition = new Vector3();
  let roadVisible = false;
  let enabled = false;
  let disposed = false;
  let eligibleCount = 0;

  const renderState = (): void => {
    const canEnable = !disposed && stateByCandidate.length > 0 && roadVisible;
    toggle.disabled = !canEnable;
    toggle.setAttribute('aria-pressed', String(enabled && canEnable));
    toggle.textContent = `Street names: ${enabled && canEnable ? 'on' : 'off'}`;
    toggle.setAttribute('aria-label', 'Street names');
    if (!canEnable || !enabled) {
      for (const label of labelNodes) label.hidden = true;
      status.dataset.eligibleCount = String(canEnable ? eligibleCount : 0);
      status.dataset.visibleCount = '0';
      status.textContent = canEnable
        ? `${eligibleCount.toLocaleString()} eligible anchors · 0 visible · display diagnostics only`
        : 'Street-name annotations are off.';
    }
  };

  const clear = (): void => {
    stateByCandidate.length = 0;
    projectedCandidates.length = 0;
    placements.length = 0;
    seenNames.clear();
    widthByName.clear();
    heightByName.clear();
    eligibleCount = 0;
    enabled = false;
    roadVisible = false;
    for (const label of labelNodes) {
      label.textContent = '';
      delete label.dataset.roadLabelKey;
      label.hidden = true;
    }
    measureNode.textContent = '';
    renderState();
  };

  const setPackage = (
    roadPackage: LoadedRoadPackage,
    sampleHeight: (x: number, z: number) => number | null,
  ): void => {
    clear();
    const candidates = createRoadLabelCandidates(roadPackage, sampleHeight);
    eligibleCount = candidates.length;
    for (const candidate of candidates) {
      if (!widthByName.has(candidate.name)) {
        measureNode.textContent = candidate.name;
        const rect = measureNode.getBoundingClientRect();
        widthByName.set(candidate.name, rect.width);
        heightByName.set(candidate.name, rect.height);
      }
      const projected: ProjectedRoadLabel = {
        candidate,
        distanceM: Number.POSITIVE_INFINITY,
        screenX: Number.NaN,
        screenY: Number.NaN,
        width: widthByName.get(candidate.name) ?? 0,
        height: heightByName.get(candidate.name) ?? 0,
        projected: false,
      };
      stateByCandidate.push({
        candidate,
        anchor: new Vector3(candidate.x, candidate.y, candidate.z),
        projected,
      });
      projectedCandidates.push(projected);
    }
    measureNode.textContent = '';
    renderState();
  };

  const setRoadVisible = (visible: boolean): void => {
    roadVisible = visible;
    if (!visible) enabled = false;
    renderState();
  };

  const toggleEnabled = (): void => {
    if (disposed || !roadVisible || stateByCandidate.length === 0) return;
    enabled = !enabled;
    renderState();
  };

  const update = (): void => {
    if (disposed || !enabled || !roadVisible || stateByCandidate.length === 0) {
      return;
    }
    const shellRect = shell.getBoundingClientRect();
    const width = shell.clientWidth;
    const height = shell.clientHeight;
    if (width <= 0 || height <= 0) return;
    camera.updateMatrixWorld();
    camera.getWorldPosition(cameraPosition);
    for (const state of stateByCandidate) {
      const projected = state.projected;
      projected.distanceM = cameraPosition.distanceTo(state.anchor);
      state.anchor.project(camera);
      projected.projected =
        Number.isFinite(state.anchor.x) &&
        Number.isFinite(state.anchor.y) &&
        Number.isFinite(state.anchor.z) &&
        state.anchor.z >= -1 &&
        state.anchor.z <= 1;
      projected.screenX = ((state.anchor.x + 1) * width) / 2;
      projected.screenY = ((1 - state.anchor.y) * height) / 2;
      state.anchor.set(state.candidate.x, state.candidate.y, state.candidate.z);
    }

    for (let index = 0; index < panelElements.length; index += 1) {
      const element = panelElements[index];
      const rect = panelRects[index];
      if (!element || !rect) continue;
      if (element.hidden || getComputedStyle(element).display === 'none') {
        rect.left = rect.right = rect.top = rect.bottom = 0;
        continue;
      }
      const bounds = element.getBoundingClientRect();
      rect.left = bounds.left - shellRect.left;
      rect.right = bounds.right - shellRect.left;
      rect.top = bounds.top - shellRect.top;
      rect.bottom = bounds.bottom - shellRect.top;
    }

    const eligibleAnchors = selectRoadLabelPlacements(
      projectedCandidates,
      panelRects,
      width,
      height,
      placements,
      seenNames,
    );
    for (let index = 0; index < labelNodes.length; index += 1) {
      const label = labelNodes[index];
      const placement = placements[index];
      if (!label) continue;
      if (!placement) {
        label.hidden = true;
        continue;
      }
      if (label.textContent !== placement.candidate.name) {
        label.textContent = placement.candidate.name;
      }
      label.dataset.roadLabelKey = placement.candidate.key;
      label.hidden = false;
      label.style.left = `${placement.screenX}px`;
      label.style.top = `${placement.screenY}px`;
    }
    status.dataset.eligibleCount = String(eligibleAnchors);
    status.dataset.visibleCount = String(placements.length);
    status.textContent =
      `${eligibleAnchors.toLocaleString()} eligible anchors in view · ${placements.length} visible · ` +
      'display diagnostics only; labels are not terrain occlusion-aware or coverage metrics.';
  };

  const dispose = (): void => {
    if (disposed) return;
    disposed = true;
    clear();
    toggle.removeEventListener('click', toggleEnabled);
    root.remove();
    toggle.disabled = true;
    toggle.setAttribute('aria-pressed', 'false');
    toggle.textContent = 'Street names: off';
  };

  toggle.addEventListener('click', toggleEnabled);
  return {
    setPackage,
    clear,
    setRoadVisible,
    toggle: toggleEnabled,
    update,
    dispose,
  };
}
