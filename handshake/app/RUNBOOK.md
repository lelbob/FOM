# FOM — Future of Myanmar · local runbook

## Revised receipt MVP — 23 October 2026

The latest user direction supersedes the earlier customer navigation and automatic-provider demonstration. The normal index now has Escrow, Payment and Enter code, with no Account tab. Receipt submission records Marked as sent, not verified payment. Escrow adds seller delivery photo and buyer received confirmation; one-time payments archive after submission. Shop setup saves an application and ends at Contact team without external contact. ES/PY/SP codes and camera/image QR scanning are supported. Existing financial records, sessions and staff controls are preserved in the legacy view. New nonfinancial states use migration 006 and `/api/mvp/*`; they never book a ledger entry or dispatch money. Full revised flow and current validation: `outputs/receipt-mvp/HANDOFF.md` at workspace root.


22 October 2026. Exactly two services: escrow and acceptance (single-use requests or permanent shops). All financial capabilities are simulated; none are sandbox-connected or live.

## Current FOM build

Use `/index.html` for the normal phone-width app and `/mobile.html` for the optional device preview. Both use this server and the saved database. The desktop workspace is `/admin.html`. Home has Protect a deal and Accept payments; requests and shops reuse saved fictional merchant setup. Provider authorization is explicitly simulated on the separate testing surface. A counter browser QR is not bank-payable.

Current implementation evidence and selected screenshots: `../../outputs/fom-implementation/IMPLEMENTATION_REPORT.md`. The prior 37-test evidence below is historical; the FOM pass has 46 backend tests plus browser checks. No provider connection or deployment occurred.

## Start

Python 3.11+. No dependency install, frontend build or external assets.

```powershell
Set-Location "C:/Users/user/OneDrive/Documents/ChatGPT/event 4/handshake/app"
python server.py
```

Open the **customer mobile app preview: http://127.0.0.1:8800/mobile.html**. The **desktop admin: http://localhost:8800/admin.html** uses a separate local host cookie so staff sign-in does not replace the customer test session. Both use the same backend and database. Direct customer links such as `http://127.0.0.1:8800/#home` also use the mobile app layout.

Ctrl+C stops a foreground server. `Start Handshake.cmd` or `& './Start Handshake.ps1'` starts a hidden server, verifies readiness and reuses an existing instance. The launcher does not automatically reload changed source. Logs and PID are in `data/`.

SQLite data in `data/handshake.sqlite3` survives restart. Migrations apply once in order. Do not delete the database to resolve exceptions. Use SQLite's backup API while running, or stop before copying the database and WAL. For an isolated walkthrough, set `HANDSHAKE_DB` to a new filename and `HANDSHAKE_PORT` to another port before starting. `.env.example` contains placeholder secrets; `.env` is not auto-loaded. The callback secret is initialized once per database and persisted; environment changes do not rotate an existing secret.

## Independent participants

Use a normal browser for owner/seller and a private window for payer/buyer. A second ordinary tab shares its session. For local QA, `127.0.0.1` and `localhost` also provide independent host-only cookie sessions against the same backend; replace the host in a shared URL for that arrangement.

Save the private recovery key shown once on session creation. Restore it through **Private access** to recover activity and server drafts. Public links/codes never recover ownership or authorize release. Escrow requires the separate seller-issued private buyer invitation. Never enter real banking PINs or OTPs.

Browser URLs/QRs are stable local entry links, not bank-app MMQR. Loopback links cannot open on another physical phone.

## Walkthroughs

1. **Escrow:** create/review/share; buyer joins privately and accepts exact terms/fees; authorize and open the separate provider simulator. Return pending and refresh first. Confirm collection there, seller marks delivery, buyer deliberately releases, then wait for separate payout confirmation. A timely report pauses queued release immediately.
2. **Temporary request:** specify recipient net and simulated destination; payer reviews gross/fee and method. One request creates one intent, resumed by the same payer. Collection and payout remain separate. A late receipt at the still-current accepted authorization can fulfill after expiry.
3. **Shop:** keep one URL and pay 3,000, 5,000 and 10,000 MMK; private activity shows independent payments. Owner pause blocks new collections. A new simulated beneficiary version changes future quotes only.

