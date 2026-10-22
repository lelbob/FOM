# Customer mobile app and desktop staff

Updated 22 October 2026 in response to the user's mobile-app direction.

- Customer browser preview: http://127.0.0.1:8800/mobile.html
- Customer without a device frame: http://127.0.0.1:8800/index.html#home
- Desktop admin: http://localhost:8800/admin.html

This is the working browser implementation of the mobile customer experience, not a native Android/iOS binary. It retains the existing server commands, authentication, SQLite data and financial state machine. The phone preview is an iframe of the real app, not a second UI/fixture model. The two local hosts let staff and customer sessions stay independent during testing.

Changes: dedicated phone shell at every screen width, Home/Activity/Enter code/Account tabs, compact two-service home, request/shop selector within acceptance, touch-sized fields/actions, focused payment/status/share/receipt views and collapsible history. Staff retains a desktop workspace. Manrope/periwinkle/navy and the articulated elephant are preserved.

`mobile-app.css` and `mobile-shell.js` own customer layout and staff/customer shell selection. `mobile.html`, `mobile-preview.css` and `mobile-preview.js` provide the browser device frame, scale to available space and preserve the current customer route on refresh. `admin.html` is the staff entry and loads the same app/controller/API. Original customer sources were copied to `design-history/customer-before-mobile/` before editing.

Validation: all 37 backend tests passed (6.051 seconds). App, shell and preview JavaScript syntax checks passed. Browser checks created a real 10,000 MMK request with 10,200 total, kept review after refresh, rendered genuine QR/code, and showed the saved record in Activity. Staff workspace read the same database on the separate desktop origin. Home/form/review/share were visually inspected. Existing payment-provider capabilities remain explicitly simulated.

The fixed 360px check measured a 360px viewport and document, no horizontal overflow, zero running animations with reduced motion, and an active reduced-motion flag. The actual phone preview and desktop staff screenshots plus `mobile-ui-checks.json` are under `outputs/product-v2/workstreams/04-integration/`. The final app browser returned no warnings/errors. One-time request ↔ Shop QR switching was also exercised.
