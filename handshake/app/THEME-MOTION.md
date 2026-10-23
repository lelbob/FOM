# Customer theme and motion — 23 October 2026

Applied to the active receipt MVP at /index.html, including Home, Escrow and Payment hubs, history, creation steps, review, sharing, deal details, payment-method selection and receipt instructions, delivery, receive confirmation, scanner, help and recovery.

Uses the approved Escrow Buyer Flow palette, bundled Manrope, rounded input/card/button treatments, lilac amount step and neutral typography. Original AI elephant remains /assets/soft-elephant.png. Previous entry files are preserved under design-history/before-theme-motion-2026-10-23.

Motion: interruptible 250ms screen entrances with 160ms exits, directional tab and back movement, press feedback, focus/selection feedback, submit progress, reversible toast transitions, details reveal, stage and deal progress, finite mascot greeting/rest and event responses. Keyboard navigation is immediate. Reduced motion and hidden-document/input-focus cancellation are built in. Server states and actions remain authoritative. Unchanged polling does not replay entry motion. Financial inputs and sensitive confirmations have no decorative mascot.

Mascot limitation: the source artwork is a flattened PNG. Current performances use subtle transforms of that exact image. Independent trunk/ear acting and the thirteen authored character-performance briefs require external video clips or a real character rig; those assets are not fabricated by this implementation.

Validation: JavaScript syntax checks passed; all 53 backend tests passed; DOM simulations passed for 17 route/state/draft/accessibility cases in both standard and reduced motion; active server returns 200 for the entry page, theme, motion, app script and original mascot. Visual browser verification could not complete because local browser use was disabled in Work settings. No screenshot or pixel-level layout verification is claimed.

## User review refinement — 23 October 2026

Replaced Home's promotional/service banners with editable local profile/avatar and in-place Escrow/Cross banking history filters. Header uses an interlocking FOM mark, simple wordmark and profile access. Removed the repeated demo badges/labels and promotional hub banners. Enter code is now a focused code-only screen; the camera scanner controls were removed. Native photo chooser visuals were replaced with accessible upload tiles and live previews, including persisted draft photo previews. Creation uses Title, a compact four-step indicator, matching amount/input fills and hidden numeric spinner controls. Sharing removes exposed URL and scanner explanation and uses compact QR, amount and paired actions. Short-height CSS reduces unnecessary vertical spacing without hiding overflowing real content.

Profile name and photo are stored on this browser only. Financial/backend behavior is unchanged. Cross banking is the label for the existing payment-request workflow; no live bank integration was added.

Validation: all 53 backend tests and syntax checks passed. Simulated DOM interactions passed in standard/reduced motion for profile photo/name persistence, in-place history switching, code resolution, title/photo draft persistence, share cleanup and 14 routes. Updated entry/script/styles return HTTP 200. Visual and viewport-height verification remain unavailable: local browser use is disabled in Work settings. No screenshot or exact no-scroll claim is made.

## Restored scanner functionality

Restored live camera QR scanning, QR image upload/decoding, stop-camera controls, and the bundled jsQR dependency. Camera permission failures retain manual/image alternatives; streams are stopped on route exit, hidden document, page exit, decode failure and stale permission grants. QR image decoding uses the same existing code/URL resolver as manual entry. Restored an expandable public-link field on Share, including a select-and-copy fallback when Clipboard access fails. No previously named app function is missing relative to the pre-cleanup version.

Added durable DOM regression checks in tests/scanner_ui.cjs and tests/customer_ui.cjs. These require jsdom (or FOM_JSDOM pointing to its module path), and run from handshake/app. Camera and bitmap/decoder APIs are mocked so tests exercise integration without hardware permissions. Scanner start/stop, image success/failure, live decode routing, denied-permission fallback, late-grant cleanup and navigation cleanup passed. The existing customer interaction checks also passed in standard/reduced motion across 14 routes. Live browser/hardware verification is not claimed while browser access is disabled.

## Cozy mascot theme and Help repair

Added two project-local AI image assets (documented with final prompts in public/assets/MASCOT-ASSETS.md), including the elephant-and-peach-ball header logo and a seated welcome pose. Home history and the Escrow/payment headings now include the elephant as part of their layout; no promotional banners were reintroduced. Colors use warm ivory/oat paper, cornflower blue, soft peach and sage. Bottom navigation has consistent accessible house/shield/transfer/scan outline icons. Financial-entry mascot art is still and reduced-motion rules remain active.

