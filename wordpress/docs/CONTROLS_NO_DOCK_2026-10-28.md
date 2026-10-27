# Floating controls without full-width shelf — 2026-10-28

Status: STAGING PASS. Application/marker `921698e085263f23493e8f757aa0e7c1b561946c`, receipt `browser_verified`.

User requested removal of the full-width white bottom band on desktop/mobile while retaining back-to-top, cart and phone. Hide only `.rollsbar-controls-dock`; keep existing individual button surfaces, positions, JS, cart state and last-row scroll clearance. Application delta: only theme `assets/css/app.css`.

Focused Playwright at 320/390/701/900/1440, empty/populated cart: no shelf, nine-point control hit tests, first cart/back-top activation, phone visibility, no overflow and isolated cart cleanup PASS. Desktop/mobile screenshots inspected. Existing Interaction Stability baseline remains unchanged; its historical whole-band assertion assumes the old visual shelf and is not relabelled as PASS under this new UI contract. Existing JS/race/cart behavior is untouched; focused release inherits the accepted full application 529cbf3 and tests the CSS delta directly.

Release reuses staging-only transport, fresh verified backup, exact one-file scope, all other app hash guards, native catalog/media/business checks and exact browser proof. Checkout application bytes remain unchanged. Production access/mutation: no.

Final evidence: [run 40588306513](https://github.com/tilaninishi12754-code/rollsbar/actions/runs/40588306513), fresh verified backup `20261027T213818Z`, all five live widths PASS, `UX_RELEASE_PASS`. Artifact `12773370211`, independently verified SHA256 `1eedcde9c4e319c266766834758f0ebca6ce8adf05325fdbdc55a79aba31c204`. Actual desktop 1440 and mobile 390 populated screenshots inspected: no full-width band, existing cart/back-to-top/phone visible. Native checkout, catalog/media and all other application hashes preserved. No orders or production access.
