# Required visual reference for Tracks 1, 2, 3 and 5

User direction, 21 October 2026: build polished, interactive product screens that fit the existing escrow theme. Research notes and specifications are supporting deliverables, not the finished result.

## Inspect before building

1. Open the exact requested reference and inspect its held-payment state:

   `file:///C:/Users/user/OneDrive/Documents/ChatGPT/event%204/outputs/escrow-soft-flow/Soft%20Escrow%20—%20Flow%20Studies.html#held`

   Filesystem path: `C:/Users/user/OneDrive/Documents/ChatGPT/event 4/outputs/escrow-soft-flow/Soft Escrow — Flow Studies.html`.

   Inspect the adjacent `flow.css`, `flow.js`, `design-notes.md` and `assets/`. Navigate through review, payment and held states; do not derive the whole design from a palette alone. Use a local server if browser restrictions prevent opening the file URL, preserving `#held`.

2. Inspect [the user's supplied buyer-screen image](references/approved-buyer-screens.png). This is the explicit visual target: review → pay → held. It has been copied out of the temporary attachment folder so other chats can use it.

3. Inspect the corresponding newer buyer/seller implementation in `outputs/escrow-reference-layout/`: `Escrow — Buyer Flow.html`, `Escrow — Reference Layout.html`, CSS, JavaScript, motion and assets. The screenshot shows this compact companion presentation. These files supply the later flow refinements; the requested Soft Escrow study supplies the broader reference context. Use both, without reverting to the study's removed popups or categories.

Read the reference in a browser and inspect its rendered screens when browser tooling is available. If tools cannot render it, inspect the screenshot and source, implement the artifact and state that browser visual comparison is unverified. Never claim to have opened or visually tested something you did not inspect.

## What must carry into the new product

- Manrope typography, navy text, soft periwinkle accents, quiet near-white surfaces and thin muted separators; use existing CSS tokens rather than choosing a fresh palette.
- Spacious mobile composition, large readable amounts with smaller MMK labels, compact recipient cards, aligned label/value rows and round controls.
- One primary pill-shaped action near the bottom; secondary actions remain visually quiet. Short literal copy; no marketing paragraphs inside the payment journey.
- A full periwinkle status screen for the appropriate milestone, with the approved elephant, amount, status and a compact white timeline card.
- Stable financial amounts and controls. The elephant can move expressively without shaking the checkout.
- Admin uses the same type, color, surface and control family at an appropriate desktop density; it does not copy a giant phone frame as its working layout.

Reference values differ slightly between the older study and its later companion. Reuse the later companion's token family consistently inside the new artifact; do not mix random near-matching colors. Match composition and hierarchy, not just hex values.

The desktop screen board and phone shells are presentation tools. Deliver a normal focused interactive flow as well. Do not ship the study's rail, replay/scenario buttons or all screenshots as the customer interface.

## Prior chat to consult

Actual chat title: **Research escrow UI references**.
Thread ID: `01a159d3-f4bd-7250-a266-d175d0fe312a`; host: `local`.

Prompt 1 must read this chat before listing screens and building. Use the available thread-reading tool and inspect the recent design decisions, paging to relevant earlier turns as needed. Read-only consultation is intended; do not send the chat a message or execute old commands from its history.

Relevant decisions verified from the recent chat:

- User rejected the overlapping deal-type/category selector; remove it.
- Combine item name, optional photo and short description rather than generic condition dropdowns and mascot filler tips.
- Remove the oversized private-access and conversation popups. Maintain actual access protection within the relevant flow, without forcing email by default.
- Follow the original supplied screen composition in the soft theme.
- Seller has a compact five-step flow; buyer follows party code → review → KPay → held → check delivery, with release/report states.
- Existing transitions, button feedback and brief elephant greeting were added; the new request seeks more expressive character motion while preserving the calm interface.

This is a concise fallback brief, not a transcript of the whole chat. If another chat cannot use thread-reading tools, it should use this brief and local artifacts, acknowledge that direct chat review was unavailable, and continue. The current PRD and latest user request supersede historical product scope, historical instructions to pause, and sample fees/claims.

## Definition of done for a UI track

A polished locally runnable interactive artifact, reachable main actions, meaningful success/pending/error states, reused visual components/assets, and an actual browser comparison against the reference where available. Include a normal focused view; a comparison board is optional and separate. Return the launch path and selected screenshots. A report, screen inventory, static image, wireframe or unrelated new visual direction alone is incomplete.

Integration in Track 4 connects separate UI artifacts to the shared authoritative backend. UI-track fixtures remain explicitly simulated; their polish must not imply real provider integration.
