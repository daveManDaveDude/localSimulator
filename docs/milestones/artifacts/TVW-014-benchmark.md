# TVW-014 local browser benchmark

- Generated: 2026-10-19T18:13:40.051Z
- Commit: 98aba4a0623e0453f2b151165cfda4c423712f54
- Build output SHA-256: a7f609fee9547d27db766ead2a93838f57ddd621701c64505296107ae9f3de54
- Chromium: 156.0.8078.4
- OS: win32 10.0.26300 (x64)
- WebGL renderer: ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver) (Google Inc. (Google))
- Viewport: 1920 × 1080 CSS px, DPR 1
- Method: 3s warm-up; 3 × 10s visible/focused frame-interval runs per workload. FPS is samples divided by observed elapsed duration. Load times are fresh-context navigation and warm-context reload to requested layers plus a post-load rendered frame.

| Workload                              |   FPS | Fresh load ms | Warm reload ms | Mean frame ms | Median ms | p95 ms | p99 ms | Max ms | Draw calls | Triangles | Geometries | Textures | Max JS heap bytes | Local asset bytes |
| ------------------------------------- | ----: | ------------: | -------------: | ------------: | --------: | -----: | -----: | -----: | ---------: | --------: | ---------: | -------: | ----------------: | ----------------: |
| Synthetic M0                          | 30.40 |           444 |            361 |         32.88 |     33.30 |  33.40 |  33.50 |  50.00 |         16 |      7836 |         16 |        1 |        10,999,308 |                 0 |
| EA terrain only                       |  7.66 |           721 |            629 |        130.53 |    133.30 | 133.40 | 150.00 | 150.00 |          9 |    500012 |          9 |        2 |         9,457,144 |           1011842 |
| EA terrain + OSM buildings            |  5.39 |          1547 |           1422 |        185.26 |    183.30 | 200.00 | 200.10 | 200.10 |         11 |    627303 |         11 |        2 |         9,100,048 |           2669783 |
| EA terrain + OSM roads                |  6.76 |          2625 |           2278 |        147.87 |    150.00 | 150.10 | 150.10 | 166.80 |         13 |    598422 |         13 |        2 |        34,314,724 |          19195352 |
| EA terrain + buildings + roads (fly)  |  4.90 |          3589 |           3103 |        204.13 |    200.00 | 216.70 | 233.40 | 249.90 |         15 |    725713 |         15 |        2 |        76,914,876 |          20853293 |
| EA terrain + buildings + roads (walk) |  5.68 |          3655 |           3030 |        176.06 |    183.30 | 183.40 | 200.10 | 216.70 |         15 |    725713 |         15 |        2 |        65,022,380 |          20853293 |

JavaScript heap maximum: Chromium CDP Performance.getMetrics JSHeapUsedSize sampled approximately once per second; per-run maximum is reported when supported.. The script samples Chromium `JSHeapUsedSize`; it does not represent total process or GPU memory. Renderer geometry/texture counters are active object counts, not bytes. Frame cadence is not GPU execution time. No performance threshold is applied.

Raw frame intervals, per-run focus/visibility state, workload poses, package identities and byte inventories are in the companion JSON file.
