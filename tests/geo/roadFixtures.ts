import { createRealManifest } from './fixtures';
import {
  MAX_ROAD_MANIFEST_BYTES,
  MAX_ROAD_QA_BYTES,
  MAX_ROADS_BYTES,
  ROAD_BNG_TO_WGS84_DEFINITION,
  ROAD_FLOAT32_SLIVER_POLICY,
  ROAD_ESTIMATED_WIDTHS_M,
  type RoadDisplayGroup,
} from '../../src/geo/roadSchema';

type TestRecord = Record<string, unknown>;

function operationMetadata(definition: string, direction: string) {
  return {
    name: 'EPSG:1314 + EPSG:19916',
    description: `Pinned ${direction} operation`,
    definition,
    reported_accuracy_m: 2,
    accuracy_m: 2,
    grid_status: 'selected EPSG:1314 + EPSG:19916 operation uses no grid files',
    uses_grids: false,
    grids: [],
    best_available: false,
    preferred_missing_operations: [
      {
        name: 'Preferred OSTN15 operation',
        reported_accuracy_m: 1,
        grids: [
          {
            short_name: 'uk_os_OSTN15_NTv2_OSGBtoETRS.tif',
            full_name: '',
            available: false,
            url: 'https://cdn.proj.org/uk_os_OSTN15_NTv2_OSGBtoETRS.tif',
          },
        ],
      },
    ],
  };
}

function buildFeature() {
  return {
    id: 'way/1',
    source: {
      dataset: 'OpenStreetMap',
      objectType: 'way',
      osmId: 1,
      version: 1,
      timestamp: '2026-10-16T00:00:00Z',
      nodeIds: [11, 12],
    },
    highway: 'residential',
    displayGroup: 'vehicular' as RoadDisplayGroup,
    estimatedWidthM: 6,
    widthMethod: 'configured_visual_estimate',
    widthEvidence: {
      rawWidth: null,
      rawLanes: null,
      usedRawTags: false,
      note: 'Width is a configured visual estimate.',
    },
    groundAssumption: 'ground_assumed_from_absent_or_explicit_no_vertical_tags',
    sourceTags: { highway: 'residential', name: 'Fictional Fixture Street' },
    centerlinePartsXZ: [
      [
        [-2, -1],
        [2, -1],
      ],
    ],
    partIds: ['way/1/part/000'],
    clippedToAoi: true,
    duplicateWayIds: [],
    ribbonAreaM2: 24,
    ribbonPartIds: ['way/1/ribbon/000'],
  };
}

function buildBatch() {
  return {
    verticesXZ: [
      [-2, -2],
      [-2, 0],
      [0, -2],
    ],
    indices: [[0, 1, 2]],
    terrainTriangles: [[249, 249, 0]],
  };
}

function buildCounts() {
  return {
    highway_ways_seen: 1,
    included_ground_ways_in_buffer: 1,
    outside_acquisition_buffer: 0,
    excluded_classes: 0,
    excluded_area_surfaces: 0,
    excluded_ground_assumption: 0,
    invalid_missing_locations: 0,
    invalid_too_few_vertices: 0,
    invalid_transform_or_geometry: 0,
    duplicate_source_ways: 0,
    clipped_empty_or_non_line: 0,
    clipped_ways_with_parts: 1,
    unique_exported_ways: 1,
    duplicate_contributor_ids: 0,
    incomplete_highway_way_ids_recorded: 0,
    uniqueExportedWays: 1,
    uniquePartIds: 1,
    uniqueRibbonPartIds: 1,
    float32CollapsedSliverTriangleCount: 0,
    surfaceBatchCount: 1,
    renderVertexCount: 3,
    renderTriangleCount: 1,
  };
}

function buildLandmarks() {
  return ['ne-second-avenue', 'nw-baron-lindfield', 'sw-mount-stuart'].map(
    (id, index) => ({
      id,
      label: `Fixture context ${index + 1}`,
      buildingWayId: 208552436 + index,
      pointRole:
        'existing building representative point, not an inferred road junction',
      buildingRepresentativeWgs84: [-3.536013, 50.477853],
      buildingRepresentativeLocalXZ: [index, index],
      targetRoadNames: ['Fixture Street'],
      targetRoadNamePresent: true,
      nearestRoad: {
        wayId: 1,
        name: 'Fictional Fixture Street',
        highway: 'residential',
        nodeIds: [11, 12],
        nearestPointLocalXZ: [index, index],
        distanceFromBuildingRepresentativeM: 5,
      },
      observation: 'fictional unit-test location only',
      limitations: 'fixture only',
    }),
  );
}

