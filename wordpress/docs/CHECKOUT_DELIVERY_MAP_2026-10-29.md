# Checkout delivery map and geographic advisory — 2026-10-29

Status: IMPLEMENTED LOCALLY; staging acceptance pending. Production forbidden.

The owner explicitly requested using the prepared geographic draft now without waiting for client review, restoring the map next to the checkout address. This supersedes the earlier map deferral for staging. It does not turn inferred boundaries into client-confirmed commercial rules.

One existing Woo Checkout Block / Store API / session / COD path. Callback eligibility stays complete phone plus explicit checked privacy consent. No name/address/minimum/outside-zone gate, delivery fee, account, alternate submission endpoint or order storage introduced.

The staging-only address resolver uses verified exact FIAS identities first. A scoped verified house outside the exact table can use the geographic fallback only with DaData qc_geo=0 and valid coordinates. Existing ambiguous Kechkemetskaya/Bespalova sections and conflicting exact identities retain unresolved status. Geographic locality footprints precede the city background; conflicting geographic tiers resolve to no minimum. Low-precision, edited, missing-proof/house and out-of-scope addresses never acquire a fabricated geographic threshold. All seven levels are free-delivery minimums. Geographic results are explicitly provisional and say a manager will confirm.

Map: same-origin isolated display iframe immediately after the native address form, hidden in pickup. It embeds the locally vendored Leaflet license, public vector-road fallback and the same geographic polygons used server-side. OSM tiles provide optional network cartography on top of the local vector fallback. Exact selected addresses receive a marker through origin/source-checked postMessage, without address strings or customer contacts in URLs. Editing clears the marker and signed proof. Map interactions never write Woo state or introduce another cart. Wheel zoom is off; mobile map dragging is off to preserve form scrolling. Existing modal chrome and immutable reference gates remain.

Source: `delivery-draft-2026-10-29/`, all 92 workbook source cells retained, Mazanka 4000. `qa/delivery-draft/build_checkout_map.py` compiles 37 geographic features into two new plugin files. No original review dataset or workbook edits.

Local proof: original identity/signed-proof PHP fixtures PASS; independently generated GEOS point fixtures cover two points at each of seven tiers, all lower precision cases, missing house, outside/staging guard, edge and precedence cases PASS. Actual native Woo offline five-width gate 1440/701/700/390/320 PASS, including phone-only callback, consent highlight/clear, map placement/pickup and native pre-submit payload without HTTP order submission.

Release scope: existing twelve-file cumulative delivery scope since accepted controls baseline, two of which are new geography/map assets. Before-image guard uses verified application `a4d5e5a68c59bb7904c36749b2dfadf828c67a22`. Fresh verified staging backup and explicit apply/inspect/finalize release workflow. Map five-width evidence and screenshots are required for finalization alongside unchanged modal-reference, native provider and storefront gates.
