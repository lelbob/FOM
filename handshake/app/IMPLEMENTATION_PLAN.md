# Integration completion plan

Inventory: Tracks 1–3 and 5 have handed off. `handshake/app` already contains a runnable Python 3.11 HTTP/SQLite application, 23 passing HTTP tests, local assets, a vendored QR encoder, and customer/staff screens. `handshake/dist` and hosting metadata are not the application. Reuse the runnable source and preserve existing databases and previews.

1. Close private-payment and internal-note leaks; separate customer and staff authority.
2. Add ordered migrations, durable authenticated receipt inbox/reconciliation exceptions, immutable financial instructions and isolated job recovery.
3. Freeze complete quote/instruction snapshots; audit decisions; enforce permissions, approvals and dispute races on the server.
4. Finish operational UI, accessible navigation, deterministic scenario setup and financial/browser regression checks.
5. Update the central contract, runbook and Track 4 handoff with current evidence and explicit simulated/provider boundaries.

Only two services. Buyer-authorized escrow release; no deadline release. All money capabilities remain local simulation. No deployment or real transfer.

Completed: shared state/privacy, durable receipt recovery, immutable instructions, isolated jobs, server drafts, versioned shop destinations and consented partial settlement. Final evidence: 37 passing tests, database reconciliation, actual multi-session browser walkthroughs and 360px/reduced-motion checks. See RUNBOOK.md and the Track 4 HANDOFF.md.
