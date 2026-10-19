import type { Camera } from 'three';

export interface AlignmentQaCameraPose {
  x: number;
  y: number;
  z: number;
  bearingDegrees: number;
  pitchDegrees: number;
}

export interface AlignmentQaCameraApi {
  setPose: (pose: AlignmentQaCameraPose) => void;
}

declare global {
  interface Window {
    __torquayAlignmentQa?: AlignmentQaCameraApi;
  }
}

/** Install the screenshot-only camera setter in development builds. */
export function installAlignmentQaCamera(
  target: Window,
  camera: Camera,
  isDevelopment: boolean,
): () => void {
  if (!isDevelopment) return () => undefined;

  const api: AlignmentQaCameraApi = {
    setPose: (pose) => {
      const values = [
        pose.x,
        pose.y,
        pose.z,
        pose.bearingDegrees,
        pose.pitchDegrees,
      ];
      if (values.some((value) => !Number.isFinite(value))) {
        throw new Error('Alignment QA camera pose values must be finite.');
      }
      if (Math.abs(pose.pitchDegrees) > 89) {
        throw new Error(
          'Alignment QA camera pitch must be between -89 and 89 degrees.',
        );
      }

      camera.rotation.order = 'YXZ';
      camera.rotation.set(
        (pose.pitchDegrees * Math.PI) / 180,
        (-pose.bearingDegrees * Math.PI) / 180,
        0,
      );
      camera.position.set(pose.x, pose.y, pose.z);
      camera.updateMatrixWorld(true);
    },
  };
  target.__torquayAlignmentQa = api;

  return () => {
    if (target.__torquayAlignmentQa === api) {
      delete target.__torquayAlignmentQa;
    }
  };
}
