# Final shared application contract

22 October 2026. This is the authoritative integration decision for Tracks 1–3 and 5. Their browser fixtures are preserved as references and are not financial databases.

## Stack and authority

The inventory found real runnable source in `handshake/app`, not just the earlier previews/empty `dist`. Retain Python 3.11+, a same-origin HTTP app, SQLite with WAL and explicit migrations, plain browser JavaScript, bundled Manrope/elephant and licensed QR encoding. No runtime package install, external CDN or hosting service is needed. No deployment is part of this build.

SQLite is the sole shared authority. Browser storage keeps a draft cache and one-time recovery reminder. Drafts also save under the authenticated account on the server. Records, evidence, receipts, commands, instructions, audit, approvals and jobs persist across restarts. HTTP success is sent only after the transaction commits. All money/state mutations serialize with `BEGIN IMMEDIATE`.

## Resolved product policies

- Exactly two services: escrow and payment acceptance. Single-use requests and permanent shops are acceptance modes.
- Canonical local URLs use `/#record/:id`. This intentionally consolidates the three proposed `/d`, `/r`, `/s` routes under a stable hash router that survives back/refresh. The QR contains the browser URL, not a provider/MMQR payload. Codes resolve the same resource.
- Private high-entropy sessions authorize actions. Public links/codes never authorize release, ownership, evidence or recovery. Escrow also needs a separately shared private buyer invitation. Staff cannot join or pay as customer identities.
- Buyer-authorized escrow release only. Delivery cannot trigger a deadline or automatic release. A timely participant dispute or staff hold blocks a queued release under the same database write lock. Already dispatched unknown outcomes must be queried; confirmed payouts cannot be undone.
- MMK integers; creation limits 500–1,000,000; illustrative net pricing of 2%, minimum 100. Provider collection/payout costs are explicitly zero in this simulator, not an approved real tariff. Requests expire after 30 minutes; payment quotes after 15. A quote freezes total, net, fee/version, beneficiary/version, method, destination, terms, expiry and hash.
- A late receipt at the currently authorized reference can fulfill the original accepted payment after link expiry. Earlier/failed-attempt receipts, extra receipts and amount mismatches become separate refund-only recovery obligations. They never fulfill the request twice or disappear.
- Full refunds return gross, including the original fee, to the original simulated payer source. Partial settlements retain the disclosed original fee and divide the original principal between seller and buyer; both participants must explicitly consent to the exact allocation hash before independent finance approval. There is no arbitrary alternate refund destination.
- Shop beneficiary updates require the private owner and explicit simulated verification, create a new version, and affect only new intents. Existing quotes retain the original destination. This is not real beneficiary verification.

## Persistent schema and migrations

`001_initial.sql` supplies accounts, sessions, records, evidence, events, ledger, jobs, callbacks, commands, proposals and settings. `002_reliability.sql` adds durable receipt inbox/claims, simulated provider instructions, immutable instruction payloads, attempts/error retention and proposal snapshots. `003_drafts_attempts.sql` adds account-scoped drafts and immutable collection attempts. `004_inbox_outcome.sql` preserves exact callback response status on replay. `schema_migrations` applies each migration once; legacy records are retained and their original accounting policy continues. Partial settlement allocation is available on records created with accounting version 2.

Record kinds are `escrow`, `request`, `shop`, `payment`; a payment may also be a refund-only receipt exception or a settlement leg. Cases belong to records, have stable `case:<record-id>` identifiers, assignee, status, reason, evidence and history. Settlement parents link separate immutable payout/refund obligations. They cannot dispatch the original hold again.

Escrow: `awaiting_buyer → awaiting_payment → collection_pending → held → delivered → release_pending → completed`. Exceptions include disputed, payment_failed, payout_failed, payout_unknown, refund_pending, refunded. Agreed allocation uses `settlement_pending → settled` with `settlement_attention` for an unresolved leg. Acceptance payment collection and payout states are separate; collection confirmation alone never means recipient paid.

## Reads

| Endpoint | Authority and result |
|---|---|
| GET /api/session | Actor/role or null; simulation mode |
| GET /api/records/:id | Safe escrow/request/shop preview; private payment reads require owner/payer/staff; private scoped evidence/events/case/quote added for participants |
| GET /api/activity | Customer account-scoped records |
| GET /api/drafts | Private account-scoped drafts |
| GET /api/resolve?code= | Public resource lookup, 30/minute/address; payment-intent codes cannot enumerate private payments |
| GET /api/qr?text= | Actual local browser-entry QR SVG |
| GET /api/evidence/:id | Private participant/staff download |
| GET /api/admin | Staff records, balances, liquidity, inbox, reconciliation and audit |

Admin query filters: `q`, `kind`, `assignee`, `min_amount`, `min_age_hours`. The UI exposes search, service/case filter, assignee, minimum amount and age. Internal staff notes, decisions, raw command/audit payloads and private provider projections do not enter customer event history. Staff can view their full audit history.

## Commands and access

Mutations require same-origin JSON and `X-Handshake: 1`. Customer create/recover, fixed local staff sign-in and logout issue/revoke HttpOnly, SameSite=Strict cookies with seven-day sessions. Recovery keys are stored as hashes. Staff/recovery sign-in is limited to 20 attempts/minute/address. The server binds only to 127.0.0.1.

POST `/api/create`: kind, name, net if applicable, payout rail/destination, simulated verification acknowledgment; escrow adds item, description, delivery and inspection terms. A successful creation clears the server draft. POST `/api/drafts` saves an account-scoped draft without interpreting it as an agreed transaction.

POST `/api/records/:id/:action`: `command_id` and optional `expected_version`. Same actor/key and identical request returns the original committed result; changed input under the same key returns 409. Browser commands send the record version. Supported actions:

- Customer: pay-intent, join, authorize, requote, deliver, release, dispute, pause, destination, evidence, consent-split.
- Support: notes, assignment, evidence requests, pause-release and query an existing unknown outcome; no new financial instruction or approval.
- Operations: support actions, route pause/resume, submit an already independently approved instruction.
- Finance/Admin: human review, offer-split, propose/cancel, independent approve/submit, simulation scenarios; admin has no approval bypass.

Finance proposals freeze amount, action, destination, beneficiary version, quote hash, allocation hash and 30-minute expiry; approval must match the current record version and come from a different immutable staff identity. New evidence invalidates human review. Any changed record invalidates pending approval. Unknown/pending instructions cannot be replaced. Retry requires definitive failed status and retains the failed instruction type, including original-source refunds.

`offer-split` accepts `seller_net`; the server computes conserved buyer principal and discloses retained fee. `consent-split` requires `agree=true` and the exact current hash from each private participant. `propose decision=split`, independent approval and submit allocate the original liability to two separate payment records. Each leg has its own instruction, status and safe recovery. The parent is settled only after both confirm.

POST `/api/admin/route` pauses/resumes new authorizations while preserving outstanding liabilities. Denied/conflicting financial commands are audited independently of rollback. Actor, reason, command ID, version, state changes, amounts, masked destination and stable instruction/provider references remain in append-only history.

## Provider and simulation contract

Only `SimulatedProvider` is configured; capabilities explicitly include `live=false`. Collection payload generation, callback verification, payout submission, refund submission and instruction status querying are separate adapter methods. Status-only querying cannot dispatch an instruction that was never submitted. The simulated provider retains immutable reference/payload identity and final outcomes in SQLite.

The separate `/simulator.html#id` page replaces the external provider handoff for local testing; it requires private payer authority. Outcome/scenario controls are outside the normal customer UI. `POST /api/simulate/:id` accepts confirmed/failed/pending collection only for private payer/buyer or finance/admin. Pending return does not manufacture success. Staff simulation lab selects success, payout_failed, payout_unknown or insufficient_float. Seed commands provide repeatable setups; HTTP tests inject signed duplicates, out-of-order deliveries and failures.

POST `/api/provider/callback` requires `X-Provider-Signature`: HMAC-SHA256 over exact raw JSON bytes using the database's server-only secret. Required fields: record_id, event_id, receipt_id, amount, currency=MMK, reference, method, final=true. Signature, integer amount, exact authorized reference/route, accepted quote and finality are checked. Each authorization reference is durably retained; a browser redirect/screenshot has no financial authority.

Authenticated deliveries and conflicts persist in an append-only inbox. Receipt identity is unique independently of callback-delivery identity. Exact replays retain their response; receipt duplicates never create another fulfillment. Confirmed extra/mismatched receipts create separate balanced suspense and refund-only cases (202). Invalid routes/currencies, identity conflicts and unmatched references are retained for investigation without inventing fulfillment. Corrected authoritative events can later resolve the actual payment. External unmatched-statement import/matching remains a provider integration dependency.

## Ledger, durable jobs and reconciliation

All postings use integer debit-positive/credit-negative MMK; every journal must sum to zero. Unique journal/account constraints and append-only triggers prevent duplicate posting and edits.

For accounting version 2:

1. Collection: debit provider_cash gross; credit escrow_liability or merchant_payable principal and deferred_fee fee.
2. Reserve payout: debit the relevant liability, credit payout_reserved. Full refund also moves deferred_fee into refund_reserved.
3. Confirm payout: debit payout_reserved and deferred_fee; credit provider_cash net and fee_income fee. Confirm refund: debit refund_reserved, credit provider_cash gross.
4. Definitive failure or blocked queued release reverses reservation without deleting history; unknown retains reservation.
5. Extra/mismatched receipts credit receipt_suspense until an independently approved original-source refund.
6. Partial settlement transfers the original hold through settlement_clearing into separately balanced seller/refund obligations; clearing returns to zero. No second collection is booked. Only a failed leg may be retried.

Jobs are a transactional outbox, written alongside authorization and frozen with type, amount, currency, destination, quote/allocation hashes and stable provider/idempotency reference. Workers re-read under a write lock; duplicate worker/status calls are harmless. Jobs commit independently, so one transport failure cannot roll back/starve other payments. Attempts/errors remain recoverable at the same reference across restarts.

Float is simulated capacity, distinct from ledger assets/liabilities. Pending/unknown seller payouts reserve capacity. New authorization checks route/float; post-collection shortage leaves a case and payable, never a request for a second charge. Refunds use collected original-source funds.

Reconciliation compares local authenticated receipts to collection journals, provider instruction outcomes to internal jobs, and all journal balances. Inbox exceptions remain visible in staff work. `python check_database.py` runs a read-only integrity/reconciliation check. CSV exports preserve exact audit/balance data and escape spreadsheet formulas. No balance editing or pretend reconciliation adjustment is offered.

## Motion and operational limits

Track 5's articulated elephant receives authoritative projected state. Confirmed-event identities deduplicate celebration across rerenders/refresh in the browser session. Money text stays static. OS reduced motion and `?motion=reduce` cancel/skip animations; a static PNG fallback is bundled. The fixed 360px QA frame reports real geometry and running-animation counts.

All collection, custody, payout/refund, liquidity and beneficiary verification are simulated. Nothing is sandbox-connected or live. External custody/settlement permission, provider contracts/credentials, real IAM/verification, bank statements, external unmatched-receipt investigation, notifications/SMS/email, production evidence retention/backups and operational response targets remain unresolved connections. The local simulator must not be represented as a completed live payout integration.
