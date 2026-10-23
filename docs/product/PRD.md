# FOM — Future of Myanmar

Escrow and Cross Banking — Product Requirements Document

Brand decision · 22 October 2026: **FOM** is the app name; **Future of Myanmar** is its full meaning. Preserve the approved visual system and elephant. Existing internal paths and identifiers may retain the historical Handshake name.

Version 2.2 · 22 October 2026 · Accurate simulated MVP and partner-led automated product

## 1. Product decision

Exactly two customer services:

1. **Escrow:** buyer and seller agree on a deal; an approved financial partner holds payment under an agreed arrangement until authorized release or refund, with a human dispute route. Real-money availability is conditional on a partner supporting this model and its required operations.
2. **Cross banking / payment acceptance:** a customer pays a verified merchant through a supported bank or wallet using an approved provider integration. Prefer direct settlement to that merchant under the provider's agreement. Temporary payment requests and permanent shops are acceptance modes, not separate services.

Example: an approved MMQR merchant shares a payment request or shop link. A customer pays using a participating wallet; the payment network processes the merchant payment and our backend records provider-confirmed collection. The provider settles to the merchant's verified account on its agreed schedule. A seller's ordinary personal KPay phone number is not equivalent to an approved MMQR merchant account.

Product architecture decision: operate the customer experience, orders and financial records in partnership with an authorized bank/payment provider; the partner handles customer funds under a documented arrangement. This is a proposed operating model, not an approved partnership or a determination that the platform needs no authorization. Collection APIs do not establish arbitrary personal-wallet transfers, automated settlement, platform aggregation or escrow custody. Those capabilities require separate evidence and approval. “Cross banking” remains an internal working label; use **Accept payments** in customer copy. Initial currency: MMK.

Routine payment processing should be automated. Human staff handle verification exceptions, disputes, reconciliation differences and uncertain outcomes; the product must not depend on staff manually resending every customer payment. Direct merchant acceptance is the first production candidate. Escrow remains simulated or unavailable until its partner and operating requirements are satisfied.

## 2. Scope reset

The latest pre-implementation companion is [Payment blueprint — start here](payment-blueprint/README.md). It specifies provider outputs, exact customer authorization steps, the permanent-shop solution, backend mapping, planned app changes, unsent provider inquiries and presentation/video handoff. Public documentation, Handshake design decisions, requested partner capabilities and MVP simulation are labeled separately.

This is the current PRD. Version 1 is archived in `outputs/product-v2/archive/Escrow_Product_PRD_v1.md`; the previous specification is preserved in `outputs/product-v2/archive/PRD-v2.0-2026-10-21.md`. This revision supersedes its assumed collect-then-wallet-payout model and desktop customer presentation. Existing workstream artifacts and simulator contracts describe delivered work; they do not override these production requirements.

Remove subscriptions, recurring billing, general invoicing, marketplace/catalog/cart features, lending, crypto, currency conversion and unrelated business tools from the active product. AI creation assistance and AI dispute judging are outside this MVP. Admin, receipts, transaction activity and help support the two services; they are not additional customer products.

Preserve the approved minimalist interface and existing escrow journey. Remove unrelated scope without deleting approved design assets or operational records.

## 3. Users and setting

- Buyers and sellers arranging protected transactions through chat or in person.
- Approved occasional sellers and stalls requesting a particular merchant payment; provider eligibility must be established before live acceptance.
- Shop owners wanting one persistent payment URL/QR and a verified provider settlement account.
- Staff handling reports, disputes, payment exceptions and reconciliation.

Prioritize physical-world payment: one person shows a QR on a phone or counter; another opens the payment experience. Chat links work equally well. Physical does not mean offline: verified payment needs connectivity. Recover the server's actual status after interruptions.

The customer product is a mobile app experience, testable in a mobile browser without forced installation: phone-width screens, mobile navigation and focused tasks. Staff use a separate desktop admin panel backed by the same system. Native app-store distribution is a later packaging decision, not required for this scope. Request contact or identity information where required for authorization, recovery or provider onboarding. Persistent owners need durable private access; customers need no platform account merely to open a payment page. Paying still requires authorization in the provider's supported flow.

## 4. Research and positioning

