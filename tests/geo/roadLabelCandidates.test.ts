import { describe, expect, it } from 'vitest';
import type { LoadedRoadPackage, RoadFeature } from '../../src/geo/roadSchema';
import {
  createRoadLabelCandidates,
  selectRoadLabelPlacements,
  type ProjectedRoadLabel,
  type RoadLabelCandidate,
  type ScreenRect,
} from '../../src/geo/roadLabelCandidates';

function feature(
  osmId: number,
  name: string | undefined,
  parts: [number, number][][],
): RoadFeature {
  return {
    id: `way/${osmId}`,
    source: {
      dataset: 'OpenStreetMap',
      objectType: 'way',
      osmId,
      version: 1,
      timestamp: null,
      nodeIds: [],
    },
    highway: 'residential',
    displayGroup: 'vehicular',
    estimatedWidthM: 6,
    widthMethod: 'configured_visual_estimate',
    widthEvidence: {
      rawWidth: null,
      rawLanes: null,
      usedRawTags: false,
      note: 'fictional test feature',
    },
    groundAssumption: 'ground_assumed_from_absent_or_explicit_no_vertical_tags',
    sourceTags: name === undefined ? {} : { name },
    centerlinePartsXZ: parts,
    partIds: parts.map((_, index) => `part/${osmId}/${index}`),
    clippedToAoi: true,
    duplicateWayIds: [],
    ribbonAreaM2: 1,
    ribbonPartIds: [],
  };
}

function packageOf(...features: RoadFeature[]): LoadedRoadPackage {
  return { features } as unknown as LoadedRoadPackage;
}

function candidate(
  name: string,
  key: string,
  roadId = key,
  partIndex = 0,
): RoadLabelCandidate {
  return {
    key,
    name,
    roadId,
    wayId: Number.parseInt(key.replace(/\D/g, ''), 10) || 1,
    partIndex,
    x: 0,
    y: 1,
    z: 0,
  };
}

function projected(
  value: RoadLabelCandidate,
  fields: Partial<ProjectedRoadLabel> = {},
): ProjectedRoadLabel {
  return {
    candidate: value,
    distanceM: 10,
    screenX: 100,
    screenY: 100,
    width: 50,
    height: 18,
    projected: true,
    ...fields,
  };
}

describe('createRoadLabelCandidates', () => {
  it('uses the arc-length midpoint of bent and reversed lines', () => {
    const roads = packageOf(
      feature(1, ' Bent Road ', [
        [
          [0, 0],
          [4, 0],
          [4, 3],
        ],
      ]),
      feature(2, 'Bent Road', [
        [
          [4, 3],
          [4, 0],
          [0, 0],
        ],
      ]),
    );
    const candidates = createRoadLabelCandidates(roads, () => 12);
    expect(candidates).toHaveLength(2);
    expect(candidates.map(({ x, y, z, name }) => [x, y, z, name])).toEqual([
      [3.5, 12.25, 0, 'Bent Road'],
      [3.5, 12.25, 0, 'Bent Road'],
    ]);
    expect(candidates[0]?.partIndex).toBe(0);
  });

  it('keeps disconnected parts separate and skips zero-length or invalid samples', () => {
    const roads = packageOf(
      feature(4, 'Multipart', [
        [
          [0, 0],
          [0, 0],
          [4, 0],
        ],
        [
          [10, 2],
          [10, 2],
          [10, 6],
        ],
        [
          [1, 1],
          [1, 1],
        ],
        [
          [Number.NaN, 0],
          [2, 0],
        ],
      ]),
      feature(5, 'No terrain', [
        [
          [3, 3],
          [5, 3],
        ],
      ]),
    );
    const candidates = createRoadLabelCandidates(roads, (x) =>
      x === 2 ? null : x === 10 ? 5 : null,
    );
    expect(candidates).toHaveLength(1);
    expect(candidates[0]).toMatchObject({
      partIndex: 1,
      x: 10,
      y: 5.25,
      z: 4,
    });
  });

  it('trims only outer whitespace and rejects missing, blank and markup-shaped names safely', () => {
    const roads = packageOf(
      feature(10, '   ', [
        [
          [0, 0],
          [1, 0],
        ],
      ]),
      feature(11, undefined, [
        [
          [0, 0],
          [1, 0],
        ],
      ]),
      feature(12, ' <b>Quay</b> ', [
        [
          [0, 0],
          [1, 0],
        ],
      ]),
    );
    expect(
      createRoadLabelCandidates(roads, () => 0).map((item) => item.name),
    ).toEqual(['<b>Quay</b>']);
  });
});

describe('selectRoadLabelPlacements', () => {
  it('chooses the closest exact trimmed name, then road and part identity deterministically', () => {
    const far = projected(candidate('Quay Road', '3', 'way/3'), {
      distanceM: 4,
      screenX: 200,
    });
    const nearTieLater = projected(candidate('Quay Road', '2', 'way/2', 1), {
      distanceM: 2,
      screenX: 100,
    });
    const nearTieFirst = projected(candidate('Quay Road', '1', 'way/1', 0), {
      distanceM: 2,
      screenX: 300,
    });
    const candidates = [far, nearTieLater, nearTieFirst];
    const result: ProjectedRoadLabel[] = [];
    const seen = new Set<string>();
    selectRoadLabelPlacements(candidates, [], 500, 300, result, seen);
    expect(result).toEqual([nearTieFirst]);
    expect(candidates[0]).toBe(nearTieFirst);
  });

  it('culls behind-camera, off-viewport and beyond-500m anchors', () => {
    const candidates = [
      projected(candidate('Back', '1'), { projected: false }),
      projected(candidate('Far', '2'), { distanceM: 500.01 }),
      projected(candidate('Outside', '3'), { screenX: -2 }),
      projected(candidate('Visible', '4'), { screenX: 100 }),
    ];
    const result: ProjectedRoadLabel[] = [];
    selectRoadLabelPlacements(candidates, [], 300, 200, result, new Set());
    expect(result.map((item) => item.candidate.name)).toEqual(['Visible']);
  });

  it('avoids control panels and overlapping labels while allowing separated labels', () => {
    const candidates = [
      projected(candidate('Control', '1'), { screenX: 50 }),
      projected(candidate('Overlap', '2'), { screenX: 100 }),
      projected(candidate('Collision', '3'), { screenX: 140 }),
      projected(candidate('Clear', '4'), { screenX: 220 }),
    ];
    const obstacles: ScreenRect[] = [
      { left: 0, top: 0, right: 60, bottom: 200 },
    ];
    const result: ProjectedRoadLabel[] = [];
    selectRoadLabelPlacements(
      candidates,
      obstacles,
      300,
      200,
      result,
      new Set(),
    );
    expect(result.map((item) => item.candidate.name)).toEqual([
      'Overlap',
      'Clear',
    ]);
  });

  it('enforces the bounded 20-label pool and reuses caller-owned buffers', () => {
    const candidates = Array.from({ length: 25 }, (_, index) =>
      projected(candidate(`Street ${index}`, String(index)), {
        distanceM: index,
        screenX: 30 + index * 70,
      }),
    );
    const result: ProjectedRoadLabel[] = [];
    const seen = new Set<string>();
    selectRoadLabelPlacements(candidates, [], 1900, 300, result, seen);
    const resultBuffer = result;
    selectRoadLabelPlacements(candidates, [], 1900, 300, result, seen);
    expect(result).toBe(resultBuffer);
    expect(result).toHaveLength(20);
    expect(result[0]?.candidate.name).toBe('Street 0');
    expect(result[19]?.candidate.name).toBe('Street 19');
  });
});
