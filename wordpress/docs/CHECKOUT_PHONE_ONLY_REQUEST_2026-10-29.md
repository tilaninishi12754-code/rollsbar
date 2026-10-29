# Phone-only callback request — owner override 2026-10-29

Status: local native PASS; staging pending. This later explicit owner instruction supersedes required-name/address/minimum assumptions in the older checkout specs for request submission.

Goal: do not lose a contact because delivery rules cannot classify an address or goods are below the minimum. In the existing non-empty-cart native Woo checkout, a complete customer phone and explicit consent are required. Name/address/details/comment are optional. The owner clarified that the privacy checkbox remains required, with error copy at CTA plus a red marker, focus and scroll at the unchecked consent block. Never precheck or fabricate consent. Preserve selected native receiving mode, internal guest email/country compatibility, COD, one cart/session and original Store API path.

Address suggestions and seven deterministic minimums remain informational. They do not authorize or refuse callback submission. The phone contact is saved in the original Woo order contract; manager confirms fulfillment conditions by phone. No separate lead endpoint, cart state, alternate submit path, delivery charge, boundary or map is introduced. Existing country/email/rate/internal safety requirements are automatically satisfied by the native architecture; native malformed phone rejection remains.

Implemented narrow changes: native field registry name optional and consent required; commercial address-proof/minimum pre-order refusal removed for the real delivery rate; no frontend delivery validation error; address aria-required false; CTA explanation asks for phone and promises manager callback. Unchanged classifier/proof still powers advisory information; forged rate protection retained.

Local native five-width gate PASS: actual POST assembly with full phone and absent name/address plus explicit consent; empty phone/prefix-only rejection; below-minimum native assembly; full original mode/cart/totals/COD/session contracts retained. Actual order HTTP is intercepted; no worker order/account/mail creation. Installed-Woo schema/field fixtures, live five-width/address/adversarial/storefront/visual checks pending. QA expectations intentionally updated to the newly authorized business contract; frozen visual baselines unchanged.

Production forbidden. Existing batch backup/deploy/finalization guards retained. Final evidence will be recorded after staging acceptance.