export async function createRoadBundle() {
  const terrain = createRealManifest();
  const source = {
    publisher: 'OpenStreetMap contributors; extract prepared by Geofabrik GmbH',
    product: 'OpenStreetMap regional extract — Devon',
    downloadPageUrl:
      'https://download.geofabrik.de/europe/united-kingdom/england/devon.html',
    fileUrl:
      'https://download.geofabrik.de/europe/united-kingdom/england/devon-261016.osm.pbf',
    checksumUrl:
      'https://download.geofabrik.de/europe/united-kingdom/england/devon-261016.osm.pbf.md5',
    acquisitionDate: '2026-10-17',
    acquiredAtUtc: '2026-10-17T16:43:51Z',
    filename: 'devon-261016.osm.pbf',
    sizeBytes: 58_254_938,
    sha256: '52942b39636e1cb002e5d78a004668996cb469ee9c9e9b9b93049c66b9ac2cd5',
    publisherMd5: 'c9c2018b331d8affd6b7be6464444bc5',
    extractTimestamp: '2026-10-16T20:21:21Z',
    replicationSequence: '4932',
    generator: 'osmium/1.16.0',
    boundsWgs84LonLat: [-4.752335, 50.11104, -2.881604, 51.30895],
    licence: 'Open Database Licence 1.0 (ODbL)',
    licenceUrl: 'https://www.openstreetmap.org/copyright',
    attribution:
      'Data © OpenStreetMap contributors; extract provided by Geofabrik GmbH.',
    attributionRequirement:
      '© OpenStreetMap contributors, with a link to the ODbL licence; credit Geofabrik as the extract provider.',
    sourceStorage: 'ignored fixture source',
  };
  const counts = buildCounts();
  const forwardDefinition = terrain.provenance.coordinateOperation.definition;
  const coordinateOperation = {
    axisOrder:
      'longitude-latitude for geographic input; easting-northing for BNG',
    wgs84ToBng: operationMetadata(forwardDefinition, 'WGS84 to BNG'),
    bngToWgs84: operationMetadata(ROAD_BNG_TO_WGS84_DEFINITION, 'BNG to WGS84'),
  };
  const terrainIdentity = {
    worldId: terrain.id,
    origin: terrain.origin,
    heightfieldPath: terrain.heightfield.path,
    heightfieldSha256: terrain.heightfield.sha256,
    heightfieldByteLength: terrain.heightfield.byteLength,
    heightfieldDimensions: [
      terrain.heightfield.columns,
      terrain.heightfield.rows,
    ],
    verticalReference: terrain.provenance.verticalReference,
    manifestSha256: 'a'.repeat(64),
    extentM: terrain.extentM,
    columns: terrain.heightfield.columns,
    rows: terrain.heightfield.rows,
    spacingM: terrain.heightfield.spacingM,
    axisConvention: terrain.axisConvention,
  };
  const policyWidths = { ...ROAD_ESTIMATED_WIDTHS_M };
  const policies = {
    version: 1,
    acquisitionBufferM: 50,
    coordinateQuantizationM: 0.001,
    minimumRibbonAreaM2: 0.01,
    fullWidthsM: policyWidths,
    pathClasses: [
      'bridleway',
      'cycleway',
      'footway',
      'path',
      'pedestrian',
      'track',
    ],
    excludedClasses: [
      'abandoned',
      'bus_guideway',
      'construction',
      'disused',
      'escape',
      'proposed',
      'raceway',
      'steps',
    ],
    groundAssumption: {
      bridge: "absent or exactly 'no' accepted; otherwise exclude whole way",
      tunnel: "absent or exactly 'no' accepted; otherwise exclude whole way",
      covered: "absent or exactly 'no' accepted; otherwise exclude whole way",
      layer: 'absent or strict integer zero accepted; all others excluded',
      tagAbsence: 'visual ground assumption only, not verified elevation',
    },
    areaSurfacePolicy: 'exclude area=yes and any area:highway tag',
    buffer: {
      widthMeaning: 'estimated full display width; radius is width/2',
      capStyle: 'flat',
      joinStyle: 'bevel',
      mitreLimit: 2,
      quantization:
        'centerline coordinates quantized to configured millimetres before buffering',
    },
    clip: 'buffered polygons clipped to exact AOI; centerline parts are also clipped for inspection',
    displayPriority: ['vehicular', 'cycleway', 'path'],
    triangulation:
      'fixed TerrainGrid triangles (NW,SW,NE) and (NE,SW,SE); constrained Delaunay per clipped triangle',
    surfaceOffsetM: 0.05,
    float32SliverPolicy: ROAD_FLOAT32_SLIVER_POLICY,
  };
  const roadFeature = buildFeature();
  const batch = buildBatch();
  const emptyBatch = { verticesXZ: [], indices: [], terrainTriangles: [] };
  const payload = {
    formatVersion: 1,
    worldId: terrain.id,
    features: [roadFeature],
    surfaceBatches: {
      vehicular: batch,
      cycleway: emptyBatch,
      path: emptyBatch,
    },
  };
  const qa = {
    formatVersion: 1,
    worldId: terrain.id,
    status: 'pass',
    selectionStatus: 'selected_pending_coverage',
    coverageStatus: 'not_checked',
    source,
    counts,
    displayBatches: {
      vehicular: {
        uniqueWayCount: 1,
        clippedCenterlinePartCount: 1,
        vertexCount: 3,
        triangleCount: 1,
        surfaceAreaM2: 2,
        bufferedAreaBeforePriorityM2: 2,
      },
      cycleway: {
        uniqueWayCount: 0,
        clippedCenterlinePartCount: 0,
        vertexCount: 0,
        triangleCount: 0,
        surfaceAreaM2: 0,
        bufferedAreaBeforePriorityM2: 0,
      },
      path: {
        uniqueWayCount: 0,
        clippedCenterlinePartCount: 0,
        vertexCount: 0,
        triangleCount: 0,
        surfaceAreaM2: 0,
        bufferedAreaBeforePriorityM2: 0,
      },
    },
    areas: {
      byDisplayGroupM2: { vehicular: 2, cycleway: 0, path: 0 },
      totalDisjointSurfaceM2: 2,
      overlayPriority: ['vehicular', 'cycleway', 'path'],
      areaDifferenceWithinDeclaredTolerance: true,
    },
    meshNumerics: {
      float32CollapsedSliverTriangleCount: 0,
      float32CollapsedSliverAreaM2: 0,
      maximumOmittedAreaM2: 1e-6,
      policy: ROAD_FLOAT32_SLIVER_POLICY,
    },
    coordinateOperation,
    surfacePolicy: {
      fullWidthsM: policyWidths,
      surfaceOffsetM: 0.05,
      float32SliverPolicy: ROAD_FLOAT32_SLIVER_POLICY,
    },
    landmarkContexts: buildLandmarks(),
    interpretation: 'Mapped counts do not establish completeness.',
  };
  const roadsBytes = new TextEncoder().encode(JSON.stringify(payload)).buffer;
  const qaBytes = new TextEncoder().encode(JSON.stringify(qa)).buffer;
  const [roadsSha, qaSha] = await Promise.all([
    sha256(roadsBytes),
    sha256(qaBytes),
  ]);
  const manifest = {
    formatVersion: 1,
    worldId: terrain.id,
    name: 'Fixture local road ribbons',
    packageType: 'osm-road-ribbons',
    sourceCrs: 'EPSG:27700',
    axisConvention: '+X east, +Y up, -Z north',
    units: 'metres',
    aoi: {
      crs: 'EPSG:27700',
      boundsM: [...terrain.aoi.boundsM],
      centerBngM: [...terrain.aoi.centerBngM],
      widthM: terrain.aoi.widthM,
      heightM: terrain.aoi.heightM,
      boundaryWgs84: {
        crs: 'EPSG:4326',
        coordinateOrder: 'longitude-latitude',
        closedRing: true,
        ring: terrain.aoi.boundaryWgs84.ring.map((coordinate) => [
          ...coordinate,
        ]),
      },
      selectionStatus: 'selected_pending_coverage',
      coverageStatus: 'not_checked',
    },
    terrainIdentity,
    coordinateOperation,
    source,
    policies,
    generator: {
      name: 'torquay_pipeline.road_export',
      version: '0.1.0',
      shapelyVersion: '2.2.0',
      geosVersion: '3.14.1',
    },
    limits: {
      maxManifestBytes: MAX_ROAD_MANIFEST_BYTES,
      maxQaBytes: MAX_ROAD_QA_BYTES,
      maxPayloadBytes: MAX_ROADS_BYTES,
      maxWays: 100_000,
      maxVertices: 1_000_000,
      maxTriangles: 1_000_000,
    },
    counts,
    assets: {
      roads: {
        path: 'roads.json',
        byteLength: roadsBytes.byteLength,
        sha256: roadsSha,
      },
      qa: { path: 'qa.json', byteLength: qaBytes.byteLength, sha256: qaSha },
    },
    coverage: {
      selectionStatus: 'selected_pending_coverage',
      coverageStatus: 'not_checked',
      note: 'Mapped counts do not establish completeness.',
    },
    attribution: {
      text: '© OpenStreetMap contributors; extract provided by Geofabrik GmbH.',
      licence: source.licence,
      licenceUrl: source.licenceUrl,
      geofabrikCredit: 'Extract provided by Geofabrik GmbH.',
      environmentAgency: terrain.provenance.attribution,
      environmentAgencySourceUrl: terrain.provenance.catalogueUrl,
    },
  };
  return {
    terrain,
    terrainManifestSha256: terrainIdentity.manifestSha256,
    manifest,
    payload,
    qa,
    roadsBytes,
    qaBytes,
  };
}

async function sha256(bytes: ArrayBuffer): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}

export type RoadBundle = Awaited<ReturnType<typeof createRoadBundle>>;
export type RoadBundleRecord = RoadBundle & { manifest: TestRecord };