Removed the Earlier saved transactions interface and its extra legacy activity fetch, without deleting stored records. Help is now three expandable answers, with restoration still available and the private key shown only when it exists. Added mascot/logo/nav/Help regression assertions; customer interactions and scanner lifecycle tests pass with mocked browser APIs. JS syntax and live asset endpoints verified. Browser visual/hardware verification remains unavailable under the current disabled browser-use setting.

## Wrapping and card containment review

History rows now have rounded backgrounds, borders, internal padding and shrinkable grid tracks. Text wraps without truncation, including identifiers and amounts; at 360px or less, the amount/role moves under the title. Related fixes: share titles grow naturally instead of an inner scrolling region; long page headings, labels, upload captions, buttons and tab labels wrap; detail label/value pairs stack on narrow screens; the mascot and back controls do not shrink; Help disclosure markers stay inside their cards.

Validation: customer and scanner DOM regressions passed, including a separate stress run with very long unbroken titles/descriptions/account references and a 1,000,000 MMK amount in both standard and reduced motion. Updated stylesheet returns HTTP 200. These are content/integration checks, not pixel geometry checks. Visual responsive verification remains blocked by the disabled local browser-use setting.

## Payment-code payer journey

Root cause: a code from its creator's browser was treated as owner navigation; detail() reopened Share payment. Entered/scanned payment codes now deliberately join/resume the payer journey, including the creator-browser case. Existing payer reservations remain exclusive; escrow still forbids the seller joining as its buyer. Expired requests reject receipt submission on the server.

Payer UI is now Method → Pay → Receipt: choose one of five methods, review receiving details/amount, return after paying, upload a required receipt image, confirm, then Mark as done. Navigation alone makes no server-state change; only the saved receipt submission changes requested to sent. Success opens the persistent receipt/details view. Requested payment records already joined by this payer resume method selection instead of sharing.

Validation: all 57 backend tests passed, including creator-browser payment, escrow role separation, exclusive payer and expiry regression tests. Customer/scanner DOM regressions passed. Added tests/payment_flow_ui.cjs covers same-browser code entry through method selection, instructions, missing-receipt rejection, preview/upload, completion and reopening the saved record without returning to Share. Local server restarted with its existing database to load the backend change. No actual money transfer or payment-provider integration was added.

## Escrow back-and-forth flow

Re-read the user's latest full receipt-MVP prompt from Implement FOM app flows and compared it with the historical escrow PRD. The later user requirement governs: no provider/holding/release work added. Escrow remains requested → sent (buyer receipt) → delivering (seller package photo/note) → completed (buyer receipt/checking), with private seller/buyer roles.

The evolving escrow page now prioritizes the current participant's next action or clearly says whose turn is next. Buyer code entry uses the same three-stage method/pay/receipt flow as cross banking, with deal/delivery review and Mark payment as sent instead of falsely finishing the deal. Seller receipt view leads to Confirm package sent, with required package photo and delivery/tracking note. Buyer sees the delivery evidence, confirms receipt/checking, then the completed deal moves to History. Role-specific Active/History rows show waiting/next-action labels. Payment-method/account metadata stays in private receipt details. Financial state and role permissions remain server-owned.

Fixed background refresh rescheduling when an input is focused so the participant can later receive the other party's update. Existing saved records and backend transitions remain unchanged.

Validation: all 11 receipt-MVP HTTP/backend tests passed. Customer, scanner and cross-banking DOM regressions passed. New tests/escrow_flow_ui.cjs exercised two independent participant windows sharing state through code entry, agreement, method choice, prominent destination, receipt upload, seller-only dispatch with required photo, buyer-only receipt confirmation and History. No early completion or opposite-role action appeared. Browser APIs/backend are mocked for DOM checks; actual backend tests use isolated real HTTP sessions and temporary SQLite. Visual browser checks remain unavailable under the disabled browser-use setting.

## Creator-browser escrow code correction

Fixed the remaining owner-code branch that returned a local creator to seller details/sharing. Entering/scanning an unfinished escrow code owned by the current local session now navigates to the same app on the alternate loopback host (127.0.0.1 ↔ localhost), preserving the seller's host-only session. A new buy/:id route creates or resumes the separate buyer session, joins the deal, and opens method selection. Existing buyer sessions resume normally. No escrow self-buy permission, session logout, record deletion or role bypass was introduced. Non-local own-deal entry continues to require a separate buyer browser; an alternate local host already authenticated as the same seller is reported instead of overwriting its identity.

