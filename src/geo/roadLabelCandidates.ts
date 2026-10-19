import type { LoadedRoadPackage } from './roadSchema';

export const ROAD_LABEL_GROUND_OFFSET_M = 0.25;
export const ROAD_LABEL_MAX_DISTANCE_M = 500;
export const ROAD_LABEL_MAX_VISIBLE = 20;
export const ROAD_LABEL_COLLISION_PADDING_PX = 6;

export interface RoadLabelCandidate {
  readonly key: string;
  readonly roadId: string;
  readonly wayId: number;
  readonly partIndex: number;
  readonly name: string;
  readonly x: number;
  readonly y: number;
  readonly z: number;
}

export interface ProjectedRoadLabel {
  readonly candidate: RoadLabelCandidate;
  distanceM: number;
  screenX: number;
  screenY: number;
  width: number;
  height: number;
  projected: boolean;
}

export interface ScreenRect {
  readonly left: number;
  readonly top: number;
  readonly right: number;
  readonly bottom: number;
}

export interface RoadLabelSelectionOptions {
  maxDistanceM?: number;
  maxVisible?: number;
  collisionPaddingPx?: number;
}

function midpointOfPart(
  part: readonly (readonly number[])[],
): readonly [number, number] | null {
  if (part.length < 2) return null;

  let totalLength = 0;
  for (let index = 1; index < part.length; index += 1) {
    const previous = part[index - 1];
    const current = part[index];
    if (
      previous === undefined ||
      current === undefined ||
      previous.length < 2 ||
      current.length < 2 ||
      !Number.isFinite(previous[0]) ||
      !Number.isFinite(previous[1]) ||
      !Number.isFinite(current[0]) ||
      !Number.isFinite(current[1])
    ) {
      return null;
    }
    totalLength += Math.hypot(
      current[0]! - previous[0]!,
      current[1]! - previous[1]!,
    );
  }
  if (!Number.isFinite(totalLength) || totalLength <= 0) return null;

  const midpointDistance = totalLength / 2;
  let travelled = 0;
  for (let index = 1; index < part.length; index += 1) {
    const previous = part[index - 1];
    const current = part[index];
    if (previous === undefined || current === undefined) return null;
    const dx = current[0]! - previous[0]!;
    const dz = current[1]! - previous[1]!;
    const length = Math.hypot(dx, dz);
    if (length <= 0) continue;
    if (travelled + length >= midpointDistance) {
      const fraction = (midpointDistance - travelled) / length;
      return [previous[0]! + dx * fraction, previous[1]! + dz * fraction];
    }
    travelled += length;
  }
  return null;
}

/** Build one terrain-relative label anchor for each named clipped line part. */
export function createRoadLabelCandidates(
  roadPackage: LoadedRoadPackage,
  sampleHeight: (x: number, z: number) => number | null,
): RoadLabelCandidate[] {
  const candidates: RoadLabelCandidate[] = [];
  for (const feature of roadPackage.features) {
    const sourceName = feature.sourceTags.name;
    if (typeof sourceName !== 'string') continue;
    const name = sourceName.trim();
    if (!name) continue;

    feature.centerlinePartsXZ.forEach((part, partIndex) => {
      const midpoint = midpointOfPart(part);
      if (midpoint === null) return;
      const [x, z] = midpoint;
      const ground = sampleHeight(x, z);
      if (ground === null || !Number.isFinite(ground)) return;
      const y = ground + ROAD_LABEL_GROUND_OFFSET_M;
      if (!Number.isFinite(y)) return;
      candidates.push({
        key: `${feature.source.osmId}:${partIndex}`,
        roadId: feature.id,
        wayId: feature.source.osmId,
        partIndex,
        name,
        x,
        y,
        z,
      });
    });
  }
  return candidates;
}

/**
 * Select an in-place, deterministic screen-space subset. `candidates`,
 * `placements`, and `seenNames` are caller-owned reusable buffers so frame
 * updates do not allocate candidate arrays or DOM nodes.
 */
export function selectRoadLabelPlacements(
  candidates: ProjectedRoadLabel[],
  obstacles: readonly ScreenRect[],
  viewportWidth: number,
  viewportHeight: number,
  placements: ProjectedRoadLabel[],
  seenNames: Set<string>,
  options: RoadLabelSelectionOptions = {},
): number {
  const maxDistanceM = options.maxDistanceM ?? ROAD_LABEL_MAX_DISTANCE_M;
  const maxVisible = options.maxVisible ?? ROAD_LABEL_MAX_VISIBLE;
  const padding = options.collisionPaddingPx ?? ROAD_LABEL_COLLISION_PADDING_PX;
  placements.length = 0;
  seenNames.clear();
  candidates.sort((left, right) => {
    const distanceOrder = left.distanceM - right.distanceM;
    if (distanceOrder !== 0) return distanceOrder;
    const roadOrder = left.candidate.roadId.localeCompare(
      right.candidate.roadId,
    );
    if (roadOrder !== 0) return roadOrder;
    return left.candidate.partIndex - right.candidate.partIndex;
  });

  let eligibleAnchors = 0;
  for (const candidate of candidates) {
    if (
      !candidate.projected ||
      !Number.isFinite(candidate.distanceM) ||
      candidate.distanceM > maxDistanceM ||
      !Number.isFinite(candidate.screenX) ||
      !Number.isFinite(candidate.screenY) ||
      candidate.width <= 0 ||
      candidate.height <= 0
    ) {
      continue;
    }
    const halfWidth = candidate.width / 2;
    const halfHeight = candidate.height / 2;
    const left = candidate.screenX - halfWidth;
    const right = candidate.screenX + halfWidth;
    const top = candidate.screenY - halfHeight;
    const bottom = candidate.screenY + halfHeight;
    if (
      left < 0 ||
      top < 0 ||
      right > viewportWidth ||
      bottom > viewportHeight
    ) {
      continue;
    }
    eligibleAnchors += 1;
    if (placements.length >= maxVisible) continue;
    if (seenNames.has(candidate.candidate.name)) continue;
    if (overlapsAny(left, top, right, bottom, obstacles, padding)) continue;
    let collides = false;
    for (const placed of placements) {
      if (
        rectsOverlap(
          left,
          top,
          right,
          bottom,
          placed.screenX - placed.width / 2,
          placed.screenY - placed.height / 2,
          placed.screenX + placed.width / 2,
          placed.screenY + placed.height / 2,
          padding,
        )
      ) {
        collides = true;
        break;
      }
    }
    if (!collides) {
      seenNames.add(candidate.candidate.name);
      placements.push(candidate);
    }
  }
  return eligibleAnchors;
}

function overlapsAny(
  left: number,
  top: number,
  right: number,
  bottom: number,
  obstacles: readonly ScreenRect[],
  padding: number,
): boolean {
  for (const obstacle of obstacles) {
    if (
      rectsOverlap(
        left,
        top,
        right,
        bottom,
        obstacle.left,
        obstacle.top,
        obstacle.right,
        obstacle.bottom,
        padding,
      )
    ) {
      return true;
    }
  }
  return false;
}

function rectsOverlap(
  left: number,
  top: number,
  right: number,
  bottom: number,
  otherLeft: number,
  otherTop: number,
  otherRight: number,
  otherBottom: number,
  padding: number,
): boolean {
  return !(
    right + padding <= otherLeft ||
    left >= otherRight + padding ||
    bottom + padding <= otherTop ||
    top >= otherBottom + padding
  );
}