Illustrative policy: integer MMK, 500–1,000,000; net + 2%, minimum 100 fee; requests expire after 30 minutes and quotes after 15. These are not live tariffs. Full refunds return gross including fee; agreed partial settlements retain the disclosed original fee.

## Staff and scenarios

Staff identities: `support`, `operations`, `finance-a`, `finance-b`, `admin`. Local demo password: **handshake-demo-2026**, unless overridden before server startup. These fixed identities are demonstration authentication, not production IAM. Support cannot create or approve financial instructions. Operations may submit an already independently approved instruction. Admin cannot bypass second-person approval.

Seed labeled scenarios while the server is running:

```powershell
python seed_demo.py --scenario success
python seed_demo.py --scenario payout_failed
python seed_demo.py --scenario payout_unknown
python seed_demo.py --scenario insufficient_float
python seed_demo.py --scenario duplicate_events
```

Each invocation preserves existing data, creates a request/payment, shop and funded disputed escrow, and prints their URLs plus private demo recovery keys. Each run adds a new set. Pass `--url http://127.0.0.1:8801` for another port; use the same overridden staff-password environment as the server if applicable.

Finance can also use a record's **Provider simulation lab**, outside customer navigation. Set the source scenario before intent creation, or a payment/escrow before instruction dispatch. Existing payment snapshots retain their own scenario.

- **Failed payout:** collection remains confirmed and owed. Change the failed payment's scenario to success; propose retry; another finance identity approves; submit. No second charge.
- **Unknown payout:** query its original reference after setting the simulator's eventual evidence to success or failed. Pending/unknown outcomes cannot be replaced/refunded/retried; unknown capacity stays reserved.
- **Insufficient float:** blocks authorization or leaves a recoverable payable after collection. No false completion or second-payment request.
- **Full refund:** human-review a disputed escrow; propose refund; independent finance approval; submit. Confirmation returns gross to the original simulated payer. A failed refund retry remains a refund.
- **Partial settlement:** human-review; enter **Seller allocation · MMK** and **Offer partial settlement**. Both private participants agree to the exact allocation/retained fee on their status page. Finance proposes `split`; another identity approves; submit. Seller payout and buyer refund have separate references. Follow a failed leg from the staff case and recover only that leg. The parent settles only when both confirm.
- **Extra/mismatched receipts:** signed deliveries create separate refund-only liabilities/cases in the receipt inbox. Review, propose original-source refund, independently approve and submit. Invalid/unmatched references remain visible for investigation without invented fulfillment. Signed replay/out-of-order/mismatch setup is exercised by the HTTP suite.

Private evidence supports PNG/JPEG/PDF/text up to 2 MB. Staff notes never enter customer history. Reasons are required; changed records invalidate approvals. Reconciliation/audit CSV exports escape spreadsheet formulas. There is no balance-editing interface.

## Checks

```powershell
python -m unittest discover -s tests -v
python check_database.py
node --check public/app.js
node --check public/simulator.js
node --check public/mascot.js
node --check public/review-mobile.js
```

The **37 tests** use real independent HTTP sessions and temporary databases. The read-only database check targets your selected saved database. Open funded cases are liabilities, not automatically reconciliation differences. Node is needed only for optional syntax checks.

`http://127.0.0.1:8800/review-mobile.html#home` embeds the real app at 360px with reduced motion. Other routes include `#create/request`, `#admin` and `#record/ID`. Its separate QA panel measures geometry, overflow, running animations and focus. A scrollbar may leave 345px content width inside the 360px frame.

## Provider and operating dependencies

Collection, custody, payout/refund, float and beneficiary verification are simulated. No real transfer, publication or deployment is enabled. Real operation still needs approved holding/intermediary settlement arrangements, provider contracts/credentials/finality, real identity/beneficiary verification and authentication, external statements/unmatched-receipt resolution, notifications/recovery delivery, retention/backups and response targets. No deadline release or arbitrary alternate-beneficiary override is enabled. See `CONTRACT.md` for the final shared API/schema/policy and Track 4 handoff for actual validation evidence.
