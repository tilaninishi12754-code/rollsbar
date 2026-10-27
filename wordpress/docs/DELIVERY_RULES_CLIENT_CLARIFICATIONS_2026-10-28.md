# RollsBar — delivery rules client clarifications — 2026-10-28

Status: APPROVED CLIENT/OWNER INPUT

Use the previously supplied client delivery table as source data. It contains 92 normalized textual street/locality/area entries across seven minimum-order thresholds for free delivery: 1200 / 1500 / 2000 / 2500 / 3000 / 3500 / 4000 RUB.

Current owner decision: determine the applicable minimum automatically before checkout completion wherever the supplied rule can be resolved safely. Do not wait for exact polygons to automate unambiguous rules. DaData/FIAS address identity is preferred; polygons are optional fallback only where truly needed.

New client clarifications:
- Мазанка = 4000 RUB.
- Rule «до Центрального рынка»: the boundary is understood from the Rolls Bar location at **Симферополь, Кечкеметская улица, 1** toward/through Central Market. Do not reinterpret it as starting from an arbitrary city point.

Still unresolved / do not guess:
- «от ДКП до Автовокзала» — exact street/house boundary;
- «ул. Кечкеметская до ул. Арабатская» — exact split/range;
- «Беспалова ДО МАРЬИНО / ОТ МАРЬИНО» — exact house/intersection divider.

Implementation policy for the next Delivery Rules batch:
- automatically classify every unambiguous table rule now;
- Мазанка must classify to 4000;
- use the Central Market clarification where it can be mapped deterministically from known address/anchor data without inventing geometry;
- unresolved/unknown addresses must fail closed and request clarification rather than silently receive the wrong threshold;
- do not block implementation of all other rules because three boundary phrases remain unresolved;
- these numeric tiers are minimum order thresholds for free delivery, not invented delivery fees;
- preserve Checkout Final Direct Port, native Woo/Store API, DaData precision safety, COD, cart/session and storefront accepted state;
- production remains forbidden until a later explicit gate.
