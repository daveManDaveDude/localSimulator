# Local synthetic asset contract, version 1

TVW-004 defines the browser-side boundary between a local manifest and a binary heightfield. The contract currently accepts **synthetic** worlds only. Manifest validation, byte decoding and loading are independent of Three.js; TVW-005 consumes the validated result to create the default terrain viewer. The analytic M0 scene remains available at `/?world=m0`.

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

The loader checks manifest HTTP status and JSON parsing, validates the complete manifest before requesting binary data, checks binary HTTP status, verifies its SHA-256 with Web Crypto, then decodes the bytes. Failures identify the stage and asset involved. Browser fetch is the default; tests inject a fetch function. The default heightfield viewer loads and renders the local synthetic package; `/?world=m0` bypasses the loader and opens the retained analytic M0 demo.

## Reproducible fixture

`public/worlds/synthetic-heightfield/` contains a fictional 3 × 3 fixture with 2 m spacing and a 4 × 4 m extent. Its row-major values are `[-2.5, 0, 1.25, 10, 11.5, 12, 20, 21, 22.75]`. The manifest has local zero origins, marks its source and provenance synthetic, and includes the binary checksum. It is retained for decoder and loader tests.

`public/worlds/synthetic-terrain-demo/` is a separate 25-column × 19-row fixture with 2 m spacing and a 48 × 36 m extent. Its deterministic generator combines a gentle planar slope, a Gaussian hill and a narrow ridge. It records generator `scripts/generate-synthetic-heightfield.mjs`, version `1.0.0`, synthetic provenance and the binary SHA-256 `cf57dd9d5551eaad413c5e1ea43c8d2f9acb709c410bb016e8fbf7afd95dcd3b` (1,900 bytes). The formula and all samples are fictional and are not measurements of Torquay. Neither fixture contains geographic coordinates, buildings or roads.

## Terrain-grid and mesh interpretation

The renderer places the first sample at the north-west corner and the final sample at the south-east corner. For a grid with width `W`, depth `D`, and spacing `s`, sample `(row, column)` maps to `x = column × s − W/2`, `y = height[row × columns + column]`, and `z = row × s − D/2`. Thus columns increase east on +X, rows move south on +Z, and row zero is north on −Z. Heights are already world Y values relative to the synthetic local origin elevation; the renderer does not add an origin offset.

Each cell uses a fixed diagonal from NE to SW. For `a=NW`, `b=NE`, `c=SW`, and `d=SE`, indices are `(a,c,b)` and `(b,c,d)`, which wind upward. The sampler interpolates those exact two planes: when cell fractions `u+v ≤ 1`, `h = a + (b−a)u + (c−a)v`; otherwise `h = d + (c−d)(1−u) + (b−d)(1−v)`. Maximum-edge queries use the final cell with fraction 1; non-finite queries and positions outside the finite extent return `null`, with no extrapolation.

Regenerate both files deterministically with:

```powershell
npm run generate:synthetic-heightfield
```

The generator reproducibly writes both fixture packages as little-endian Float32 bytes and derives each manifest checksum from those exact bytes. Its version is recorded in both manifests. Unit tests verify fixture dimensions and hashes, row orientation, mesh normals/winding, and triangle-consistent sampling.