User-confirmed references: Dinger, MyanMyanPay and MMQR. Public documentation checked 22 October 2026. Distinguish documented capabilities from proposed partner arrangements; a public API is not permission to run a multi-seller financial platform.

| Reference | Published capability | Implication |
| --- | --- | --- |
| [Dinger Social Merchant](https://dinger.asia/social/eng) | Shared messaging payment links without a merchant website and transaction management. | Links and multi-method collection already exist. |
| [Dinger production Pay API](https://dinger.asia/production-payAPI/eng) and [production callback](https://dinger.asia/production-merchant-callback/eng) | Merchant `/api/pay` with provider-specific QR, notification and redirect flows; success/failure callbacks. | Collection is documented. No arbitrary-beneficiary payout endpoint was found in the public documentation reviewed. Confirm current production methods, settlement and platform permission with Dinger. |
| [Dinger onboarding](https://dinger.asia/User-guide/eng) and [partnership page](https://www.dinger.asia/partnership/eng) | Merchant/project approval and integration keys; a digital-agency partnership program. | Merchant activation or an agency referral partnership does not establish escrow, sub-merchant aggregation or payout rights. |
| [MyanMyanPay API](https://docs.myanmyanpay.com/api/) | `/payments/handshake`, `/payments/create`, `/payments/get`, `/payments/cancel`; MMQR payloads and signature/nonce-verified webhooks. | Supports order-based collection/status. Cancellation and a `REFUNDED` status do not establish a refund-initiation API; settlement status fields do not establish a payout-initiation API. |
| [MyanMyanPay terms, sections 06 and 08](https://myanmyanpay.com/terms), [FAQ](https://myanmyanpay.com/faqs) | Published terms updated 30 August 2026: 24-hour security hold, manually requested Monday/Thursday settlement; prohibition on intermediary, white-label and nested sub-merchant use. FAQ lists verified KBZ, AYA and CB bank settlement accounts. | Standard merchant terms do not fit platform collection for other sellers or fully automated withdrawals. A separately approved arrangement would be needed; no such arrangement exists in this project. The security hold does not establish buyer-controlled escrow. |
| [KBZPay MMQR](https://www.kbzpay.com/en/products/mmqr), [Wave MMQR merchant service](https://www.wavemoney.com.mm/partner/myanmar-pay-merchant/) | Merchant acceptance from multiple wallets, merchant onboarding and transaction tools. | Direct merchant acceptance is an existing route. Confirm integration APIs and platform onboarding separately; do not assume occasional sellers are universally ineligible. |
| [MyanmarPay QR specification, pages 6–7](https://myanmarpay.gov.mm/frontend/assets/files/MyanmarQRSpecification.pdf) | Merchant-presented static/dynamic QR; the payment operator processes the transaction to a designated merchant account. | MMQR handles interoperable merchant payment routing. Its QR format is not a public transfer API or authority to credit any personal wallet. |
| [Government-published mobile financial services regulations](https://servicetrade.gov.mm/service/regulation-detail/regulations-on-mobile-financial-service) | CBM framework includes provider registration, agents, safeguarding, controls and records. | Myanmar payments counsel and the proposed partner must confirm the applicable current classification, approvals and responsibilities for this exact model. Partnering does not automatically remove platform obligations. |
| [WeTransfer link sharing](https://wetransfer.com/resources/share-files-download-link) | Recipients can open shared download links in a browser without accounts. | Borrow simple browser entry; financial actions still require authorization. |

**Positioning hypothesis:** convenient temporary requests and permanent shop links, mobile payment tracking and clear fees/settlement timing, plus a separately approved protected-deal service. Validate remaining pain after existing MMQR offerings, willingness to pay and whether sellers accept the partner's onboarding and settlement schedule. Instant arbitrary wallet bridging is not the validated value proposition.

### Production partner requirements

Before selecting a live adapter, obtain a written capability and responsibility matrix covering:

- Independent seller/occasional-seller eligibility, merchant identities, KYC/KYB ownership, platform/agent permission and production approval.
- Who receives and holds each payment; direct merchant settlement accounts, supported destinations, schedules, finality, fees, reserves and loss allocation.
- Actual APIs for dynamic collection, authenticated notifications, status queries, automated settlement/payout and original-source refunds; idempotency, limits and unknown-outcome recovery for each.
- For escrow: permitted custody/holding, buyer-authorized release, dispute freeze, refund, partial settlement and enforcement when the provider is unavailable. A technical hold in our database cannot prevent external funds movement by itself.
- Provider statements, reconciliation, incident escalation, availability commitments and credential/security requirements.

No reviewed provider is selected or confirmed to support the full model. Do not work around aggregation restrictions using one ordinary merchant account or assume that separate seller keys permit an otherwise prohibited platform arrangement.

## 5. Shared entry and private access

Create → share link/show QR → recipient opens the correct page → reviews amount and recipient → acts.

- Web URL is canonical; the product QR encodes it. Optional **Enter a code** resolves the same resource.
- Distinguish our website-entry QR from a provider/MMQR payment QR. A URL QR must not be advertised as scannable by every banking app.
- Prefer verified same-device app opening/redirect when supported. For QR-only providers, confirm an image-import or second-device route; never expect someone to scan their own screen.
- Public links/codes permit the appropriate preview/payment entry, never ownership, payout changes, private evidence access, refunds or escrow release.
- Private participant/owner sessions authorize sensitive actions. A public code cannot recover ownership. Offer private cross-device recovery without requiring a native app.
- Public previews expose no full phone, address, evidence or access secrets. Rate-limit code lookups and handle invalid, expired, revoked and completed links.

## 6. Service A: escrow

Production gate: activate only when a partner agreement and tested capabilities cover collection, holding, dispute freeze, authorized release and refund. Otherwise keep the protected-deal journey explicitly simulated or unavailable for real payments. Ordinary MMQR merchant acceptance must not be labeled escrow.

1. Seller describes the item/service, amount, delivery terms, inspection window and verified payout destination.
2. Seller reviews and shares the deal link/QR; code entry is a fallback.
3. Buyer reviews exact terms and fees, joins with private participant authority and accepts. Freeze the accepted agreement version.
4. Buyer pays through a supported collection route. Show **Payment secured** only after authoritative confirmation of the agreed holding arrangement.
5. Seller delivers directly and records delivery. Routine transactions need no extensive evidence checklist.
6. Buyer confirms acceptance and authorizes release, or reports a problem. Show payout recipient and amount before release.
7. Show **Release requested** while pending and **Paid to seller** only after payout confirmation.

Rules:

- An invitation cannot impersonate a participant. Bind the intended buyer securely using a private invitation or intended-buyer confirmation where necessary.
- Define deliverables and acceptance; real categories require suitable policies. Avoid a large category picker in the demo.
- Either party can report a problem while funds are held. A valid dispute blocks release immediately and creates an admin case.
- Default: buyer-authorized release. Deadline release stays off until agreed policy, qualifying receipt evidence, reminders and dispute-race handling are implemented and supported by the partner. A seller claiming delivery cannot start a release timer alone.
- Humans decide contested outcomes against terms/evidence. Support release, refund or documented agreed partial settlement. No AI judging or blanket guarantees.
- Internal release approval and external payout confirmation are separate facts. Sent payouts cannot be assumed reversible.

Deal states: `draft → awaiting_buyer → awaiting_payment → held → delivered → release_pending → completed`. Exceptions: `disputed`, `refund_pending`, `refunded`, `canceled`, `expired`. Store funding/payout state separately.

## 7. Service B: cross banking

Production direction: merchant acceptance using the partner's approved merchant identities and settlement arrangement. Default funds flow is customer → provider/payment network → merchant account. Do not add a second platform-funded wallet transfer unless separately approved, documented and tested. Ordinary personal-to-person wallet transfer/remittance is outside this product.

### Temporary request

An eligible seller completes required merchant verification and links a provider-approved settlement account before accepting live payments. Seller enters the amount; the app uses the approved merchant identity and settlement configuration. Verify account control and resolve the recipient name where supported; a phone number alone is not verification. Show customer total, charges, expected net proceeds, settlement account and timing before creation. Produce one expiring request with URL, QR and optional code. Occasional sellers are subject to the same applicable provider eligibility rules; a temporary link does not bypass onboarding.

Customer opens it, checks recipient and amount, selects an available payment method, reviews final total and authorizes in the supported provider flow. Return to our status page. The recipient sees collection and settlement progress without chasing screenshots.

Each request accepts one successful payment. Concurrent attempts cannot create two fulfillments. Expiry prevents new attempts, but a late confirmed receipt must be reconciled into fulfillment or refund under the accepted policy. Never discard received funds because a link expired.

### Permanent shop

Owner completes merchant onboarding and approved settlement setup once and receives a stable URL/QR. No catalog, cart, inventory or website builder. Every visitor creates a separate provider-linked payment intent from that address. MVP: customer enters amount and reviews before paying. Fixed-amount sales can use temporary requests.

A private activity list shows individual collection, net proceeds and settlement state. Pausing a shop prevents new collections while preserving outstanding transactions. Settlement-account changes require owner verification and applicable provider approval. Existing quotes retain their merchant/account snapshot unless canceled and requoted.

A one-time shop setup fee may supplement transaction commission if validated. Pricing is undecided; no subscriptions or recurring service charges.

### Amounts and fees

Use integer MMK for this product. Simulator default: **recipient-net pricing**; merchant specifies their net amount, payer sees any additional disclosed charge. Live pricing and fee payer require provider permission and verified costs. Do not promise a fixed net amount unless the agreed collection/settlement model can deliver it; otherwise show the sale amount, disclosed deductions and expected net proceeds.

Illustration only: recipient receives 10,000 MMK; payer pays 10,200 MMK; displayed charge is 200 MMK. This must cover applicable provider collection/settlement costs plus platform margin; it is not all profit. It is not an approved tariff. Calculate real provider costs before offering live quotes.

Freeze `recipientNet`, `payerTotal`, provider costs, platform fee, fee version, collection route, provider merchant identity, settlement-account/beneficiary version and expiry. Requote changes before authorization. Use **You pay** for customers and **You receive** for recipients rather than technical incoming/outgoing rail forms.

### Collection and settlement operations

- Offer configured supported routes, not universal wallet claims.
- Confirm the platform/merchant-acquirer agreement and only expose its permitted capabilities. Do not infer permission from API access or route live funds through informal personal accounts.
- In direct merchant acceptance, the provider settles to the merchant. Track settlement separately from collection without inventing a platform payout, platform custody or platform-owned cash. The internal ledger must represent the actual ownership and provider statements.
- If a separately approved model requires platform-funded payouts, track recipient liabilities and available, reserved and pending float, including funding ownership, limits and loss allocation. The local simulator's prefunded payout model does not establish this production arrangement.
- Check route health, merchant eligibility and limits before offering a quote; check liquidity where the actual model requires float. A post-payment settlement failure becomes **Payment received — settlement pending**, with an exception case and next step. Never request a second customer payment.
- Simulation uses per-payment settlement. Live timing follows the agreement. Automated confirmation does not mean automated withdrawal or instant settlement; a manual-only settlement arrangement must not be marketed as a fully automated end-to-end product.
- Query an uncertain provider reference before retrying. Never blindly duplicate payouts. Browser redirects and screenshots do not confirm success.
- Handle unmatched, duplicate, under/overpaid or reversed receipts, invalid destinations and unavailable routes explicitly. Refund to the supported original source where possible; alternate destinations require verification and approval.
- This is merchant/request-based acceptance, not unrestricted remittance or public wallet exchange.

Product states: `created → awaiting_payment → collection_pending → collected → settlement_pending → completed`. Exceptions: `expired`, `payment_failed`, `collection_unknown`, `settlement_unknown`, `settlement_failed`, `review_required`, `refund_pending`, `refunded`. Maintain separate collection and settlement records. A confirmed collection is a paid order, not proof of bank availability. If individual settlement cannot be verified, show the actual pending/batched state rather than manufacturing per-payment confirmation. Existing simulator `payout_*` states are implementation terminology for its simulated second leg, not proof that production requires or supports that leg. Escrow release still tracks an explicit payout instruction and confirmation.

## 8. Operations and staff admin

Prioritize work queues and transaction detail over decorative analytics.

| Area | Required behavior |
| --- | --- |
| Needs attention | Disputes, reports, unmatched receipts, failures, unknown outcomes and overdue cases; filter by type, age, amount and assignee. |
| Transaction detail | Search internal/provider references; see accepted terms/quote, actual collection and settlement/escrow legs, merchant identity, masked account, receipt and chronological events. |
| Escrow cases | Review claims/private evidence, request clarification, freeze release, record decision and authorized release/refund. |
| Cross banking exceptions | Query collection/settlement, resolve matching and arrange approved refunds. Submit payout/refund retries only where the provider supports them and the previous outcome is definitively failed. |
| Shops and routes | Review onboarding, pause new collections, inspect beneficiary versions and route availability; no silent rerouting of funded transactions. |
| Reconciliation | Compare ledger, provider reports and bank/wallet statements; expose shortages and unmatched entries; export differences. |

Every sensitive action shows amount/destination, enforces permission and records actor, reason, time and outcome. Separate support, operations, finance and admin permissions; support cannot release money. Exceptional manual payouts/refunds and beneficiary overrides require second-person approval. Routine provider-approved automatic settlement does not require manual approval of every purchase. Staff address exceptions rather than manually resend every payment; contested escrow decisions retain human review.

Every report has a case ID, owner and status visible to its participant. Response targets remain an operating decision. Refund approval and completion are separate. No editing balances/holds simply to make reconciliation appear correct.

## 9. Shared backend contract

One authoritative backend and persistent datastore. Browser storage may preserve drafts/access context; it cannot be the shared financial record.

Records: `Deal`, `Shop`, `PaymentRequest`, `MerchantAccount`, `Quote`, `CollectionAttempt`, `Settlement`, `SettlementAllocation`, `Payout`, `Refund`, `LedgerEntry`, `ParticipantSession`, `Case`, `AuditEvent`, `ProviderRoute`. Merchant accounts record provider identity, verification/approval status and versioned settlement configuration. Settlement/allocation records support batches and payment-level reconciliation. Payout instructions exist only for an actual supported outgoing leg. Money movements have immutable IDs, external references, currency, amount and idempotency keys. Snapshot accepted terms, fees, merchant identity and beneficiaries. These are production requirements; reconcile schema changes centrally before implementation.

- Double-entry ledger separates clearing, escrow liabilities, merchant payables, reserved payouts, refunds, provider costs and earned revenue where applicable to the actual operating model. Direct provider-to-merchant funds must not be represented as platform cash or custody. Gross collection is not platform revenue.
- Verify authenticated provider callbacks/status queries and match reference, amount, currency and destination. Enforce durable deduplication and transactional transitions.
- Replayed/out-of-order events, repeated clicks and worker retries cannot duplicate money movement. Lock single-use fulfillment and competing dispute/release decisions.
- Backend owns transitions. Admin cannot simply rewrite payment status labels.
- Server-only provider secrets; masked public details, restricted uploads/staff access and minimized sensitive logs. Never collect wallet PINs or OTPs in our forms.
- Adapter declares collection, collection status, settlement reporting, payout initiation/status, refund initiation/status and escrow holding/release/freeze capabilities separately. Missing operations stay disabled. A QR format, callback, cancellation endpoint or status value is not evidence of a missing initiation capability. Each enabled production capability requires approved credentials, current provider documentation and verified finality/recovery behavior.

Starting routes: `/d/:publicToken`, `/r/:publicToken`, `/s/:shopSlug`, `/join`, `/admin`. Private sessions are independent of public identifiers. These specify application routes, not live hosted URLs. The integration chat owns final schema/API decisions after reconciling track outputs.

## 10. Interface and motion

User-requested visual reference: `outputs/escrow-soft-flow/Soft Escrow — Flow Studies.html#held`, inspected together with the supplied buyer screenshot and the later compact seller/buyer implementation in `outputs/escrow-reference-layout/`. Follow `outputs/product-v2/DESIGN_REFERENCE.md`: reuse the theme/status composition and retain later simplifications, including removal of category grids and oversized popups. Older Figma studies are historical, not permission to redesign this direction.

- Preserve Manrope, periwinkle `#afb5ff`, navy `#282a3d`, quiet near-white surfaces, clear large amounts, compact summaries and rounded controls.
- Customer UI is a mobile app experience with phone-width views, bottom navigation and focused tasks, testable in the browser. Desktop admin is separate and shares the same backend; do not reuse a desktop staff/sidebar layout for customer screens. Native installation is not required for testing or shared links.
- One primary next action; short copy; explanations at point of need. Do not create a separate obligatory screen for every field.
- Two main intents: **Protected deal** and **Accept payments**. Temporary/permanent belongs within acceptance.
- Plain statuses distinguish **Waiting for payment**, **Payment received**, **Settlement pending**, **Settled to merchant account**, **Needs attention**. Show wallet-specific sending/paid labels only for a confirmed supported outgoing wallet leg. Reserve **Funds held** for verified escrow custody. Show actual settlement timing separately from order payment success.
- QR/link sharing first, code second. No mandatory download banner or chat-room feature.
- Preserve the approved navy/blue elephant. Give it expressive waves, trunk/ear movement, anticipation and short celebrations. A whole static PNG bobbing is not finished character animation.
- Financial amounts and irreversible-action controls stay stable. Celebrate confirmed outcomes, never a click or unverified redirect. Pending motion cannot imply completion.
- Motion is interruptible, pauses offscreen, respects reduced motion and has a static fallback. No persistent confetti, streak pressure or gambling-style rewards.
- Verify 360px mobile layout, keyboard, contrast, touch targets and readable Burmese font fallback. Human review is needed before calling Burmese localization polished.

## 11. Functional app boundary

**Competition MVP priority:** the provider need not be live or connected. The frontend and backend presentation must nevertheless show a coherent intended product: merchant setup, order review, external authorization, server-confirmed return, private receipt and separate settlement/escrow outcomes. Simplify screens and copy while preserving those necessary steps. The target remains automatic routine processing; lack of a partnership does not make manual per-payment forwarding the proposed solution. Provider negotiation is a production step, not a reason to postpone accurate flow design. Implement the next UI changes only under a subsequent implementation request, following the payment blueprint's output plan.

The current `handshake/app/` is a locally runnable Python/SQLite full-stack simulator with shared persistent state, private participant access, staff authentication, QR/link routing, transactions, cases, receipts and admin actions. Customer mobile testing is at `http://127.0.0.1:8800/mobile.html`; desktop staff testing is at `http://localhost:8800/admin.html` while the local server runs. Local URLs are not publicly reachable. Read its runbook and integration handoff for exact delivered behavior; the reported 37 backend tests validate the local simulator, not provider capabilities. Earlier empty `handshake/dist`/hosting metadata did not establish an app or production readiness.

Without approved credentials/capabilities, use an explicitly labeled **simulation adapter**: backend-driven funding, payout, failures, duplicate events and unknown outcomes. Keep scenario controls outside the customer journey. Report completion as functional simulation, sandbox connection or live payments accurately. Never hide a missing payout API behind fake success.

This PRD update defines the path toward an official automated product; it does not authorize publication, production activation or real transfers. No external provider sandbox or live payment integration is currently connected. Existing simulator tests are not evidence of bank settlement, live escrow or production approval.

### Production readiness gates

1. **Operating model:** establish the business entity and banking relationship appropriate to the confirmed model. Myanmar payments counsel and the proposed partner document the applicable current approvals, agent/platform status, safeguarding, KYC/KYB, AML/CFT, complaints, retention and loss responsibilities. Do not assume an ordinary merchant agreement or agency referral program supplies these rights.
2. **Partner selection:** sign an arrangement covering independent sellers, occasional-seller eligibility, merchant identities, direct settlement, fees, supported accounts and automation. Obtain actual API documentation and credentials for every offered capability. Reject or visibly narrow features that the agreement does not support.
3. **Sandbox integration:** replace simulated capabilities individually; test authenticated callbacks, status recovery, duplicates, out-of-order events, unknown outcomes, refunds and settlement/report reconciliation. Provider sandbox tests remain distinct from local simulation and live tests. MyanMyanPay sandbox QRs require its dashboard simulator rather than real banking apps, per its FAQ.
4. **Production engineering and operations:** use HTTPS, production authentication/recovery and staff MFA, server-side secret management, durable background jobs, a database suitable for the agreed workload, monitoring/alerts, tested backups/restores and disaster recovery. Ingest provider/bank statements, assign reconciliation/case owners and establish support/incident procedures. No default demo staff passwords or exposed scenario controls in production.
5. **Acceptance pilot:** only after separate authorization, run a limited provider-approved merchant pilot with agreed limits, reconciliation and escalation. Measure actual settlement timing, failure recovery, operator touches and costs. Expand after matching provider statements and internal records.
6. **Escrow activation:** separately satisfy holding, freeze, release, refund and dispute-policy requirements and their end-to-end tests before enabling real escrow. Retain simulation/unavailability until then; acceptance launch does not approve escrow.

## 12. Acceptance criteria

1. Only escrow and acceptance are customer services, with supporting activity/help and staff admin.
2. Fresh browsers open deal/request/shop QR links without installation; fallback codes do not grant ownership.
3. Escrow creation, private joining, verified funding, delivery, release and payout confirmation work across two sessions and refreshes in simulation; production repeats the path against the approved partner holding arrangement.
4. A timely dispute wins against concurrent release; staff decision and actual settlement remain distinct. Production verifies the partner-side freeze and authoritative release outcome; a local database flag alone is insufficient.
5. Temporary requests disclose net amount/charges and fulfill exactly once under concurrent attempts.
6. One permanent shop URL supports three independent customer payments without exposing another customer's data.
7. Collected funds with failed/unknown settlement or escrow payout remain recoverable without false completion or duplicate collection. Batch settlement remains identifiable and reconcilable to individual orders.
8. Duplicate/out-of-order events, double clicks and retries do not duplicate charges, payouts or refunds. Ledger balances reconcile to simulated provider statements locally and actual provider/bank statements before production acceptance.
9. Late receipts, changed/expired quotes, underpayment, duplicate collections, unavailable routes and insufficient float where applicable have explicit outcomes.
10. Public visitors cannot release money/change destinations; participant evidence is private; support lacks finance-only authority.
11. Reports become cases; sensitive admin decisions record reasons and required approvals.
12. Customer experience uses the mobile app layout, desktop admin stays separate, and both share the authoritative backend. Minimal copy, one primary action, no 360px horizontal overflow, keyboard/back/refresh recovery, no native-app requirement, reduced-motion and interruption behavior checked. Mascot states never misrepresent payment.
13. Every offered live route maps to an approved merchant/account and a documented, tested provider capability. No arbitrary personal-wallet payout, automatic withdrawal or escrow claim is inferred from collection support.
14. Provider agreement and responsibility matrix, applicable approval review, production security, incident procedures and backup/restore checks are complete before a separately authorized real-money pilot. Local simulation, provider sandbox and live evidence are labeled separately.
15. Routine acceptance and any advertised automatic settlement work without staff initiating every purchase's transfer. Manual provider withdrawal requirements remain disclosed and do not pass end-to-end automation acceptance. Human review remains available for disputes and exceptions.

Measure time to create/pay, abandonment, link-to-payment conversion, collection-to-settlement delay (or escrow release-to-payout delay), operator touches, dispute response, reconciliation differences and margin after costs. Establish baselines before targets.

## 13. Decisions to validate

- Provider selection and signed platform/agent/merchant model; actual merchant collection, direct/batched settlement, payout/refund and escrow capability matrix.
- Seller onboarding eligibility, especially occasional sellers, provider merchant identities and which party owns verification/customer support obligations.
- Applicable current company, banking and regulatory approvals confirmed with Myanmar payments counsel and the partner; this PRD does not determine the license category.
- Identity checks, limits, verified phone/account formats and beneficiary name matching.
- Settlement schedules and API automation versus manual withdrawal; statement access, finality, reserves, reversals and loss allocation. Prefunding only if the selected model requires platform-funded payouts.
- Commission, fee payer, costs, request expiry and permanent-shop pricing.
- Remaining customer friction after existing MMQR offerings and willingness to pay.
- Protected-deal categories, inspection rules, evidence, staffing and support targets.
- Production private recovery, notifications, staff identity/MFA and incident/support providers.

Continue local mobile testing, accurate flow design and reversible simulation while resolving these dependencies. Document the intended automatic architecture now; finalize the actual live adapter and money/control arrangement with the approved partner. No publication, provider registration, external contact or real transfers are authorized by this document update. Unconfirmed live routes must not be labeled working integrations.
