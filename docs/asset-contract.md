# Local synthetic asset contract, version 1

TVW-004 defines the browser-side boundary between a local manifest and a binary heightfield. The contract currently accepts **synthetic** worlds only. It is deliberately independent of Three.js and is not connected to the M0 viewer.

## Manifest fields

`formatVersion` is the integer `1`. `id` and `name` are non-empty strings. `worldType` must be `synthetic`, `sourceCrs` must be `LOCAL_SYNTHETIC`, and `axisConvention` must be `+X east, +Y up, -Z north`. Other world types and CRS labels, including EPSG codes, are rejected until a later issue defines real-data handling.

`origin` has finite `eastingM`, `northingM`, and `elevationM` numbers. Synthetic fixtures use fictional zero values; these are local placeholders, not projected coordinates. `extentM` has positive finite `width` and `depth` values in metres.

`heightfield` contains:

- A safe package-relative `path` to the binary asset.
- Integer `columns` and `rows`, each at least 2, and positive finite `spacingM`.
- `rowOrder: "north-to-south"`, `byteOrder: "little-endian"`, and `encoding: "float32"`.
- `valueMeaning: "world Y in metres relative to origin elevation"`.
- A 64-character hexadecimal `sha256` of the raw binary bytes.

The horizontal dimensions must satisfy `(columns - 1) × spacingM = width` and `(rows - 1) × spacingM = depth`. Computed extents must remain finite before comparison. Comparisons use a relative tolerance of `1e-9 × max(1, |declared extent|, |computed extent|)` to absorb floating-point representation error. The product `columns × rows` must be safe integer arithmetic and cannot exceed **16,000,000 samples** (64 MB of Float32 data) before the decoder allocates its output.

`provenance` requires `kind: "synthetic"`, a non-empty generator name and version, and a note. `buildings` and `roads` may be omitted; if present, they are validated as safe local relative paths only. TVW-004 does not define those payloads or fetch them.

## Paths, decoding, and loading

Asset paths consist of non-empty ASCII letter/digit/dot/underscore/hyphen segments separated by `/`. Absolute paths, schemes, backslashes, percent escapes, query/hash characters, and `.` or `..` path segments are rejected. The loader also confirms that a resolved heightfield URL remains in the manifest directory and origin.

The decoder requires exactly `rows × columns × 4` bytes. It reads a little-endian Float32 at each row-major offset into an owned `Float32Array`. Row zero is the northern edge; subsequent rows move south. Non-finite values fail with sample index, row, and column. Finite negative and zero values are valid. The decoder does not apply origins, interpolate, sample, or build geometry.

The loader checks manifest HTTP status and JSON parsing, validates the complete manifest before requesting binary data, checks binary HTTP status, verifies its SHA-256 with Web Crypto, then decodes the bytes. Failures identify the stage and asset involved. Browser fetch is the default; tests inject a fetch function. The loader is not called from the viewer.

## Reproducible fixture

`public/worlds/synthetic-heightfield/` contains a fictional 3 × 3 fixture with 2 m spacing and a 4 × 4 m extent. Its row-major values are `[-2.5, 0, 1.25, 10, 11.5, 12, 20, 21, 22.75]`. The manifest has local zero origins, marks its source and provenance synthetic, and includes the binary checksum. There are no coordinates, buildings, roads, or Torquay measurements in the fixture.

Regenerate both files deterministically with:

```powershell
npm run generate:synthetic-heightfield
```

The generator writes little-endian Float32 bytes and derives the manifest checksum from those exact bytes. Its version is recorded in the manifest.