Regression validation: all 12 receipt-MVP HTTP/backend tests pass, including two host-only sessions in a single CookieJar with independent seller/buyer authority. The escrow DOM scenario now begins with the seller entering their own code, checks the alternate-host handoff, creates the buyer session at buy/:id, and continues through payment/receipt, seller dispatch and buyer completion. Customer, scanner and cross-banking regression checks also pass. DOM navigation is intercepted in tests; physical browser visual/camera verification remains unavailable while browser use is disabled.

## Seller arrival confirmation and issue reports

Escrow now follows requested → payment sent → package sent (seller) → arrived (second seller confirmation) → received/checked (buyer). Buyer receipt controls remain unavailable, including through direct API calls, until the seller confirms arrival. Arrival alone never completes a deal. The additional state is stored in existing record JSON; no saved records were deleted or migrated into completion.

A white Report an issue panel appears below the deal's next-step controls and below the buyer's final receipt confirmation. Participants can submit a reason and optional image. Reports are saved with the record and visible to both participants and staff; public viewers cannot access report text or images. Open reports pause payment/dispatch/arrival/completion. Authors can withdraw their own reports; withdrawing one participant's report cannot clear the other participant's open report. No external messages are sent and no automatic dispute decision is made.

Validation: 61 backend tests passed, including seller-only arrival, blocked premature buyer completion, report permissions/privacy/evidence, paused transitions, idempotent arrival and independent report withdrawals. Updated two-party DOM regression covers seller dispatch → buyer report/evidence → pause → withdrawal → seller arrival → buyer receipt/checking → History. Customer, scanner and cross-banking DOM regressions also passed. Backend restarted against the existing database to load these changes. Visual/hardware checks remain unavailable while browser use is disabled.

## Exclusive code claims and pending shop inquiries

Escrow/payment code claims are atomically conditional on an unclaimed code or the same existing buyer/payer. The binding is the persistent server account ID, not a display name or a local-only flag. Another account receives 409 and cannot submit a receipt. Existing claim checks, closed/expired gates and private projections remain in force. Public links may still show the public agreement; viewing it never transfers the claim.

Shop creation now rejects another pending inquiry for the same owner inside the existing BEGIN IMMEDIATE write transaction. Idempotent retries return the original submission. Legacy contact_team shop records count as pending without rewriting or deleting them. Reviewed shops do not consume the pending slot, so multiple registrations can accumulate over time with one pending inquiry at a time. Other accounts have independent limits.

Cross banking greys out the shop-registration button while pending and shows a short explanation. Direct create/shop URLs recheck the server and open the existing inquiry instead of another submission form. Operations/admin can approve or decline an inquiry with a review note from its staff detail view; customers/support cannot self-review or reopen a finished review. Review closes the inquiry and re-enables another shop submission. Internal registration approval does not activate live payments.

Validation: all 65 HTTP/backend tests passed, including simultaneous competing claims, simultaneous submissions from two recovered sessions of one account, idempotent submission, legacy pending inquiries, approval/decline and multiple owned shops. New tests/shop_inquiry_ui.cjs passed disabled-button, direct-route block, permission-aware staff review and re-enabled-registration checks. Customer, scanner, payment and two-party escrow DOM regressions passed. Local backend restarted with the existing database. No records deleted. Physical browser visual/hardware testing remains unavailable under the disabled browser-use setting.

## Earned milestones — 23 October 2026

Added seven finite, command-triggered milestone treatments covering ten Escrow/Cross banking cases: creation, joining/opening, receipt submission, package sent, arrival, buyer-confirmed completion in History, and saved shop inquiry. Status and controls are available immediately. Receipt copy explicitly retains the unverified-payment distinction. The existing approved elephant remains a whole-image asset; separate sheet/parcel/connection/burst elements supply the richer choreography.

Rewards are keyed to the successful command and record, rather than state alone. Reduced-motion, keyboard and hidden-tab paths retain static results. Navigation/input-focus cancels decorative motion. Whole-screen clones and idle breathing loops were removed; deferred focus respects an already-focused field.

Both service journeys were walked before and after implementation in an isolated browser/database, including actual uploads of a synthetic test receipt. All 65 backend tests, existing customer/payment/escrow/scanner checks and new earned-motion lifecycle checks passed. A separate critic reviewed all ten cases in the browser; eight initially passed. Arrival and shop received exactly one spacing revision each for 320px. The final independent layout check used new screenshots while retaining the initial unchanged choreography judgments. Final scores are 7.0–7.8, overall 7.3/10; all ten meet the requested threshold. No second redo was performed.

Full evidence and critic reports are under outputs/motion-implementation at workspace root.
