# Handshake — working local app

Customer experience: [Mobile app in the browser](http://127.0.0.1:8800/mobile.html). Staff experience: [Desktop admin](http://localhost:8800/admin.html). These share the same persistent backend. The customer app now has a phone-width layout, bottom tabs and focused mobile flows; the desktop sidebar is reserved for staff.

The current operational instructions are in [RUNBOOK.md](RUNBOOK.md); the final shared API/state decisions are in [CONTRACT.md](CONTRACT.md). The expanded suite contains 37 backend tests, including receipt exceptions and independently recoverable partial-settlement legs.

The payment-acceptance, customer-UX, admin and motion workstreams are integrated into one app. The home screen leads to escrow, single-use payment requests, permanent shops, private activity, code entry, recovery, receipts and staff operations. All financial state is stored on the server in SQLite. No deployment or real transfers are performed.

## Run

Requires Python 3.11 or later. No package installation or frontend build is needed. Fonts, mascot and the licensed QR encoder are bundled.

From PowerShell:

```powershell
Set-Location "C:/Users/user/OneDrive/Documents/ChatGPT/event 4/handshake/app"
python server.py
```

Open **http://127.0.0.1:8800/#home**. The server binds to loopback only. Keep it running while using the app. `Start Handshake.cmd` is also available. Stop the foreground server with Ctrl+C.

`& './Start Handshake.ps1'` starts a hidden background server, confirms readiness, and reuses this app if already running. Its logs and process ID are in `data/`. This is the launch mode used for the currently running app.

The default database is `data/handshake.sqlite3`; restarting preserves records, sessions, recovery hashes, evidence, events and unfinished jobs. Back up the SQLite database using SQLite's backup API while running, or copy the database and its WAL after stopping. Do not delete the database to resolve a payment exception.

Optional process variables are listed in `.env.example`; the app does not automatically load `.env`. For a separate empty demo database, set `HANDSHAKE_DB` to a new filename before starting. No preloaded customer transactions are required. Staff identities, 10,000,000 MMK simulated payout capacity and open collection routes initialize automatically.

## Customer walkthrough

1. Create a protected deal, payment request or shop from Home. Review exact amounts and the destination before creation. Unfinished forms save in this browser and under your private server account.
2. Save the private recovery key shown once when a new customer session starts. Restore it under **Private access** in a different browser to recover ownership. Public codes cannot recover a private session.
3. Share the browser URL or QR. Localhost URLs only work on this computer. For escrow, give the intended buyer the separate private invitation key; the public code alone cannot join a buyer.
4. Use a private browser window for the buyer. For local QA, `127.0.0.1` and `localhost` also provide independent host-only cookie sessions against the same database. A second ordinary tab on the same host shares its session.
5. The buyer accepts escrow terms, then reviews the total and authorizes payment. The explicitly labeled provider simulator offers successful, failed or pending collection outcomes. Returning pending does not create success.
6. After escrow funding, the seller marks delivery. The buyer checks and authorizes release, or reports a problem. A report blocks a queued release atomically. Payout confirmation follows as a separate server job.
7. A payment request has one payment intent; the same payer resumes it. Different concurrent payers cannot create duplicate fulfillment. Every shop payment creates its own intent. Owners can pause future shop collections.

Illustrative pricing: net amount + 2% fee, minimum 100 MMK. Supported demo amount range: 500–1,000,000 integer MMK. Requests expire after 30 minutes; quotes after 15. This consolidates the four proposals into one explicit demo policy, including escrow. These are not live tariffs or approved limits.

## Staff and scenarios

Open **Staff workspace**. Use a separate browser, or sign out of the customer session first.

| Identity | Access |
| --- | --- |
| `support` | Read cases; assign; add notes; request evidence; query the existing unknown outcome |
| `operations` | Support actions; submit independently approved instructions; pause/resume new collections |
| `finance-a`, `finance-b` | Review cases; propose refund/release/retry; independently approve another identity's proposal; simulation lab |
| `admin` | Finance/operations capabilities, with the same mandatory independent approval |

The default local password is `handshake-demo-2026`. Override with `HANDSHAKE_STAFF_PASSWORD` before starting if needed. These fixed identities are demonstration staff authentication, not enterprise identity management. Sessions are server-issued, HttpOnly, SameSite=Strict cookies, valid for seven days. Customer recovery keys are high-entropy bearer secrets stored as hashes on the server. Save and protect them.

In the queue select **All records**, then open a payment or request. Finance users can open **Provider simulation lab** on a record and set `success`, `payout_failed`, `payout_unknown`, or `insufficient_float`. Set the scenario on a request/shop before creating its payment, or on an escrow before release. Existing payment snapshots retain their own scenario.

Optional setup: `python seed_demo.py` adds clearly named demo request/shop/dispute records and prints the two private demo recovery keys. It preserves existing records. Each run intentionally adds a new set. The server must already be running; pass `--url http://127.0.0.1:PORT` to use another port.

- Success confirms the durable payout/refund job after two seconds.
- Failed payout keeps the collection and liability. Set the payment's scenario back to success; propose retry; use the other finance identity to approve; submit. Retry is only allowed after definitive failure.
- Unknown payout reserves its capacity. Select success or failed as the provider's eventual evidence, then **Query existing provider reference**. Unknown/pending instructions cannot be replaced.
- Insufficient float can block a new authorization, or create a recoverable collected-but-unpaid case after collection. No second payer charge is requested.
- Escrow dispute: record human review, propose full refund or release, independently approve, then submit. Refunds return principal plus the fee to the original simulated source. Failed refunds retain their instruction type on retry.
- Changed records invalidate proposals. Finance can cancel the pending proposal and create a reviewed replacement.
- Agreed partial settlement requires human review, an exact allocation offer, consent from both private participants, and independent finance approval. Payout/refund legs have separate references and recover independently; see RUNBOOK.md.

Private PNG/JPEG/PDF/text evidence is supported up to 2 MB per file. Assignments and evidence requests are shared only with authorized participants and staff. Staff notes remain internal. Reconciliation compares local receipts/instructions to postings and job outcomes, checks zero-sum journals, and exports CSV. Signed extra/mismatched receipts create separate refund-only recovery cases. Audit CSV is escaped against spreadsheet formulas.

## Validate

```powershell
python -m unittest discover -s tests -v
python check_database.py
node --check public/app.js
```

The HTTP integration suite uses temporary databases and independent cookie jars, without touching your saved app records. It covers concurrency, idempotency, callback authentication and reference matching, privacy, permissions, dispute blocking, recovery, unknown/failed payout, independent approvals, full refunds and balanced journals. Node is needed only for the optional JavaScript syntax check.

`http://127.0.0.1:8800/review-mobile.html` presents the actual app in a 360px iframe with the deterministic reduced-motion override. It is a QA page outside customer navigation. OS reduced-motion preferences are also respected.

## Files

`server.py` owns HTTP, sessions, authorization and transactional domain commands. `providers.py` separates simulated collection, callback authentication, payout/refund submission and status querying. `migrations/` contains ordered schema upgrades and append-only/immutable constraints. `public/` contains the integrated interface, local fonts and Track 5 mascot; scenario controls live in the separate simulator/lab. `tests/` exercises the real HTTP server. `CONTRACT.md` documents final decisions.

## Scope and remaining connections

This is an operational **local simulator**, not a live financial service. No bank/wallet collection, payout, custody, real identity/beneficiary verification, SMS/email recovery or notifications are connected. QR handoff is browser-entry only. External statement ingestion/unmatched-reference resolution, reconciliation adjustments and production onboarding remain provider/operating dependencies. Full refunds, agreed partial settlement and versioned simulated shop destinations are implemented. No automatic deadline release is enabled.

Live use additionally requires approved provider/custody/beneficiary arrangements, provider-specific adapters and finality policies, production identity and secrets management, HTTPS hosting, external reconciliation, durable delivery/notification services, retention/backup controls and review of financial operations. The configured provider advertises `live: false`; there is no switch that silently makes this app live.
