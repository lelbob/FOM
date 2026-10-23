# FOM earned motion — 23 October 2026

The implemented motion follows the current customer flows in both Escrow and Cross banking. The existing ivory/blue palette, Manrope and approved elephant art are retained. No payment/provider behavior or financial authority was added.

## What changed

| Successful action | Where the reward appears | Performance |
|---|---|---|
| Escrow deal created | Share deal | A deal sheet arrives, the elephant lifts and settles, the submission mark appears, and a few shapes disperse. |
| One-time request created | Share payment | Same creation vocabulary, labeled Request ready. QR, amount, code and controls remain stable. |
| Buyer joins escrow | Choose payment method | Two deal tabs meet; the character acknowledges the connection. |
| Payer opens cross banking | Choose payment method | Same restrained connection gesture, labeled Request opened. |
| Receipt submitted, either service | Saved receipt / deal detail | The sheet lands, the elephant nods and a submission mark appears. Persistent copy says Payment is not verified. |
| Seller records package sent | Deal detail | A parcel follows a small arc; the next progress node acknowledges the update. |
| Seller records arrival | Deal detail | A smaller target/mark acknowledgment. The buyer still has to receive and check. |
| Buyer confirms received and checked | Escrow History | The largest finite performance: a jump/settle, short burst, and completed History-row entrance. The reward survives the redirect. |
| Shop inquiry saved | Shop detail | A small document acknowledgment. The message explicitly says team setup is still required. |

## Trigger and interruption rules

- Rewards are queued only after the existing command returns success. Record ID plus the original command identity scopes the event; a state name alone cannot distinguish creation from joining.
- An action plays once per browser session. Refreshing, revisiting an old record and unchanged polling do not replay it. A failed save never queues a reward.
- Keyboard actions, reduced-motion settings and hidden documents receive the same static result. Moving away, focusing an input or hiding the tab stops an in-progress performance and leaves the final information intact.
- Controls remain usable immediately. There is no full-screen blocking celebration, artificial wait, repeated idle loop or new animation dependency.
- Whole-screen cloning was removed from route transitions. New screen content uses a short, staggered entrance. Deferred focus now respects focus already placed inside the new screen.

## Ingredients

- Native Web Animations API; transform and opacity. Existing strong ease-out and ease-in-out curves are reused.
- Individual entrance/mark motions are 180–300 ms. The staged, rare reward performances span approximately 400–850 ms; completion particles finish within about one second. These are finite, nonblocking performances, rather than a delay before the next action.
- The current elephant is a flattened image. Its body moves as one image; ears and trunk are not independently rigged. Separate document, parcel, connection, ring and burst elements provide the richer action choreography.

## Browser verification

An isolated local server and database were used at port 8820. Synthetic titles, receiving details and a clearly labeled test receipt were used; existing user records were not modified by the walkthrough.

Before implementation, both complete services were walked in the browser. After implementation, the Escrow journey was repeated through creation, buyer joining, method selection, receipt upload, seller package photo, arrival confirmation and buyer receipt/checking into History. Cross banking was repeated through creation, code entry, method selection, receipt upload and saved receipt display. The current shop inquiry was also submitted in a separate isolated database and its pending-review acknowledgment was verified. The command-triggered moments and resulting headings are recorded in `evidence/browser-walkthrough.json`.

The replay studio uses the same production motion code and CSS, with sample content and normal, slow and frozen-frame controls. It writes no records. Open `http://127.0.0.1:8821/studio.html` while the local preview servers are running.

## Independent critique and one-redo limit

The first independent pass accepted eight of ten cases. Arrival and shop inquiry each scored 6.8/10 because the compact illustration crowded the first headline letter at 320px, including reduced motion. Each received exactly one targeted layout revision: a 14px grid gap and smaller art anchored from the left. No other choreography was revised after scoring. The final independent layout check inspected revised browser captures and retained the prior unchanged choreography judgments. Both revised cases scored 7.2/10; all ten meet the threshold, with an overall 7.3/10. No second redo was performed.

## Validation

- JavaScript syntax checks passed.
- All 65 backend tests passed.
- Existing customer, payment, two-party escrow and scanner regression checks passed.
- New earned-motion checks passed for all ten service/milestone variants, once-per-command deduplication, truthful status copy, the completion redirect, reduced/query/keyboard/hidden modes, interrupted playback, wrong-record events and single-screen mounting.
- The independent critic’s initial and final scores, including the one allowed targeted revision for any below-7 case, are recorded separately in the critic reports.

## Files

- `handshake/app/public/escrow-motion.js`: choreography, single-screen mounting and motion preferences.
- `handshake/app/public/reward-motion.css`: milestone stage, symbolic objects and responsive layout.
- `handshake/app/public/receipt-app.js`: command-scoped event handoff.
- `handshake/app/public/index.html`: new stylesheet and cache versions.
- `handshake/app/tests/earned_motion_ui.cjs`: semantic and lifecycle regression coverage.

Original entry/controller/motion files were saved under `before/`. Other local shop/claims edits arrived during this task and were retained through narrowly scoped patches; these snapshots should not be used to overwrite those later changes.
