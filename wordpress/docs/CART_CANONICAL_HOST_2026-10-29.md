# Cart canonical staging host — 2026-10-29

Status: VERIFY. Production access/mutation: no.

Reproduced the exact screenshot flow: `https://staging.rollsbar.ru./` is a distinct browser origin from configured `https://staging.rollsbar.ru`. Native relative cart AJAX successfully adds there; the absolute native checkout link switches to canonical origin, whose Woo session is empty, so checkout redirects to `/cart/`. Canonical-host control keeps the populated native checkout. No speculative cache/session-race explanation is needed.

Fix: at WordPress init priority-100, before Woo customer/session initialization, redirect GET/HEAD from exactly the configured staging hostname plus one trailing dot to configured home origin, preserving path/query. Target host comes exclusively from trusted home configuration, unrelated hosts and mutation methods are unchanged, production is explicitly excluded. No cookie copying, technical session migration, cart reconstruction, second state or order endpoint. Existing dotted-origin carts are not migrated; new visits normalize before customers add products.

Local pure fixture verifies path/query, GET/HEAD, no mutation replay, no unrelated-host/open redirect, canonical no-loop and production exclusion. Existing checkout-loading fixture remains PASS. New real browser gate covers dotted entry before first add, four distinct products in drawer and native checkout, then dotted direct-checkout entry retaining the canonical session, at1440/390. Orders never submitted; only isolated test carts cleaned. Gate evidence is uploaded separately without changing the existing screenshot manifest/baselines/tolerances. Staging backup/deploy/native/map/storefront/vision/finalization pending.
