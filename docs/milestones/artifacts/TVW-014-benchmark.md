# TVW-014 local browser benchmark

- Generated: 2026-10-19T18:44:59.891Z
- Commit: 2e2120b5528c16d6a28e76a55f5281ff2f6206c6
- Build output SHA-256: a7f609fee9547d27db766ead2a93838f57ddd621701c64505296107ae9f3de54
- Chromium: 156.0.8078.4
- OS: win32 10.0.26300 (x64)
- WebGL renderer: ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver) (Google Inc. (Google))
- Viewport: 1920 × 1080 CSS px, DPR 1
- Method: 3s warm-up; 3 × 10s visible/focused frame-interval runs per workload. FPS is samples divided by observed elapsed duration. Load times are fresh-context navigation and warm-context reload to requested layers plus a post-load rendered frame.

| Workload                              |   FPS | Fresh load ms | Warm reload ms | Mean frame ms | Median ms | p95 ms | p99 ms | Max ms | Draw calls | Triangles | Geometries | Textures | Max JS heap bytes | Local asset bytes |
| ------------------------------------- | ----: | ------------: | -------------: | ------------: | --------: | -----: | -----: | -----: | ---------: | --------: | ---------: | -------: | ----------------: | ----------------: |
| Synthetic M0                          | 30.39 |           433 |            358 |         32.91 |     33.30 |  33.40 |  50.00 |  50.00 |         16 |      7836 |         16 |        1 |        10,910,584 |                 0 |
| EA terrain only                       |  7.69 |           683 |            617 |        130.04 |    133.30 | 133.40 | 133.50 | 166.60 |          9 |    500012 |          9 |        2 |         7,438,348 |           1011842 |
| EA terrain + OSM buildings            |  5.42 |          1547 |           1414 |        184.54 |    183.30 | 200.00 | 200.10 | 200.10 |         11 |    627303 |         11 |        2 |         9,726,792 |           2669783 |
| EA terrain + OSM roads                |  6.79 |          2733 |           2410 |        147.32 |    150.00 | 150.10 | 150.10 | 183.30 |         13 |    598422 |         13 |        2 |        89,601,212 |          19195352 |
| EA terrain + buildings + roads (fly)  |  4.95 |          3558 |           3040 |        202.10 |    200.00 | 216.70 | 216.70 | 216.80 |         15 |    725713 |         15 |        2 |        64,266,352 |          20853293 |
| EA terrain + buildings + roads (walk) |  5.67 |          3263 |           3241 |        176.25 |    183.30 | 183.40 | 200.00 | 216.70 |         15 |    725713 |         15 |        2 |        77,494,060 |          20853293 |

JavaScript heap maximum: Chromium CDP Performance.getMetrics JSHeapUsedSize sampled approximately once per second; per-run maximum is reported when supported.. The script samples Chromium `JSHeapUsedSize`; it does not represent total process or GPU memory. Renderer geometry/texture counters are active object counts, not bytes. Frame cadence is not GPU execution time. No performance threshold is applied.

Raw frame intervals, per-run focus/visibility state, workload poses, package identities and byte inventories are in the companion JSON file.
