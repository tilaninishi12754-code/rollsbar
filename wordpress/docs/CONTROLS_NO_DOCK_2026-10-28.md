# Floating controls without full-width shelf — 2026-10-28

Status: local PASS, staging pending.

User requested removal of the full-width white bottom band on desktop/mobile while retaining back-to-top, cart and phone. Hide only `.rollsbar-controls-dock`; keep existing individual button surfaces, positions, JS, cart state and last-row scroll clearance. Application delta: only theme `assets/css/app.css`.

Focused Playwright at 320/390/701/900/1440, empty/populated cart: no shelf, nine-point control hit tests, first cart/back-top activation, phone visibility, no overflow and isolated cart cleanup PASS. Desktop/mobile screenshots inspected. Existing Interaction Stability baseline remains unchanged; its historical whole-band assertion assumes the old visual shelf and is not relabelled as PASS under this new UI contract. Existing JS/race/cart behavior is untouched; focused release inherits the accepted full application 529cbf3 and tests the CSS delta directly.

Release reuses staging-only transport, fresh verified backup, exact one-file scope, all other app hash guards, native catalog/media/business checks and exact browser proof. Checkout application bytes remain unchanged. Production access/mutation: no.
