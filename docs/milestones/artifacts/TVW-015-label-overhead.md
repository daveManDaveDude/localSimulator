# TVW-015 labels-off/on browser observation

The production browser E2E sampled the same camera pose and viewport with the optional street-name overlay off and on. Each condition used a 2 s warm-up followed by a 3 s `requestAnimationFrame` interval sample.

| Field                         | Recorded value                                            |
| ----------------------------- | --------------------------------------------------------- |
| Route                         | `/?world=torquay-poc-001&roads=1`                         |
| Browser                       | Chromium / Chrome 156.0.8078.4                            |
| WebGL renderer                | ANGLE, Vulkan 1.3, SwiftShader (software renderer)        |
| Viewport                      | 1280 × 800 CSS pixels; DPR 1.5                            |
| Canvas                        | 1280 × 800 CSS and drawing-buffer pixels                  |
| Camera                        | `X 0.0 · Y 170.6 · Z 360.0 m`, bearing 0.7°, pitch −25.8° |
| Warm-up / sampling            | 2,000 ms / 3,000 ms per condition                         |
| Median interval, labels off   | 116.7 ms (8.57 FPS), 26 intervals                         |
| Median interval, labels on    | 116.7 ms (8.57 FPS), 26 intervals                         |
| Visible label nodes, off / on | 0 / 3                                                     |
| Focus / visibility            | Document remained focused and visible during both samples |

This is a software-rendered observation for this run. It has no performance threshold and should not be interpreted as hardware renderer performance. Raw intervals and full browser metadata are in [TVW-015-label-overhead.json](TVW-015-label-overhead.json).
